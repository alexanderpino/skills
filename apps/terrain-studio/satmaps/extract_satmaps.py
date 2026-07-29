#!/usr/bin/env python3
"""Derive Terrain Studio's SatMap colour LUTs from REAL top-down satellite imagery.

Gaea's SatMaps are hand-curated gradients "extracted from satellite imagery". We don't
hand-pick RGB stops — we reproduce the extraction: pull public-domain **top-down**
satellite/aerial images from Wikimedia Commons (the satellite-image *categories*
guarantee orbital/aerial framing, so there is no sky to pollute the ramp — the failure
mode of ground-level photos), mask out deep space and open ocean, then order the
remaining land pixels by luminance into an elevation gradient with the skill's own
`reference-impl/render.extract_satmap` (Rec.709 luminance ordering — valley floors and
shadow dark, crests/snow bright).

Run:  python3 extract_satmaps.py           # writes derived.json + prints a JS SATMAPS block
Output is reproducible: same categories -> same ranked pick -> same palette.

Pure stdlib + numpy + PIL. Network via the environment's HTTPS proxy.
"""
import io
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "reference-impl"))
from render import extract_satmap  # noqa: E402  (the skill's verified extractor)

API = "https://commons.wikimedia.org/w/api.php"
UA = "TerrainStudio-SatMapExtractor/1.0 (skill reference-impl; contact via repo)"

# Per biome: a CURATED ordered list of specific real top-down images (we choose the SOURCE that
# actually depicts this terrain type; the algorithm still derives the palette mechanically), plus
# category fallbacks. Prefer TRUE-COLOUR nadir imagery (Sentinel-2 / Landsat / ISS / natural-colour
# ASTER); false-colour scenes are rejected by the hue guard below.
SOURCES = {
    "Alpine":   ["File:Alpi liguri-satellite.jpg"],
    "Canyon":   ["File:Perspective view over the Grand Canyon, Arizona (ASTER).jpg",
                 "File:Yarlung Zangpo Grand Canyon, Tibet.jpg"],
    "Arid":     [],  # no confirmed warm true-colour source -> category fallback, else authored
    "Dune":     ["File:Rub' al Khali (Arabian Empty Quarter) sand dunes imaged by Terra (EOS AM-1).jpg",
                 "File:Linear Dunes, Namib Sand Sea.jpg"],
    "Volcanic": ["File:Icelandic lava ESA25438760.jpg",           # true-colour basalt (not false-colour ASTER)
                 "File:Solidified lava ESA25461016.jpg"],
    "Verdant":  ["File:Amazon 57.53278W 2.71207S.jpg", "File:Amazon MODIS.jpg"],
    "Arctic":   ["File:Shedding Light on Greenland, relief.jpeg"],
    "Tundra":   ["File:Earth from Space- Cloud-free Iceland ESA509442.jpg"],  # Sentinel true-colour subarctic
    "Mars":     [],  # MOLA is false-colour hypsometry, not natural surface -> keep authored Mars
    "Lunar":    ["File:The Moon showing Mare Orientale (LROC WAC orthographic projection).jpg"],
}
# Category fallbacks (scored) if none of the curated sources load.
BIOMES = {
    "Alpine":   ["Satellite pictures of the Alps", "Satellite pictures of the Himalayas"],
    "Canyon":   ["Satellite pictures of Utah"],
    "Arid":     ["Satellite pictures of Iran"],
    "Dune":     ["Satellite pictures of the Rub' al Khali", "Satellite pictures of the Sahara"],
    "Volcanic": ["Satellite pictures of volcanoes"],
    "Verdant":  ["Satellite pictures of the Amazon rainforest"],
    "Arctic":   ["Satellite pictures of Greenland"],
    "Tundra":   ["Satellite pictures of Iceland"],
    "Mars":     ["Maps of Mars"],
    "Lunar":    ["Satellite pictures of the Moon"],
}
# Hue-plausibility guard: given the MEDIAN land colour, is this source the right terrain family?
# Rejects false-colour scenes and semantic mismatches (a green valley masquerading as a canyon).
def _warm(r, g, b):  return r > b + 6 and r >= g - 6            # rock / desert / mars
def _green(r, g, b): return g >= r - 4 and g >= b               # vegetation
def _grey(r, g, b):  return (max(r, g, b) - min(r, g, b)) < 42  # ice / rock / moon (low saturation)
HUE_GUARD = {
    "Canyon": _warm, "Arid": _warm, "Mars": _warm, "Dune": _warm,
    "Verdant": _green,
    "Volcanic": _grey, "Arctic": _grey, "Lunar": _grey,
    # Alpine (brown->snow) and Tundra (mixed) take any plausible land image.
}

