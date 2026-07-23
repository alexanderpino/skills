"""A 3D 'hero' view of a heightfield — a pure-numpy software rasteriser (perspective camera + z-buffer)
that projects the terrain as a mesh, drapes it with the substance colouring, lights it in 3-D
(sun+sky + AO from the mesh normal) and composites it over a sky background. The plan-view renders in
`render.py` show the DATA (top-down hillshade / splat); this shows the PLACE — the angled 3/4 view a
Gaea / World Machine / Terragen viewport gives.

`main()` renders terrain that comes STRAIGHT FROM THE GRAPH — no hand-sculpting: `from_graph()` uplifts
a noisy block and lets stream-power fluvial erosion (Braun & Willett 2013) carve it, so the ridges and
dendritic valleys *emerge* from the simulation (Cordonnier-2016 uplift+erosion), exactly how an AAA
terrain graph produces them. The rivers are real: `hydrology.py` gives a water SURFACE (lakes fill to
spill level, rivers carry a discharge-scaled depth), rendered as water at a level in the carved
channel — not a blue line painted on the bed.

Deliberately dependency-free: numpy for the maths, `render.write_png` for output. It is a *software*
rasteriser (z-buffered, sun+sky lit, depth fog + supersampled AA) — it will not match a path-traced
engine (no soft shadows, no atmosphere, no PBR), but it turns any heightfield into a credible hero
render. Run: `python hero.py`.
"""
import numpy as np

import hydrology
import render


# --------------------------------------------------------------------------- #
# camera maths (right-handed, OpenGL-style)
# --------------------------------------------------------------------------- #
def _look_at(eye, target, up):
    eye, target, up = (np.asarray(v, dtype=np.float64) for v in (eye, target, up))
    f = target - eye
    f /= np.linalg.norm(f) + 1e-12
    s = np.cross(f, up)
    s /= np.linalg.norm(s) + 1e-12
    u = np.cross(s, f)
    m = np.eye(4)
    m[0, :3], m[1, :3], m[2, :3] = s, u, -f
    m[:3, 3] = -m[:3, :3] @ eye
    return m


def _perspective(fovy_deg, aspect, near, far):
    fy = 1.0 / np.tan(np.radians(fovy_deg) / 2.0)
    m = np.zeros((4, 4))
    m[0, 0] = fy / aspect
    m[1, 1] = fy
    m[2, 2] = (far + near) / (near - far)
    m[2, 3] = 2.0 * far * near / (near - far)
    m[3, 2] = -1.0
    return m


