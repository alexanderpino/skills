#!/usr/bin/env python3
"""
detect_doc_conventions.py — learn an organisation's documentation house style.

Scans a docs tree (and repo signals like issue templates and .feature files), clusters
documents by type, and infers each type's conventions: required front-matter fields,
**mandatory sections** (headings present in most instances), ID scheme, and format
signals (Connextra user stories, Gherkin acceptance criteria, Nygård/MADR ADRs, …).

Output is a machine-readable `house-profile.yaml` that the skill conforms to and that
`arch_lint.py --house` enforces. House conventions OVERRIDE the skill's built-in defaults
— a company that mandates, say, a "Data Privacy Impact" section in every HLD gets it
enforced. Can also emit starter house templates from what it learned.

Pure standard library (Python 3.8+). Uses PyYAML to write YAML if present, else JSON
(also valid YAML). No third-party dependencies required.

Usage:
  python detect_doc_conventions.py --root docs/architecture --out house-profile.yaml
  python detect_doc_conventions.py --root docs/architecture --emit-templates docs/architecture/_house
  python detect_doc_conventions.py --root docs/architecture --threshold 0.6
"""
from __future__ import annotations
import argparse, glob, json, os, re, sys
from collections import defaultdict, Counter

# ---------- front-matter parsing (same tolerant approach as arch_lint) ----------
def split_frontmatter(text):
    lines = text.splitlines()
    start = next((i for i, ln in enumerate(lines[:15]) if ln.strip() == "---"), None)
    if start is None:
        return {}, text
    end = next((j for j in range(start + 1, len(lines)) if lines[j].strip() == "---"), None)
    if end is None:
        return {}, text
    return parse_yaml("\n".join(lines[start + 1:end])), "\n".join(lines[end + 1:])

def parse_yaml(raw):
    try:
        import yaml  # type: ignore
        d = yaml.safe_load(raw)
        return d if isinstance(d, dict) else {}
    except Exception:
        out = {}
        for ln in raw.splitlines():
            m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", ln)
            if m and not ln.startswith(" "):
                v = m.group(2)
                v = re.sub(r"\s+#.*$", "", v).strip().strip("'\"")
                out[m.group(1)] = v
        return out

# ---------- type inference ----------
def infer_type(path, fm):
    name = os.path.basename(path)
    t = str(fm.get("type") or "").strip()
    if t:
        return t.upper()
    fid = str(fm.get("id") or "").strip()
    for pat, label in ((r"^ADR-", "ADR"), (r"^RFC-", "RFC"), (r"^US-", "US"),
                       (r"^EP-", "EP"), (r"^SD-", "SD")):
        if re.match(pat, name) or re.match(pat, fid):
            return label
    for key in ("AD", "PRD", "HLD", "SAD", "EA"):
        if fid == key or fid.upper() == key:
            return key
    up = name.upper()
    for key in ("HLD", "PRD", "SAD", "ADR", "RFC"):
        if key in up:
            return key
    if "USER-STOR" in up or "STORY" in up:
        return "US"
    if fid in ("architecture-index", "decision-log") or name.lower() == "readme.md":
        return "INDEX"
    return fid.upper() if fid else "UNKNOWN"

def norm_section(h):
    # strip leading numbering and markers; collapse to a comparable key
    h = re.sub(r"^\s*\d+(\.\d+)*[.)]?\s*", "", h).strip()
    h = re.sub(r"\s*\(.*?\)\s*$", "", h).strip()   # drop trailing "(mandatory)" etc.
    return h

def format_signals(body):
    low = body.lower()
    sig = {}
    if any(s in low for s in ("as a ", "as an ")) and "i want" in low:
        sig["story_format"] = "connextra"
    if "given " in low and "when " in low and "then " in low or "scenario:" in low:
        sig["ac_style"] = "gherkin"
    elif "- [ ]" in body:
        sig["ac_style"] = "checklist"
    if "## context" in low and "## decision" in low and "## consequences" in low:
        sig["adr_style"] = "nygard"
    if "decision drivers" in low or "considered options" in low:
        sig["adr_style"] = "madr"
    return sig