N_STOPS = 12
THUMB_W = 640
MAX_CANDIDATES = 5          # images to score per biome
MIN_LAND_FRAC = 0.35        # reject frames that are mostly space / ocean / cloud
REQ_TIMEOUT = 20            # Commons thumb generation for gigapixel sources can hang -> skip fast
MAX_SRC_MPX = 140           # skip absurdly large sources (slow/failing on-demand thumbs)


MIN_INTERVAL = 2.6          # pace requests -> respect Wikimedia rate limits (avoid HTTP 429)
_last = [0.0]


def _pace():
    dt = MIN_INTERVAL - (time.monotonic() - _last[0])
    if dt > 0:
        time.sleep(dt)
    _last[0] = time.monotonic()


def _get(url, tries=3, timeout=REQ_TIMEOUT):
    for i in range(tries):
        _pace()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 429 and i < tries - 1:       # throttled -> long backoff, then retry
                time.sleep(18 * (i + 1))
                continue
            raise
        except Exception:  # noqa: BLE001
            if i == tries - 1:
                raise
            time.sleep(1.5 * (i + 1))
    return None


def _api(params):
    params = {**params, "format": "json"}
    return json.loads(_get(API + "?" + urllib.parse.urlencode(params)).decode("utf-8"))


def category_files(cat, limit=30):
    d = _api({"action": "query", "list": "categorymembers",
              "cmtitle": "Category:" + cat, "cmtype": "file", "cmlimit": limit})
    return [m["title"] for m in d.get("query", {}).get("categorymembers", [])]


def image_info(title):
    """Thumb URL + descriptive/licence metadata for a File: title. Returns None for
    non-images and for gigapixel sources (their on-demand thumbs hang the proxy)."""
    d = _api({"action": "query", "titles": title, "prop": "imageinfo",
              "iiprop": "url|extmetadata|mime|size", "iiurlwidth": THUMB_W})
    pages = d.get("query", {}).get("pages", {})
    for _, p in pages.items():
        ii = (p.get("imageinfo") or [None])[0]
        if not ii or not ii.get("mime", "").startswith("image"):
            return None
        if (ii.get("width", 0) * ii.get("height", 0)) > MAX_SRC_MPX * 1_000_000:
            return None
        em = ii.get("extmetadata", {})
        return {
            "title": title,
            "url": ii.get("thumburl") or ii.get("url"),
            "descurl": ii.get("descriptionurl"),
            "license": (em.get("LicenseShortName", {}) or {}).get("value", "?"),
            "artist": _strip(( em.get("Artist", {}) or {}).get("value", "")),
        }
    return None


def _strip(html):
    import re
    return re.sub("<[^>]+>", "", html or "").strip()[:160]


def load_rgb(url):
    im = Image.open(io.BytesIO(_get(url))).convert("RGB")
    return np.asarray(im, dtype=np.uint8)