# --------------------------------------------------------------------------- #
# the hero render
# --------------------------------------------------------------------------- #
def hero(h, cell, texture, *, az=38.0, elev=42.0, fovy=30.0, dist_scale=2.2, z_exag=1.0,
         size=(1200, 760), sun=(-0.5, 0.85, 0.3), sky_top=(120, 150, 192), sky_bottom=(206, 221, 236),
         fog=0.3, ss=2, ao=None, water_depth=None):
    """Render a heightfield `h` (metres, `cell` m/px) as a 3D hero view, draped with `texture` — an
    (H, W, 3) **material** colour (pass the *unshaded* substance colour; the 3D sun+sky lighting is
    applied here from the mesh normal, so don't pre-shade it). `water_depth` (optional, m) composites
    **translucent** water as a separate final stage (the bed shows through shallow water). Camera orbits
    the tile centre at `az`/`elev`; `z_exag` scales relief, `fog` hazes the far ground toward the sky,
    `ao` is an optional (H, W) occlusion field, `ss` supersamples for AA."""
    h = np.asarray(h, dtype=np.float64)
    tex = np.asarray(texture, dtype=np.float64)
    nH, nW = h.shape
    W, Hgt = int(size[0]) * ss, int(size[1]) * ss

    # world-space vertices: X east, Z north (ground plane), Y up (height). Centre the tile.
    jj, ii = np.meshgrid(np.arange(nW), np.arange(nH))
    X = (jj - (nW - 1) / 2.0) * cell
    Z = (ii - (nH - 1) / 2.0) * cell
    Y = (h - h.min()) * z_exag
    verts = np.stack([X.ravel(), Y.ravel(), Z.ravel(), np.ones(h.size)], axis=1)

    extent = max(nW, nH) * cell
    target = np.array([0.0, (Y.mean() - 0.0) * 0.4, 0.0])
    a, e = np.radians(az), np.radians(elev)
    eye = target + dist_scale * extent * np.array([np.cos(e) * np.sin(a), np.sin(e), np.cos(e) * np.cos(a)])
    mvp = _perspective(fovy, W / Hgt, 0.05 * extent, 6.0 * extent) @ _look_at(eye, target, (0, 1, 0))

    clip = verts @ mvp.T
    w = clip[:, 3]
    w_safe = np.where(np.abs(w) < 1e-9, 1e-9, w)
    ndc = clip[:, :3] / w_safe[:, None]
    sx = (ndc[:, 0] * 0.5 + 0.5) * W
    sy = (1.0 - (ndc[:, 1] * 0.5 + 0.5)) * Hgt
    depth = ndc[:, 2]
    behind = w <= 0                                                       # vertices behind the camera

    # per-vertex lit colour: bake a sun+sky term from the mesh normal so the 3D form reads
    gy, gx = np.gradient(h, cell)
    nz = 1.0 / np.sqrt(gx * gx + gy * gy + 1.0)
    normal = np.stack([-gx * nz, np.ones_like(h) * nz, -gy * nz], axis=-1)   # (H,W,3), Y-up
    sundir = np.asarray(sun, dtype=np.float64)
    sundir /= np.linalg.norm(sundir) + 1e-12
    lam = np.clip(normal @ sundir, 0.0, 1.0)
    shade = 0.55 + 0.45 * lam                                            # sky floor + sun (bright)
    if ao is not None:                                                   # darken sky-occluded creases
        shade = shade * (1.0 - 0.35 * np.clip(np.asarray(ao, dtype=np.float64), 0, 1))
    lit = tex * shade[..., None]                                         # lit LAND
    if water_depth is not None:                                         # water is a SEPARATE, TRANSLUCENT stage
        lit = hydrology.water_over_land(lit, water_depth)              # bed shows through shallow water
    vcol = np.clip(lit, 0, 255).reshape(-1, 3)

    # sky-gradient background
    grad = np.linspace(0.0, 1.0, Hgt)[:, None]
    frame = ((np.array(sky_top) * (1 - grad) + np.array(sky_bottom) * grad)[:, None, :]
             * np.ones((1, W, 1))).astype(np.float64)
    zbuf = np.full((Hgt, W), np.inf)

    # triangle indices (two per grid quad)
    i0 = (np.arange(nH - 1)[:, None] * nW + np.arange(nW - 1)).ravel()
    tris = np.concatenate([np.stack([i0, i0 + nW, i0 + 1], 1),
                           np.stack([i0 + 1, i0 + nW, i0 + nW + 1], 1)], axis=0)

    fogc = np.array(sky_bottom, dtype=np.float64)
    dmin, dmax = float(depth.min()), float(depth.max())
    for tri in tris:
        va, vb, vc = tri
        if behind[va] or behind[vb] or behind[vc]:
            continue
        xa, ya = sx[va], sy[va]
        xb, yb = sx[vb], sy[vb]
        xc, yc = sx[vc], sy[vc]
        denom = (yb - yc) * (xa - xc) + (xc - xb) * (ya - yc)
        if denom >= 0:                                                    # back-face / degenerate cull
            continue
        minx = max(int(np.floor(min(xa, xb, xc))), 0)
        maxx = min(int(np.ceil(max(xa, xb, xc))), W - 1)
        miny = max(int(np.floor(min(ya, yb, yc))), 0)
        maxy = min(int(np.ceil(max(ya, yb, yc))), Hgt - 1)
        if minx > maxx or miny > maxy:
            continue
        px, py = np.meshgrid(np.arange(minx, maxx + 1), np.arange(miny, maxy + 1))
        w0 = ((yb - yc) * (px - xc) + (xc - xb) * (py - yc)) / denom
        w1 = ((yc - ya) * (px - xc) + (xa - xc) * (py - yc)) / denom
        w2 = 1.0 - w0 - w1
        inside = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
        if not inside.any():
            continue
        z = w0 * depth[va] + w1 * depth[vb] + w2 * depth[vc]
        sub = zbuf[miny:maxy + 1, minx:maxx + 1]
        hit = inside & (z < sub)
        if not hit.any():
            continue
        col = (w0[..., None] * vcol[va] + w1[..., None] * vcol[vb] + w2[..., None] * vcol[vc])
        if fog > 0.0:                                                     # aerial haze with distance
            t = np.clip((z - dmin) / (dmax - dmin + 1e-9), 0.0, 1.0)[..., None] * fog
            col = col * (1.0 - t) + fogc * t
        dst = frame[miny:maxy + 1, minx:maxx + 1]
        dst[hit] = col[hit]
        sub[hit] = z[hit]

    frame = np.clip(frame, 0, 255).astype(np.uint8)
    if ss > 1:                                                            # box-downsample the supersample
        frame = frame.reshape(Hgt // ss, ss, W // ss, ss, 3).mean(axis=(1, 3)).astype(np.uint8)
    return frame


def from_graph(n=180, extent_km=48.0, seed=4):
    """Terrain straight from the node GRAPH — no hand-sculpting. Uplift a noisy block, then let
    STREAM-POWER fluvial erosion carve it (Braun & Willett 2013, cross-validated vs Landlab), then
    thermal talus. Ridges and dendritic valleys EMERGE from the simulation (Cordonnier-2016 uplift+
    erosion), the way an AAA terrain graph produces them. Returns (height, drainage area, cellsize)."""
    import graph_demo as G
    cell = extent_km * 1000.0 / n
    ctx = G.Ctx(cellsize=cell, resolution=n, root_seed=seed)
    g, (h_out, a_out) = G.build_graph(ctx, backbone="streampower")
    return g.evaluate(h_out), g.evaluate(a_out), cell


def main():
    import analysis
    import archetypes as A
    import flow
    import shallow_water
    h, area, cell = from_graph()                                        # graph output — nothing sculpted
    climate = {"has_water": False, "has_snow": True, "snowline": 0.6, "snow_soft": 0.16, "has_veg": True}

    # substances: LAND cover (water is a separate layer). Grab the snow mask for meltwater.
    slope = analysis.slope(h, cell)
    stack = dict(analysis.derive_substances(h, slope, area, cell, climate=climate))
    snow = stack["snow"]
    hn = (h - h.min()) / (np.ptp(h) + 1e-9)
    melt = 5e-6 * snow * np.clip(1.0 - (hn - climate["snowline"]) / (1.0 - climate["snowline"]), 0.0, 1.0)

    # REAL water: mass-conserving shallow-water flow fed by RAIN + SNOWMELT (water runs from under the snow)
    sim = shallow_water.simulate(flow.priority_flood_fill(h), cell, rain=4e-6, source_field=melt, iters=1400)
    Q = sim["discharge"]                                                # volumetric flow, m³/s
    w = hydrology.water_surface(h, cell, Q)                             # channel/lake surface from the discharge
    depth = w - h                                                      # water depth (m), 0 on dry land

    col, _, surf = A.substance_color(h, "temperate", cell, climate=climate)   # unshaded LAND material
    render_surf = np.maximum(surf, w)                                  # water fills valleys; snow piles on peaks
    ao = analysis.horizon_ao(render_surf, cell)
    img = hero(render_surf, cell, col, ao=ao, z_exag=1.0, water_depth=depth)   # translucent water as its own stage
    render.write_png("hero.png", img)
    b = sim["budget"]
    print(f"wrote hero.png  ({img.shape[1]}x{img.shape[0]}, {h.shape[0]}² graph mesh, relief {h.max()-h.min():.0f} m)")
    melt_frac = 100 * melt.sum() / (melt.sum() + 4e-6 * h.size)
    print(f"  flow: peak discharge {Q.max():.1f} m³/s ({melt_frac:.0f}% from snowmelt); "
          f"mass balance {b['rain_in']:.3e} = {b['out']+b['stored']:.3e} m³")


if __name__ == "__main__":
    main()