# ---------- scan ----------
def scan(root, threshold):
    types = defaultdict(lambda: {
        "instances": 0, "fields": Counter(), "sections": Counter(),
        "section_display": {}, "ids": [], "signals": Counter(), "files": [],
    })
    for path in sorted(glob.glob(os.path.join(root, "**", "*.md"), recursive=True)):
        text = open(path, encoding="utf-8", errors="ignore").read()
        fm, body = split_frontmatter(text)
        t = infer_type(path, fm)
        rec = types[t]
        rec["instances"] += 1
        rec["files"].append(os.path.relpath(path, root))
        for k in fm:
            if not k.startswith("_"):
                rec["fields"][k] += 1
        seen = set()
        for ln in body.splitlines():
            m = re.match(r"^(#{2,3})\s+(.*\S)\s*$", ln)
            if m:
                disp = norm_section(m.group(2))
                key = disp.lower()
                if key and key not in seen:
                    rec["sections"][key] += 1
                    rec["section_display"].setdefault(key, disp)
                    seen.add(key)
        if fm.get("id"):
            rec["ids"].append(str(fm["id"]))
        for k, v in format_signals(body).items():
            rec["signals"][f"{k}={v}"] += 1

    profile = {}
    for t, rec in sorted(types.items()):
        n = rec["instances"]
        if t in ("UNKNOWN",) and n < 2:
            continue
        need = max(1, round(threshold * n))
        required = sorted([f for f, c in rec["fields"].items() if c >= need])
        optional = sorted([f for f, c in rec["fields"].items() if c < need])
        mand = [rec["section_display"][k] for k, c in rec["sections"].most_common() if c >= need]
        opt = [rec["section_display"][k] for k, c in rec["sections"].most_common() if c < need]
        entry = {
            "instances": n,
            "required_frontmatter": required,
            "optional_frontmatter": optional,
            "mandatory_sections": mand,
            "optional_sections": opt,
        }
        if rec["ids"]:
            entry["id_examples"] = rec["ids"][:3]
            entry["id_scheme"] = _id_scheme(rec["ids"])
        if rec["signals"]:
            entry["formats"] = {s.split("=")[0]: s.split("=")[1]
                                for s, _ in rec["signals"].most_common()}
        profile[t] = entry
    return profile

def _id_scheme(ids):
    s = ids[0]
    return re.sub(r"\d+", "N", re.sub(r"[A-Za-z]+", "A", s)) if s else ""

def org_signals(repo_root):
    sig = {}
    it = []
    for pat in (".github/ISSUE_TEMPLATE/*", ".gitlab/issue_templates/*"):
        it += [os.path.relpath(p, repo_root) for p in glob.glob(os.path.join(repo_root, pat))]
    if it:
        sig["issue_templates"] = sorted(it)
    feats = glob.glob(os.path.join(repo_root, "**", "*.feature"), recursive=True)
    if feats:
        sig["feature_files"] = len(feats)
    styles = [os.path.relpath(p, repo_root)
              for p in glob.glob(os.path.join(repo_root, "**", "*.md"), recursive=True)
              if re.search(r"(contributing|style.?guide|conventions|template)", os.path.basename(p), re.I)]
    if styles:
        sig["style_docs"] = sorted(styles)[:20]
    return sig

# ---------- emit templates ----------
def emit_templates(profile, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    written = []
    for t, e in profile.items():
        if t in ("INDEX", "UNKNOWN"):
            continue
        lines = ["---"]
        for f in e.get("required_frontmatter", []) or ["id", "title", "status"]:
            lines.append(f"{f}: <{f}>")
        lines += ["---", "", f"# {t} — <title>", "",
                  "<!-- Generated from the detected house style. Mandatory sections below. -->", ""]
        for s in e.get("mandatory_sections", []):
            lines += [f"## {s}", "<...>", ""]
        path = os.path.join(out_dir, f"{t.lower()}-template.md")
        open(path, "w", encoding="utf-8").write("\n".join(lines))
        written.append(path)
    return written

# ---------- main ----------
def main():
    ap = argparse.ArgumentParser(description="Detect documentation house style")
    ap.add_argument("--root", default="docs/architecture")
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--out", default="house-profile.yaml")
    ap.add_argument("--threshold", type=float, default=0.6,
                    help="fraction of instances a section/field must appear in to be 'required'")
    ap.add_argument("--emit-templates", metavar="DIR")
    args = ap.parse_args()

    if not os.path.isdir(args.root):
        print(f"docs root not found: {args.root}"); sys.exit(2)

    profile = scan(args.root, args.threshold)
    doc = {
        "generated_from": args.root,
        "thresholds": {"mandatory_section": args.threshold, "required_field": args.threshold},
        "org_signals": org_signals(args.repo_root),
        "types": profile,
    }
    try:
        import yaml  # type: ignore
        open(args.out, "w", encoding="utf-8").write(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True))
    except Exception:
        open(args.out, "w", encoding="utf-8").write(json.dumps(doc, indent=2, ensure_ascii=False))
    print(f"Wrote house profile to {args.out}")
    for t, e in profile.items():
        print(f"  {t}: {e['instances']} doc(s), "
              f"{len(e.get('mandatory_sections', []))} mandatory section(s), "
              f"{len(e.get('required_frontmatter', []))} required field(s)")
    if args.emit_templates:
        for p in emit_templates(profile, args.emit_templates):
            print(f"  emitted template: {p}")

if __name__ == "__main__":
    main()