def land_pixels(rgb):
    """Center-crop (drop black limb / borders), then keep LAND pixels: drop deep space
    (near-black) and open ocean (blue-dominant, not too bright). Returns (pixels Nx3, land_frac)."""
    h, w, _ = rgb.shape
    y0, y1 = int(h * 0.15), int(h * 0.85)
    x0, x1 = int(w * 0.15), int(w * 0.85)
    crop = rgb[y0:y1, x0:x1].reshape(-1, 3).astype(np.float64)
    r, g, b = crop[:, 0], crop[:, 1], crop[:, 2]
    mx = crop.max(1)
    space = mx < 28                                   # cosmos / black frame
    ocean = (b > r + 14) & (b > g + 8) & (b < 155)    # open deep water
    land = ~(space | ocean)
    frac = float(land.mean())
    return crop[land], frac


def score(pixels, frac):
    """Rank frames: mostly-land AND a wide luminance spread (elevation range to map)."""
    if len(pixels) < N_STOPS * 40:
        return -1.0
    lum = pixels @ np.array([0.2126, 0.7152, 0.0722])
    spread = float(np.percentile(lum, 96) - np.percentile(lum, 4)) / 255.0
    return frac * (0.35 + spread)


def evaluate(title, biome, cat=None):
    """Load a File: title, mask to land, apply the hue guard, and extract its palette.
    Returns a candidate dict or None (not an image / too little land / wrong terrain family)."""
    try:
        info = image_info(title)
        if not info or not info["url"]:
            return None
        rgb = load_rgb(info["url"])
    except Exception:  # noqa: BLE001
        return None
    px, frac = land_pixels(rgb)
    if frac < MIN_LAND_FRAC:
        return None
    guard = HUE_GUARD.get(biome)
    med = np.median(px, axis=0)
    if guard and not guard(med[0], med[1], med[2]):
        return None                                       # wrong family (e.g. false-colour / green canyon)
    stops = extract_satmap(px.reshape(-1, 1, 3), n_stops=N_STOPS, smooth=1)
    return {"score": score(px, frac), "frac": frac, "info": {**info, "category": cat},
            "stops": [[round(p, 3), [int(round(c)) for c in rgb]] for p, rgb in stops]}


def pick_for_biome(biome):
    # 1) curated sources first, in order — the SOURCE is chosen to match the terrain; palette is derived.
    for title in SOURCES.get(biome, []):
        cand = evaluate(title, biome, cat="curated")
        if cand is not None:
            return cand
    # 2) fallback: scan the biome's category and keep the best-scoring image that passes the guard.
    best = None
    for cat in BIOMES.get(biome, []):
        try:
            titles = category_files(cat)
        except Exception:  # noqa: BLE001
            continue
        for t in titles[:MAX_CANDIDATES]:
            cand = evaluate(t, biome, cat=cat)
            if cand and (best is None or cand["score"] > best["score"]):
                best = cand
        if best is not None:
            break
    return best


def main():
    dst = HERE / "derived.json"
    out = json.loads(dst.read_text()) if dst.exists() else {}
    only = set(sys.argv[1:])                 # optional: re-extract just these biomes
    for biome in BIOMES:
        if only and biome not in only:
            continue
        print(f"[{biome}] curated={SOURCES.get(biome, [])[:1]} ...", flush=True)
        pick = pick_for_biome(biome)
        if pick is None:
            print("  -> no usable image (kept authored fallback)", flush=True)
            continue
        out[biome] = pick
        dst.write_text(json.dumps(out, indent=1, ensure_ascii=False))   # save incrementally
        i = pick["info"]
        print(f"  -> {i['title']}  land={pick['frac']:.2f} score={pick['score']:.3f}", flush=True)
        print(f"     {i['license']} | {i['descurl']}", flush=True)
    print("\n// ---- JS SATMAPS stops (paste into index.html) ----")
    for biome, p in out.items():
        stops = ",".join(f"[{s[0]:g},[{s[1][0]},{s[1][1]},{s[1][2]}]]" for s in p["stops"])
        print(f" {biome}:[{stops}],")
    print(f"\nwrote {dst}  ({len(out)} biomes extracted)")


if __name__ == "__main__":
    main()
