# Imperial core prototype: Forum of the Founder + porphyry column, Milion, Hippodrome,
# Great Palace terraces, Holy Peace, Great Church (AF30), Agora, Mese porticoes.
# Same painterly-oblique vocabulary as render_xero epic_ground/epic_tall.
# All geometry & years come from world.json / anthousa_world3d.json (never invented).
# usage: python3 epic_core.py core 0 1 30 60   |  python3 epic_core.py apostles 10 11 60
import json, math, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from shapely.geometry import Polygon, LineString, Point, box
from shapely.ops import unary_union
from shapely import affinity
from scipy.ndimage import zoom as nd_zoom, gaussian_filter

R = '/workspace/work/pubmain/'
W = json.load(open(R + 'world.json'))
D = json.load(open(R + 'docs/anthousa_world3d.json'))
ST = {s['id']: s for s in W['structures']}
S = 14.22      # px per world unit (same as Xerolophos local frame), ~0.84 m/px
SS = 2         # supersample
M = 12.0 / S   # metres per px
TILE, TILE_D = (186, 92, 62), (132, 60, 40)
MARBLE, MARBLE_D = (232, 226, 212), (176, 168, 150)
LEAD = (128, 134, 138)

def hsh(n, k=0):
    x = math.sin(n * 127.1 + k * 311.7) * 43758.5453
    return x - math.floor(x)

def alive(s, Y):
    b = s.get('built', -9999); d = s.get('destroyed')
    return b <= Y and (d is None or d > Y)

class Canvas:
    def __init__(self, x0, z0, x1, z1):
        self.x0, self.z0 = x0, z0
        self.w, self.h = int((x1 - x0) * S), int((z1 - z0) * S)
        self.im = Image.new('RGBA', (self.w * SS, self.h * SS), (0, 0, 0, 255))
        self.d = ImageDraw.Draw(self.im, 'RGBA')
    def P(self, x, z):  # world -> local px
        return ((x - self.x0) * S, (z - self.z0) * S)
    def T(self, pts, lift=0.0, dx=0.0, dy=0.0):
        return [((x + dx) * SS, (y - lift + dy) * SS) for x, y in pts]
    def poly_local(self, coords):
        return Polygon([self.P(x, z) for x, z in coords])
    def line_local(self, coords):
        return LineString([self.P(x, z) for x, z in coords])

def _split(p, depth=0):
    if not p.interiors or depth > 6: return [p]
    x0, y0, x1, y1 = p.bounds; cx, cy = p.interiors[0].centroid.x, p.interiors[0].centroid.y
    out = []
    for b in (box(x0 - 1, y0 - 1, cx, cy), box(cx, y0 - 1, x1 + 1, cy), box(x0 - 1, cy, cx, y1 + 1), box(cx, cy, x1 + 1, y1 + 1)):
        q = p.intersection(b)
        for r in ([q] if q.geom_type == 'Polygon' else [g for g in getattr(q, 'geoms', []) if g.geom_type == 'Polygon']):
            if r.area > 0.5: out += _split(r, depth + 1)
    return out
def polys(g):
    if g.is_empty: return []
    base = [g] if g.geom_type == 'Polygon' else [p for p in getattr(g, 'geoms', []) if p.geom_type == 'Polygon']
    return [q for p in base for q in _split(p)]

# ---------- primitives ----------
def shadow(c, pg, h, a=64):
    k = h * 0.55
    parts = [affinity.translate(pg, k * t, k * 0.7 * t) for t in (0.34, 0.67, 1.0)]
    sh = unary_union(parts).difference(pg)
    for p in polys(sh): c.d.polygon(c.T(p.exterior.coords), fill=(50, 34, 18, a))

def prism(c, pg, h, roof=TILE, wall=(206, 184, 150), ridge=True, sh=True, outline=None):
    """extruded block, oblique: south faces visible, roof lifted by h px"""
    if pg.geom_type != 'Polygon' or pg.interiors:
        ps = polys(pg)
        if sh:
            for p in ps: shadow(c, p, h)
        for p in sorted(ps, key=lambda p: p.centroid.y): prism(c, p, h, roof, wall, ridge, False, outline)
        return
    if sh: shadow(c, pg, h)
    pts = list(pg.exterior.coords)
    if pg.exterior.is_ccw: pts = pts[::-1]
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        nx, ny = -(by - ay), (bx - ax)   # outward normal (ring forced to shapely-cw, y down)
        if ny > 0.05 * math.hypot(nx, ny):
            k = 0.82 + 0.18 * (nx / (abs(nx) + abs(ny) + 1e-9))
            col = tuple(int(v * k) for v in wall)
            c.d.polygon(c.T([(ax, ay), (bx, by), (bx, by - h), (ax, ay - h)]), fill=col + (255,))
    c.d.polygon(c.T(pg.exterior.coords, h), fill=roof + (255,))
    if outline: c.d.line(c.T(pg.exterior.coords, h), fill=outline + (255,), width=1)
    if ridge:
        r = pg.minimum_rotated_rectangle
        if r.geom_type != 'Polygon': return
        q = list(r.exterior.coords)[:4]
        e = [(q[i], q[(i + 1) % 4]) for i in range(4)]
        L = [math.dist(a, b) for a, b in e]
        i = 0 if L[0] >= L[1] else 1
        j, k = (i + 1) % 4, (i + 3) % 4
        a = ((e[j][0][0] + e[j][1][0]) / 2, (e[j][0][1] + e[j][1][1]) / 2)
        b = ((e[k][0][0] + e[k][1][0]) / 2, (e[k][0][1] + e[k][1][1]) / 2)
        # light north slope, dark south slope
        hl = tuple(min(255, int(v * 1.12)) for v in roof)
        c.d.line(c.T([a, b], h + 1.5), fill=hl + (255,), width=max(1, int(1.6 * SS)))

def dome(c, x, y, r, base_h, col=LEAD, drum=0, drum_col=(214, 200, 176)):
    shadow(c, Point(x, y).buffer(r), (drum + r) * 0.9)
    if drum:
        c.d.rectangle([(x - r) * SS, (y - base_h - drum) * SS, (x + r) * SS, (y - base_h) * SS], fill=drum_col + (255,))
        for i in range(8):
            wx = x - r + (i + 0.5) * 2 * r / 8
            c.d.rectangle([(wx - 0.6) * SS, (y - base_h - drum * 0.75) * SS, (wx + 0.6) * SS, (y - base_h - drum * 0.3) * SS], fill=(70, 56, 40, 255))
    top = y - base_h - drum
    c.d.pieslice([(x - r) * SS, (top - r) * SS, (x + r) * SS, (top + r * 0.5) * SS], 180, 360, fill=col + (255,))
    c.d.ellipse([(x - r) * SS, (top - r * 0.25) * SS, (x + r) * SS, (top + r * 0.25) * SS], fill=tuple(int(v * 0.9) for v in col) + (255,))
    c.d.arc([(x - r * 0.7) * SS, (top - r * 0.85) * SS, (x + r * 0.2) * SS, (top + r * 0.2) * SS], 200, 270, fill=(220, 226, 228, 200), width=SS * 2)

def colonnade(c, band, h, roof=TILE, col_step=4.2, edge=None):
    """roofed portico band; columns drawn along its south/inner edge"""
    for p in polys(band): prism(c, p, h, roof=roof, wall=MARBLE, ridge=False)
    if edge is not None:
        L = edge.length; n = int(L / col_step)
        for i in range(n + 1):
            pt = edge.interpolate(i * col_step)
            c.d.line([pt.x * SS, pt.y * SS, pt.x * SS, (pt.y - h) * SS], fill=MARBLE + (255,), width=max(2, int(1.2 * SS)))
            c.d.line([(pt.x + 0.7) * SS, pt.y * SS, (pt.x + 0.7) * SS, (pt.y - h) * SS], fill=MARBLE_D + (255,), width=1)

def people(c, region, n, seed, avoid=None):
    x0, y0, x1, y1 = region.bounds; k = 0; placed = 0
    cols = [(150, 60, 50), (60, 80, 120), (226, 220, 200), (110, 90, 60), (170, 130, 60), (90, 120, 80)]
    while placed < n and k < n * 8:
        k += 1
        px, py = x0 + hsh(k, seed) * (x1 - x0), y0 + hsh(k, seed + 1) * (y1 - y0)
        if not region.contains(Point(px, py)): continue
        if avoid is not None and avoid.contains(Point(px, py)): continue
        col = cols[k % len(cols)]
        c.d.ellipse([(px + 0.3) * SS, (py + 0.1) * SS, (px + 2.2) * SS, (py + 1.0) * SS], fill=(60, 40, 20, 60))
        c.d.ellipse([(px - 0.7) * SS, (py - 1.4) * SS, (px + 0.7) * SS, (py + 0.3) * SS], fill=col + (255,))
        placed += 1


# ---------- construction phases (world.json structures[].phases, ledger-only years) ----------
def phase(sid, Y):
    """-> (stage, parts_done, frac): stage of the whole building in year Y; parts finished early;
    frac = progress through the current stage toward the next phase year (0..1)"""
    ph = ST[sid].get('phases')
    if not ph: return ('done' if alive(ST[sid], Y) else None), set(), 1.0
    if Y < ph[0]['year']: return None, set(), 0.0
    cur = None; nxt = None
    for i, p in enumerate(ph):
        if p['year'] <= Y and 'part' not in p: cur = (i, p)
    parts = {p['part'] for p in ph if 'part' in p and p['year'] <= Y}
    i, p = cur
    if p['stage'] == 'done': return 'done', parts, 1.0
    for q in ph[i + 1:]:
        if 'part' not in q: nxt = q; break
    frac = (Y - p['year'] + 0.5) / max(1, nxt['year'] - p['year']) if nxt else 0.5
    return p['stage'], parts, min(1.0, frac)

EARTH = (168, 140, 100)
def site(c, pg, seed, n_work=24, stones=True, fill=EARTH):
    """cleared plot: raw earth, survey stakes and cords, stone stacks, an ox cart, workers"""
    c.d.polygon(c.T(pg.exterior.coords), fill=fill + (255,))
    x0, y0, x1, y1 = pg.bounds
    for k in range(int((x1 - x0) * (y1 - y0) / 900) + 4):    # spoil heaps and ruts
        px, py = x0 + hsh(k, seed) * (x1 - x0), y0 + hsh(k, seed + 3) * (y1 - y0)
        if not pg.contains(Point(px, py)): continue
        r = 2 + 4 * hsh(k, seed + 5)
        c.d.ellipse([(px - r) * SS, (py - r * 0.5) * SS, (px + r) * SS, (py + r * 0.5) * SS], fill=(148, 120, 84, 255))
    ring = pg.exterior
    for i in range(int(ring.length / 10)):       # stakes + cord
        q = ring.interpolate(i * 10)
        c.d.line([q.x * SS, q.y * SS, q.x * SS, (q.y - 4) * SS], fill=(96, 70, 44, 255), width=SS)
    c.d.line(c.T(ring.coords, 3), fill=(236, 226, 200, 200), width=1)
    if stones:
        for k in range(int(ring.length / 40) + 2):
            q = ring.interpolate(hsh(k, seed + 9) * ring.length)
            px, py = q.x + (hsh(k, seed + 11) - 0.5) * 16, q.y + (hsh(k, seed + 12) - 0.5) * 10
            for j in range(3):
                prism(c, box(px - 4 + j * 0.8, py - 2 + j * 0.3, px + 4 - j * 0.8, py + 2 - j * 0.3), 2.2 + j * 1.8, roof=(206, 196, 172), wall=(178, 166, 140), ridge=False, sh=(j == 0))
    k = int(hsh(seed, 77) * 1000)
    q = ring.interpolate(hsh(seed, 78) * ring.length)
    ox(c, q.x, q.y + 4, seed)
    people(c, pg, n_work, seed + 21)

def ox(c, x, y, seed):
    c.d.rectangle([(x - 5) * SS, (y - 3) * SS, (x + 1) * SS, (y + 0.5) * SS], fill=(120, 88, 56, 255))
    for wx in (x - 4, x):
        c.d.ellipse([(wx - 1.3) * SS, (y - 0.5) * SS, (wx + 1.3) * SS, (y + 1.5) * SS], fill=(70, 50, 30, 255))
    c.d.rectangle([(x - 4) * SS, (y - 5) * SS, x * SS, (y - 3) * SS], fill=(206, 196, 172, 255))
    for k in (0, 1):
        c.d.ellipse([(x + 2 + k * 3.2) * SS, (y - 2.6) * SS, (x + 5 + k * 3.2) * SS, (y - 0.4) * SS], fill=(150, 130, 104, 255))

def scaffold(c, pg, h, step=7):
    """timber poles and ledgers around a rising building"""
    ring = pg.exterior
    pts = [ring.interpolate(i * step) for i in range(int(ring.length / step))]
    for q in pts:
        c.d.line([q.x * SS, (q.y + 1) * SS, q.x * SS, (q.y - h - 5) * SS], fill=(128, 94, 58, 255), width=SS)
    for z in np.arange(4, h + 4, 5):
        c.d.line(c.T(ring.coords, z), fill=(146, 110, 70, 230), width=SS)

def rising(c, pg, h_full, frac, seed, wall=(210, 192, 160)):
    """walls up to frac of full height, open top (rubble core), scaffolding, workers on top"""
    h = max(3, h_full * (0.25 + 0.6 * frac))
    prism(c, pg, h, roof=(176, 160, 128), wall=wall, ridge=False)
    inner = pg.buffer(-3, join_style=2)
    for p in polys(inner): c.d.polygon(c.T(p.exterior.coords, h), fill=(150, 128, 96, 255))
    scaffold(c, pg, h)
    people(c, affinity.translate(pg.buffer(-0.5), 0, -h), max(4, int(pg.length / 30)), seed)
    return h

def crane(c, x, y, h, ang=0.6):
    """treadwheel crane: a raking timber jib with a rope and block"""
    tx, ty = x + math.cos(ang) * h * 0.35, y - h
    c.d.line([x * SS, y * SS, tx * SS, ty * SS], fill=(110, 78, 46, 255), width=SS * 2)
    c.d.line([(x + 6) * SS, y * SS, tx * SS, ty * SS], fill=(110, 78, 46, 255), width=SS)
    c.d.line([tx * SS, ty * SS, (tx + 2) * SS, (ty + h * 0.45) * SS], fill=(60, 50, 40, 255), width=1)
    c.d.rectangle([(tx + 0.5) * SS, (ty + h * 0.45) * SS, (tx + 3.5) * SS, (ty + h * 0.45 + 2.5) * SS], fill=(206, 196, 172, 255))
    c.d.ellipse([(x - 4) * SS, (y - 7) * SS, (x + 4) * SS, (y + 1) * SS], outline=(110, 78, 46, 255), width=SS)

# ---------- ground ----------
def ground(c, Y):
    g = D['grid']; hgt = np.array(g['heights'], float).reshape(g['nz'], g['nx'])
    wat = np.array(g['water'], float).reshape(g['nz'], g['nx'])
    f = S * g['step']
    i0, j0 = (c.z0 - g['z0']) / g['step'], (c.x0 - g['x0']) / g['step']
    nzc, nxc = int(c.h / f) + 3, int(c.w / f) + 3
    a, b = int(i0), int(j0)
    sub_h = hgt[a:a + nzc, b:b + nxc]; sub_w = wat[a:a + nzc, b:b + nxc]
    H = nd_zoom(sub_h, f * SS, order=1); Wm = gaussian_filter(nd_zoom(sub_w, f * SS, order=1), 10 * SS)
    oy, ox = int((i0 - a) * f * SS), int((j0 - b) * f * SS)
    H = H[oy:oy + c.h * SS, ox:ox + c.w * SS]; Wm = Wm[oy:oy + c.h * SS, ox:ox + c.w * SS]
    gy, gx = np.gradient(gaussian_filter(H, 22 * SS))
    lit = np.clip(0.95 - (gx + gy) * 2.5, 0.72, 1.12)
    rng = np.random.default_rng(3); noise = gaussian_filter(rng.normal(0, 1, H.shape), 2 * SS) * 6
    land = np.stack([186 * lit + noise, 168 * lit + noise, 128 * lit + noise], -1)
    sea = np.stack([62 + 0 * H, 112 + 0 * H, 128 + 0 * H], -1) + noise[..., None] * 0.6
    m = np.clip((Wm - 0.35) * 4, 0, 1)[..., None]
    shore = np.clip(1 - np.abs(Wm - 0.42) * 14, 0, 1)[..., None]
    img = land * (1 - m) + sea * m
    img = img * (1 - shore * 0.5) + np.array([214, 200, 160]) * shore * 0.5
    c.im.paste(Image.fromarray(np.clip(img, 0, 255).astype('uint8')).convert('RGBA'), (0, 0))
    c.water = Wm

def roads(c, Y, skip=()):
    for s in W['structures']:
        if s['type'] != 'road' or not alive(s, Y) or s['id'] in skip: continue
        ln = c.line_local(s['geom']['coords']); w = s.get('width', 1.2) * S
        g = ln.buffer(w / 2 + 1.5, cap_style=1)
        for p in polys(g): c.d.polygon(c.T(p.exterior.coords), fill=(150, 132, 100, 255))
        g = ln.buffer(w / 2, cap_style=1)
        paved = s['id'] in ('r_mese', 'r_hippo') and Y >= 1
        for p in polys(g): c.d.polygon(c.T(p.exterior.coords), fill=((206, 196, 174) if paved else (176, 156, 120)) + (255,))
        if paved:   # flagstones
            L = ln.length
            for i in range(int(L / 3.2)):
                pt = ln.interpolate(i * 3.2); v = int(hsh(i, 5) * 16) - 8
                for off in (-w * 0.3, 0, w * 0.3):
                    q = ln.interpolate(min(L, i * 3.2 + 0.01)); dx, dy = q.x - pt.x, q.y - pt.y
                    c.d.point([(pt.x) * SS, (pt.y + off) * SS], fill=(190 + v, 180 + v, 160 + v, 255))

def walls(c, Y):
    for s in W['structures']:
        if s['type'] != 'wall' or not alive(s, Y): continue
        ln = c.line_local(s['geom']['coords'])
        band = ln.buffer(0.9 * S, cap_style=2)
        for p in polys(band.intersection(box(0, 0, c.w, c.h))): prism(c, p, 9, roof=(196, 180, 150), wall=(170, 150, 118), ridge=False)
        for i in range(int(ln.length / 70)):
            pt = ln.interpolate(i * 70 + 20)
            if 0 < pt.x < c.w and 0 < pt.y < c.h: prism(c, box(pt.x - 8, pt.y - 8, pt.x + 8, pt.y + 8), 16, roof=(186, 168, 136), wall=(160, 140, 110), ridge=False)

def trees(c, Y, block):
    rng = np.random.default_rng(11); n = 0
    for k in range(5000):
        x, y = rng.uniform(0, c.w), rng.uniform(0, c.h)
        if c.water[int(y * SS) % c.water.shape[0], int(x * SS) % c.water.shape[1]] > 0.25: continue
        if block.contains(Point(x, y)): continue
        r = 2.2 + rng.uniform(0, 2.4); g = int(rng.uniform(-12, 12))
        c.d.ellipse([(x + 1) * SS, (y + 0.5) * SS, (x + r * 2 + 1) * SS, (y + r + 0.5) * SS], fill=(60, 44, 20, 70))
        c.d.ellipse([(x - r) * SS, (y - r - 2) * SS, (x + r) * SS, (y + r * 0.6 - 2) * SS], fill=(104 + g, 120 + g, 64 + g, 255))
        n += 1
        if n > 700: break

def houses(c, Y, keepout):
    hs = []
    for h in D['houses']:
        if h['built'] > Y or (h['destroyed'] is not None and h['destroyed'] <= Y): continue
        x, z = h['cx'], h['cz']
        if not (c.x0 - 2 < x < c.x0 + c.w / S + 2 and c.z0 - 2 < z < c.z0 + c.h / S + 2): continue
        pg = c.poly_local(h['poly'])
        if keepout is not None and keepout.intersects(pg): continue
        hs.append((pg.centroid.y, pg, h))
    hs.sort(key=lambda t: t[0])
    for _, pg, h in hs:
        n = int(h['id'][1:]) if h['id'][1:].isdigit() else 0
        roof = [TILE, (176, 98, 66), (196, 108, 72), (162, 84, 58)][n % 4]
        prism(c, pg, 6 + 4 * hsh(n, 3), roof=roof, wall=(214, 196, 162))

# ---------- epic buildings ----------
def forum_founder(c, Y):
    F = c.poly_local(ST['forum_founder']['geom']['coords']); mese = c.line_local(ST['r_mese']['geom']['coords'])
    st, _, fr = phase('forum_founder', Y)
    if st == 'site': site(c, F, 41, 50)
    elif st == 'frame':   # paving half laid, column shafts standing, porticos not yet roofed
        site(c, F, 41, 30, stones=False)
        gap = mese.buffer(15, cap_style=2)
        inn = F.buffer(-12)
        laid = inn.intersection(box(0, 0, F.bounds[0] + (F.bounds[2] - F.bounds[0]) * (0.2 + 0.6 * fr), c.h))
        for p in polys(laid): c.d.polygon(c.T(p.exterior.coords), fill=(226, 218, 200, 255))
        band = F.difference(F.buffer(-11)).difference(gap)
        for p in polys(band): c.d.polygon(c.T(p.exterior.coords), fill=(200, 190, 168, 255))
        edge = F.buffer(-11).exterior.difference(gap)
        for ln in ([edge] if edge.geom_type == 'LineString' else list(getattr(edge, 'geoms', []))):
            for i in range(int(ln.length / 4.2) + 1):
                pt = ln.interpolate(i * 4.2)
                c.d.line([pt.x * SS, pt.y * SS, pt.x * SS, (pt.y - 13) * SS], fill=MARBLE + (255,), width=max(2, int(1.2 * SS)))
        scaffold(c, F.buffer(-5), 13, step=14)
    if st == 'done': c.d.polygon(c.T(F.exterior.coords), fill=(222, 214, 196, 255))
    inn = F.buffer(-12)
    x0, y0, x1, y1 = inn.bounds; k = 0
    if st != 'done': return column_founder(c, Y)
    for gy in np.arange(y0, y1, 4.2):     # radial-ish marble slabs
        for gx in np.arange(x0 + (3 if int(gy / 4.2) % 2 else 0), x1, 6.2):
            k += 1
            if not inn.contains(Point(gx + 3, gy + 2)): continue
            v = int(hsh(k, 7) * 18) - 9
            c.d.rectangle([gx * SS, gy * SS, (gx + 5.8) * SS, (gy + 3.8) * SS], fill=(234 + v, 228 + v, 214 + v, 255))
    gap = mese.buffer(15, cap_style=2)
    people(c, inn, 90, 41)
    band = F.difference(F.buffer(-11)).difference(gap)
    colonnade(c, band, 13, edge=F.buffer(-11).exterior.difference(gap))
    # two arched gates where the Mese enters and leaves
    for pt in F.exterior.intersection(mese.buffer(0.1)).geoms if hasattr(F.exterior.intersection(mese.buffer(0.1)), 'geoms') else []:
        pass
    hits = F.exterior.intersection(mese)
    hits = [hits] if hits.geom_type == 'Point' else list(getattr(hits, 'geoms', []))
    for pt in hits:
        t = mese.project(pt); p0, p1 = mese.interpolate(max(0, t - 3)), mese.interpolate(t + 3)
        ang = math.degrees(math.atan2(p1.y - p0.y, p1.x - p0.x))
        arch = affinity.translate(affinity.rotate(box(-7, -16, 7, 16), ang, origin=(0, 0)), pt.x, pt.y)
        prism(c, arch, 24, roof=MARBLE, wall=(220, 212, 194), ridge=False, outline=MARBLE_D)
        cx, cy = pt.x, pt.y + 7
        c.d.pieslice([(cx - 6) * SS, (cy - 17) * SS, (cx + 6) * SS, (cy - 5) * SS], 180, 360, fill=(74, 58, 42, 255))
        c.d.rectangle([(cx - 6) * SS, (cy - 11) * SS, (cx + 6) * SS, cy * SS], fill=(74, 58, 42, 255))
    column_founder(c, Y)

def column_founder(c, Y):
    # porphyry column: base, 7 drums with laurel bands, statue of the Founder
    st, _, fr = phase('col_founder', Y)
    if st is None: return
    x, y = c.P(*ST['col_founder']['geom']['coords'])
    H = 37 / M   # ~37 m column (historic order of magnitude) -> px
    c.d.polygon(c.T([(x, y), (x + 4, y), (x + 4 + H * 0.55, y + H * 0.38), (x + H * 0.55, y + H * 0.38)]), fill=(50, 34, 18, 110))
    prism(c, box(x - 7, y - 5, x + 7, y + 5), 9, roof=MARBLE, wall=(214, 206, 188), ridge=False)
    nd = 7 if st == 'done' else 0 if st == 'site' else min(6, 2 * (Y - ST['col_founder']['phases'][1]['year'] + 1))
    if st != 'done':   # crane beside the column, next drums lying on rollers
        crane(c, x + 9, y + 3, 9 + nd * (H - 14) / 7 + 14)
        for j in range(7 - nd):
            c.d.ellipse([(x - 16 + j * 4.5) * SS, (y + 8) * SS, (x - 12 + j * 4.5) * SS, (y + 11) * SS], fill=(118, 46, 52, 255))
        people(c, box(x - 18, y + 4, x + 18, y + 16), 10, 5)
    for i in range(nd):
        z0 = 9 + i * (H - 14) / 7; z1 = z0 + (H - 14) / 7
        c.d.rectangle([(x - 3.6) * SS, (y - z1) * SS, (x + 3.6) * SS, (y - z0) * SS], fill=(118, 46, 52, 255))
        c.d.rectangle([(x + 1.6) * SS, (y - z1) * SS, (x + 3.6) * SS, (y - z0) * SS], fill=(92, 34, 40, 255))
        c.d.rectangle([(x - 3.8) * SS, (y - z0 - 1) * SS, (x + 3.8) * SS, (y - z0) * SS], fill=(200, 170, 90, 255))
    if st != 'done': return
    c.d.rectangle([(x - 4.5) * SS, (y - H + 3) * SS, (x + 4.5) * SS, (y - H + 5) * SS], fill=MARBLE + (255,))
    c.d.rectangle([(x - 1.4) * SS, (y - H - 4) * SS, (x + 1.4) * SS, (y - H + 3) * SS], fill=(214, 176, 70, 255))
    c.d.ellipse([(x - 1.3) * SS, (y - H - 6.5) * SS, (x + 1.3) * SS, (y - H - 3.8) * SS], fill=(226, 190, 84, 255))
    for a in range(7):   # radiate crown
        t = math.pi * (0.15 + 0.7 * a / 6)
        c.d.line([x * SS, (y - H - 5) * SS, (x - math.cos(t) * 3) * SS, (y - H - 5 - math.sin(t) * 3) * SS], fill=(240, 206, 100, 255), width=SS)

def milion(c, Y):
    pg = c.poly_local(ST['milion']['geom']['coords']).buffer(4, join_style=2)
    st, _, fr = phase('milion', Y)
    if st is None: return
    if st == 'site': site(c, pg.buffer(6), 31, 6); scaffold(c, pg, 12, step=4); return
    if st == 'frame': site(c, pg.buffer(6), 31, 4, stones=False); rising(c, pg, 16, fr, 31, wall=(214, 206, 188)); return
    prism(c, pg, 16, roof=MARBLE, wall=(214, 206, 188), ridge=False, outline=MARBLE_D)
    x, y = pg.centroid.x, pg.centroid.y
    c.d.pieslice([(x - 3) * SS, (y - 11) * SS, (x + 3) * SS, (y - 5) * SS], 180, 360, fill=(70, 56, 40, 255))
    c.d.rectangle([(x - 3) * SS, (y - 8) * SS, (x + 3) * SS, y * SS], fill=(70, 56, 40, 255))
    dome(c, x, y - 2, 7, 16)

def hippodrome(c, Y):
    pts = [c.P(*p) for p in ST['hippodrome']['geom']['coords']]
    # long axis from carceres (north end, near the Mese) to sphendone (south)
    (a, b, cc, d_) = pts
    n_mid = ((a[0] + d_[0]) / 2, (a[1] + d_[1]) / 2); s_mid = ((b[0] + cc[0]) / 2, (b[1] + cc[1]) / 2)
    L = math.dist(n_mid, s_mid); Wd = math.dist(a, d_)
    ang = math.degrees(math.atan2(s_mid[1] - n_mid[1], s_mid[0] - n_mid[0]))
    cx, cy = (n_mid[0] + s_mid[0]) / 2, (n_mid[1] + s_mid[1]) / 2
    def place(g): return affinity.translate(affinity.rotate(g, ang, origin=(0, 0)), cx, cy)
    outer = place(unary_union([box(-L / 2, -Wd / 2, L / 2 - Wd / 2, Wd / 2), Point(L / 2 - Wd / 2, 0).buffer(Wd / 2)]))
    CV = 32
    arena = place(unary_union([box(-L / 2 + 14, -Wd / 2 + CV, L / 2 - Wd / 2, Wd / 2 - CV), Point(L / 2 - Wd / 2, 0).buffer(Wd / 2 - CV)]))
    cavea = outer.difference(arena)
    st, parts, fr = phase('hippodrome', Y)
    if st is None: return None
    if st == 'site':
        site(c, outer, 71, 90)
        c.d.polygon(c.T(arena.exterior.coords), fill=(190, 160, 112, 255))   # track being dug
        people(c, arena, 50, 73)
        return outer
    if st == 'frame':   # vaulted substructures of the stands rising ring by ring, track levelled, no crowd
        site(c, outer, 71, 30, stones=True)
        c.d.polygon(c.T(arena.exterior.coords), fill=(204, 176, 124, 255))
        nk = int(2 + 5 * fr)
        for k in range(nk):
            ring = arena.buffer(k * 4 + 4).difference(arena.buffer(k * 4)).intersection(cavea)
            tone = 196 - k * 3
            for p in polys(ring): c.d.polygon(c.T(p.exterior.coords, 3 + k * 2.4), fill=(tone, tone - 14, tone - 40, 255))
        for i in range(int(outer.exterior.length / 9)):   # radial vault piers of the outer ring
            q = outer.buffer(-3).exterior.interpolate(i * 9)
            c.d.pieslice([(q.x - 2.6) * SS, (q.y - 14) * SS, (q.x + 2.6) * SS, (q.y - 8) * SS], 180, 360, fill=(70, 56, 40, 255))
        for p in polys(outer.difference(outer.buffer(-3))): rising(c, p, 24, fr, 74, wall=(190, 170, 136))
        car = place(box(-L / 2, -Wd / 2 + 6, -L / 2 + 14, Wd / 2 - 6)); rising(c, car, 14, fr, 75)
        for t in (-0.25, 0.2):
            q = place(Point(L * t, Wd / 2 - 4)); crane(c, q.x, q.y, 30)
        people(c, arena, 30, 76)
        return outer
    shadow(c, outer, 22)
    c.d.polygon(c.T(arena.exterior.coords), fill=(214, 186, 130, 255))      # sand
    # spina with turning posts and statues
    spina = place(box(-L / 2 + 70, -2.5, L / 2 - Wd / 2 - 30, 2.5))
    prism(c, spina, 4, roof=(196, 190, 176), wall=(170, 160, 140), ridge=False)
    for t in (-L / 2 + 70, L / 2 - Wd / 2 - 40):
        p = place(Point(t, 0))
        for k in (-2, 0, 2):
            c.d.polygon(c.T([(p.x + k - 1, p.y), (p.x + k + 1, p.y), (p.x + k, p.y - 9)]), fill=(200, 170, 90, 255))
    for i in range(9):
        p = place(Point(-L / 2 + 90 + i * (L - Wd - 150) / 8, 0))
        c.d.rectangle([(p.x - 1) * SS, (p.y - 10) * SS, (p.x + 1) * SS, (p.y - 3) * SS], fill=(150, 120, 70, 255) if i % 2 else MARBLE + (255,))
    # chariot tracks
    for r_ in (8, 13):
        lane = place(unary_union([box(-L / 2 + 60, -r_, L / 2 - Wd / 2 - 30, r_)])).exterior
        c.d.line(c.T(lane.coords), fill=(190, 160, 108, 255), width=1)
    for i, col in enumerate([(30, 90, 170), (40, 140, 60), (200, 40, 40), (230, 230, 230)]):   # four factions' chariots
        p = place(Point(-L / 2 + 120 + i * 60, (-11 if i % 2 else 11)))
        c.d.ellipse([(p.x - 2) * SS, (p.y - 1.5) * SS, (p.x + 2) * SS, (p.y + 1.5) * SS], fill=col + (255,))
    # tiered stands: rings of seats stepping up toward the outer wall, packed with people
    for k in range(8):
        ring = arena.buffer(k * 4 + 4).difference(arena.buffer(k * 4)).intersection(cavea)
        tone = 214 - (k % 2) * 14 - k * 2
        for p in polys(ring): c.d.polygon(c.T(p.exterior.coords, 3 + k * 2.4), fill=(tone, tone - 8, tone - 26, 255))
    for p in polys(outer.difference(outer.buffer(-3))): prism(c, p, 24, roof=(200, 188, 164), wall=(190, 170, 136), ridge=False, sh=False)
    seats = arena.buffer(CV - 4).difference(arena.buffer(2)).intersection(cavea)
    cols = [(150, 60, 50), (60, 80, 120), (226, 220, 200), (110, 90, 60), (40, 110, 60), (30, 80, 160)]
    k = 0; x0, y0, x1, y1 = seats.bounds; n = 0
    while n < 900 and k < 9000:
        k += 1; px, py = x0 + hsh(k, 71) * (x1 - x0), y0 + hsh(k, 72) * (y1 - y0)
        if not seats.contains(Point(px, py)): continue
        dz = 3 + arena.exterior.distance(Point(px, py)) * 0.6
        col = cols[k % 6]; c.d.rectangle([(px - 0.6) * SS, (py - dz - 1) * SS, (px + 0.6) * SS, (py - dz + 0.3) * SS], fill=col + (255,)); n += 1
    # carceres (12 starting gates) at the north end
    car = place(box(-L / 2, -Wd / 2 + 6, -L / 2 + 14, Wd / 2 - 6))
    prism(c, car, 14, roof=TILE, wall=(206, 190, 160))
    for i in range(12):
        p = place(Point(-L / 2 + 14, -Wd / 2 + 12 + i * (Wd - 24) / 11))
        c.d.rectangle([(p.x - 1.2) * SS, (p.y - 5) * SS, (p.x + 1.2) * SS, p.y * SS], fill=(70, 54, 40, 255))
    # kathisma: imperial box on the palace (east) side, on the axis
    kp = place(Point(-L * 0.05, -Wd / 2 + 6))
    kb = place(box(-L * 0.05 - 14, -Wd / 2 - 2, -L * 0.05 + 14, -Wd / 2 + 10))
    if 'kathisma' in parts or not any(p.get('part') == 'kathisma' for p in ST['hippodrome']['phases']):
        prism(c, kb, 26, roof=LEAD, wall=MARBLE, ridge=True, outline=MARBLE_D)
    else:   # imperial box still in scaffolding; the races already run
        rising(c, kb, 26, 0.6, 77, wall=MARBLE)
    return outer

def palace(c, Y):
    pg = c.poly_local(ST['palace_great']['geom']['coords'])
    st, parts, fr = phase('palace_great', Y)
    if st is None: return None
    tdone = [st == 'done' or 'upper' in parts, st == 'done' or 'middle' in parts, st == 'done']
    if not any(tdone): site(c, pg, 90, 120); return pg
    shadow(c, pg, 10)
    # three terraces stepping down toward the sea (south-east)
    cen = pg.centroid; q = list(pg.exterior.coords)
    up = ((q[0][0] + q[1][0]) / 2, (q[0][1] + q[1][1]) / 2); dn = ((q[2][0] + q[3][0]) / 2, (q[2][1] + q[3][1]) / 2)
    ang = math.degrees(math.atan2(dn[1] - up[1], dn[0] - up[0]))
    L = math.dist(up, dn)
    for k in range(3):
        band = affinity.rotate(box(-L, -L / 2 + k * L / 3, L, -L / 2 + (k + 1) * L / 3), ang - 90, origin=(0, 0))
        band = affinity.translate(band, cen.x, cen.y).intersection(pg)
        hgt = 14 - k * 4
        if not tdone[k]:
            for p in polys(band): site(c, p, 90 + k, 40); scaffold(c, p.buffer(-8), 6 + 4 * k, step=16)
            continue
        for p in polys(band):
            prism(c, p, hgt, roof=[(204, 194, 170), (150, 160, 100), (196, 184, 156)][k], wall=(176, 156, 120), ridge=False, sh=False)
    # rows of halls and residences along each terrace
    for k in range(3):
        hgt = 14 - k * 4
        if not tdone[k]: continue
        for j in range(18):
            u = -L * 0.44 + (j % 9) * L * 0.11
            v = -L / 2 + k * L / 3 + L / 3 * ((0.22 if j < 9 else 0.68) + 0.1 * hsh(j + 19 * k, 2))
            bw, bd = 18 + 16 * hsh(j + 19 * k, 3), 12 + 8 * hsh(j + 19 * k, 4)
            if hsh(j + 19 * k, 8) < 0.25: continue
            b = affinity.rotate(box(u - bw / 2, v - bd / 2, u + bw / 2, v + bd / 2), ang - 90, origin=(0, 0))
            b = affinity.translate(b, cen.x, cen.y)
            if not pg.buffer(-6).contains(b): continue
            prism(c, affinity.translate(b, 0, -hgt), 10 + 6 * hsh(j + 9 * k, 6), roof=[TILE, (196, 100, 68), LEAD][(j + k) % 3], wall=(226, 214, 190))
    # gardens and courts on terraces
    rng = [(0.25, 0.22), (0.62, 0.3), (0.35, 0.55), (0.7, 0.62), (0.45, 0.82)]
    x0, y0, x1, y1 = pg.bounds
    for i, (fx, fy) in enumerate(rng):
        cx_, cy_ = x0 + fx * (x1 - x0), y0 + fy * (y1 - y0)
        if not pg.buffer(-20).contains(Point(cx_, cy_)): continue
        if not tdone[min(2, int(fy * 3))]: continue
        hgt = 14 - 4 * min(2, int(fy * 3))
        court = box(cx_ - 22, cy_ - 16, cx_ + 22, cy_ + 16)
        # peristyle court: roofs around, garden in the middle
        ring = court.difference(court.buffer(-6, join_style=2))
        c.d.rectangle([(cx_ - 16) * SS, (cy_ - 10 - hgt) * SS, (cx_ + 16) * SS, (cy_ + 10 - hgt) * SS], fill=(98, 128, 70, 255))
        for t in range(6):
            tx, ty = cx_ - 12 + hsh(i * 9 + t, 4) * 24, cy_ - 7 + hsh(i * 9 + t, 5) * 14
            c.d.ellipse([(tx - 2.5) * SS, (ty - hgt - 3) * SS, (tx + 2.5) * SS, (ty - hgt + 1) * SS], fill=(62, 98, 50, 255))
        c.d.ellipse([(cx_ - 3) * SS, (cy_ - hgt - 2) * SS, (cx_ + 3) * SS, (cy_ - hgt + 2) * SS], fill=(110, 160, 180, 255))
        for p in polys(ring): prism(c, affinity.translate(p, 0, -hgt), 9, roof=TILE, wall=MARBLE, ridge=False, sh=False)
    # great halls: an audience hall with apse, a domed triclinium, the Chalke gate toward the Augusteion
    hall = affinity.translate(affinity.rotate(box(-30, -12, 30, 12), ang, origin=(0, 0)), cen.x - 10, cen.y - 24)
    if tdone[0]: prism(c, hall, 30, roof=TILE, wall=(222, 210, 186))
    if tdone[1]: dome(c, cen.x + 30, cen.y + 10, 13, 18, drum=6)
    elif tdone[0]: rising(c, Point(cen.x + 30, cen.y + 10).buffer(13), 18, 0.5, 93)
    gate = affinity.translate(box(-14, -8, 14, 8), up[0] + 6, up[1] + 6)
    if tdone[0]:
        prism(c, gate, 24, roof=LEAD, wall=MARBLE, ridge=False, outline=MARBLE_D)
        dome(c, gate.centroid.x, gate.centroid.y, 8, 24)
    # sea wall along the lower terrace
    low = LineString([q[2], q[3]]).buffer(3, cap_style=2)
    if tdone[2]: prism(c, low, 12, roof=(196, 180, 150), wall=(170, 150, 118), ridge=False)
    else: rising(c, low, 12, 0.3 + 0.2 * tdone[1], 94, wall=(170, 150, 118))
    return pg

def basilica(c, coords, Y, name, atrium=True, length_k=1.0, roof_h=26, wonder=False, sid=None):
    pg = c.poly_local(coords)
    st, _, fr = phase(sid, Y) if sid else ('done', set(), 1.0)
    if st is None: return None
    if st != 'done':
        site(c, pg.buffer(4), 60 + len(name), 40 if st == 'site' else 20, stones=True)
        if wonder:   # foundation trench lined with the reused Byzas wall blocks
            ring = pg.buffer(-2, join_style=2).exterior
            for k in range(int(ring.length / 5)):
                q = ring.interpolate(k * 5)
                c.d.rectangle([(q.x - 2.2) * SS, (q.y - 1.4) * SS, (q.x + 2.2) * SS, (q.y + 0.4) * SS], fill=(168, 150, 116, 255) if k % 2 else (186, 168, 132, 255))
        if st == 'frame':
            rising(c, pg.buffer(-1, join_style=2), roof_h * 0.62, fr, 61 + len(name))
            cx, cy = pg.centroid.x, pg.centroid.y; crane(c, cx, cy + 6, roof_h + 14)
        return pg.buffer(2)
    q = list(pg.minimum_rotated_rectangle.exterior.coords)[:4]
    e = [(q[i], q[(i + 1) % 4]) for i in range(4)]
    i = 0 if math.dist(*e[0]) >= math.dist(*e[1]) else 1
    a, b = e[i]
    ang = math.atan2(b[1] - a[1], b[0] - a[0])
    if math.cos(ang) < 0: ang += math.pi      # point east (apse)
    L, Wd = math.dist(*e[i]), math.dist(*e[(i + 1) % 4])
    cen = pg.centroid
    def place(g): return affinity.translate(affinity.rotate(g, ang, origin=(0, 0), use_radians=True), cen.x, cen.y)
    at = L * 0.28 if atrium else 0
    if atrium:   # colonnaded forecourt with a fountain
        court = place(box(-L / 2, -Wd / 2, -L / 2 + at, Wd / 2))
        c.d.polygon(c.T(court.exterior.coords), fill=(214, 204, 184, 255))
        colonnade(c, court.difference(court.buffer(-5, join_style=2)), 9)
        f = place(Point(-L / 2 + at / 2, 0)); c.d.ellipse([(f.x - 3) * SS, (f.y - 2) * SS, (f.x + 3) * SS, (f.y + 2) * SS], fill=(110, 160, 180, 255))
    aisles = place(box(-L / 2 + at, -Wd / 2, L / 2 - Wd * 0.18, Wd / 2))
    prism(c, aisles, roof_h * 0.62, roof=TILE, wall=(214, 196, 166), ridge=False)
    nave = place(box(-L / 2 + at - 1, -Wd * (0.2 if wonder else 0.24), L / 2 - Wd * 0.18, Wd * (0.2 if wonder else 0.24)))
    prism(c, nave, roof_h, roof=(196, 100, 68), wall=(222, 206, 176))
    # clerestory windows on the south wall
    for k in range(int((L - at) / 7)):
        p = place(Point(-L / 2 + at + 4 + k * 7, Wd * (0.2 if wonder else 0.24)))
        c.d.rectangle([(p.x - 0.8) * SS, (p.y - roof_h + 3) * SS, (p.x + 0.8) * SS, (p.y - roof_h * 0.68) * SS], fill=(60, 48, 36, 255))
    ap = place(Point(L / 2 - Wd * 0.18, 0)).buffer(Wd * 0.22)
    prism(c, ap.difference(place(box(-L, -Wd, L / 2 - Wd * 0.18, Wd))), roof_h * 0.7, roof=LEAD, wall=(214, 196, 166), ridge=False)
    if wonder:   # foundation courses of reused Byzas wall blocks along the south flank
        for k in range(int((L - at) / 5)):
            p = place(Point(-L / 2 + at + k * 5, Wd / 2 + 1.5))
            c.d.rectangle([(p.x - 2.2) * SS, (p.y - 1.4) * SS, (p.x + 2.2) * SS, (p.y + 0.4) * SS], fill=(168, 150, 116, 255) if k % 2 else (186, 168, 132, 255))
    return pg.buffer(2)

def agora(c, Y):
    pg = c.poly_local(ST['agora_tetrastoon']['geom']['coords'])
    c.d.polygon(c.T(pg.exterior.coords), fill=(214, 204, 182, 255))
    people(c, pg.buffer(-8), 30, 17)
    colonnade(c, pg.difference(pg.buffer(-7, join_style=2)), 10, edge=pg.buffer(-7, join_style=2).exterior)
    return pg

def cistern(c, Y):
    pg = c.poly_local(ST['cistern_founder']['geom']['coords'])
    c.d.polygon(c.T(pg.exterior.coords), fill=(196, 188, 170, 255))
    x0, y0, x1, y1 = pg.buffer(-8).bounds
    for i in range(3):
        for j in range(3):
            x, y = x0 + (i + 0.5) * (x1 - x0) / 3, y0 + (j + 0.5) * (y1 - y0) / 3
            c.d.ellipse([(x - 3) * SS, (y - 2.2) * SS, (x + 3) * SS, (y + 2.2) * SS], fill=(150, 140, 120, 255))
            c.d.ellipse([(x - 1.8) * SS, (y - 1.3) * SS, (x + 1.8) * SS, (y + 1.3) * SS], fill=(40, 70, 86, 255))
    return pg

def acropolis(c, Y):
    pg = c.poly_local(ST['fort_acropolis']['geom']['coords'])
    for p in polys(pg.difference(pg.buffer(-6, join_style=2)).intersection(box(0, 0, c.w, c.h))): prism(c, p, 14, roof=(190, 176, 146), wall=(160, 140, 110), ridge=False)
    return pg

def mese_porticoes(c, Y, cut):
    if Y < 1: return
    ln = c.line_local(ST['r_mese']['geom']['coords']); w = ST['r_mese']['width'] * S
    for side in (1, -1):
        band = ln.buffer(w / 2 + 7, cap_style=2, single_sided=False).difference(ln.buffer(w / 2, cap_style=2))
        off = ln.parallel_offset(w / 2 + 0.5, 'left' if side > 0 else 'right')
        half = band.intersection(ln.parallel_offset(w / 2 + 3.5, 'left' if side > 0 else 'right').buffer(3.6, cap_style=2))
        half = half.difference(cut)
        if Y < 3:   # first years: timber scaffolding and column drums lying ready
            for p in polys(half): c.d.polygon(c.T(p.exterior.coords), fill=(196, 176, 140, 255))
            for i in range(int(ln.length / 9)):
                pt = off.interpolate(i * 9)
                if cut.contains(pt): continue
                c.d.line([pt.x * SS, pt.y * SS, pt.x * SS, (pt.y - 11) * SS], fill=(130, 98, 60, 255), width=SS)
        else:
            colonnade(c, half, 11, edge=off.difference(cut) if not off.is_empty else None)

def render_core(Y, out):
    c = Canvas(598, 436, 706, 512)
    ground(c, Y)
    epic = []
    if Y >= 1: epic += [c.poly_local(ST[k]['geom']['coords']) for k in ('forum_founder', 'hippodrome', 'palace_great', 'church_peace')]
    if Y >= 30: epic.append(c.poly_local(ST['church_megale']['geom']['coords']))
    keep = unary_union([e.buffer(3) for e in epic]) if epic else None
    roads(c, Y)
    order = []
    walls(c, Y)
    occ = [Point(c.P(h['cx'], h['cz'])).buffer(18) for h in D['houses'] if h['built'] <= Y and (h['destroyed'] is None or h['destroyed'] > Y) and c.x0 - 3 < h['cx'] < c.x0 + c.w / S + 3 and c.z0 - 3 < h['cz'] < c.z0 + c.h / S + 3]
    occ += [c.line_local(s['geom']['coords']).buffer(s.get('width', 1.2) * S / 2 + 4) for s in W['structures'] if s['type'] == 'road' and alive(s, Y)]
    occ += [c.poly_local(s['geom']['coords']).buffer(14) for s in W['structures'] if s['geom']['type'] == 'polygon' and alive(s, Y) and s['type'] not in ('district', 'farmland')]
    trees(c, Y, unary_union(occ))
    houses(c, Y, keep)
    agora(c, Y); acropolis(c, Y)
    if Y >= 1:
        cistern(c, Y)
        mese_porticoes(c, Y, unary_union([c.poly_local(ST['forum_founder']['geom']['coords']).buffer(2), c.poly_local(ST['agora_tetrastoon']['geom']['coords']).buffer(6)]))
        palace(c, Y); hippodrome(c, Y)
        basilica(c, ST['church_peace']['geom']['coords'], Y, 'peace', atrium=True, roof_h=24, sid='church_peace')
        if Y >= 30: basilica(c, ST['church_megale']['geom']['coords'], Y, 'megale', atrium=True, roof_h=34, wonder=True, sid='church_megale')
        forum_founder(c, Y); milion(c, Y)
    img = c.im.resize((c.w, c.h), Image.LANCZOS).convert('RGB')
    d = ImageDraw.Draw(img); d.rectangle([8, 8, 128, 34], fill=(30, 24, 18)); d.text((16, 14), f'AF {Y}', fill=(240, 224, 190))
    img.save(out, quality=88); return out

def render_apostles(Y, out):
    c = Canvas(441, 334, 481, 366)
    ground(c, Y); roads(c, Y); walls(c, Y)
    pg = c.poly_local(ST['church_apostles']['geom']['coords'])
    houses(c, Y, pg.buffer(18) if Y >= 11 else None)
    for s in W['structures']:
        if s['type'] == 'aqueduct' and alive(s, Y):
            ln = c.line_local(s['geom']['coords'])
            for p in polys(ln.buffer(4, cap_style=2).intersection(box(0, 0, c.w, c.h))): prism(c, p, 20, roof=(186, 176, 150), wall=(168, 150, 118), ridge=False)
            sline = ln.parallel_offset(4, 'right')
            for i in range(int(ln.length / 9)):
                q = ln.interpolate(i * 9)
                if 0 < q.x < c.w and 0 < q.y < c.h:
                    c.d.pieslice([(q.x - 2.6) * SS, (q.y + 4 - 18) * SS, (q.x + 2.6) * SS, (q.y + 4 - 12) * SS], 180, 360, fill=(70, 56, 40, 255))
                    c.d.rectangle([(q.x - 2.6) * SS, (q.y + 4 - 15) * SS, (q.x + 2.6) * SS, (q.y + 4) * SS], fill=(70, 56, 40, 255))
    if Y >= 11:
        cen = pg.centroid; x0, y0, x1, y1 = pg.bounds; arm = (x1 - x0) / 2; thick = arm * 0.36
        c.d.polygon(c.T(pg.buffer(16, join_style=2).exterior.coords), fill=(208, 198, 176, 255))   # precinct paving
        arms = [box(cen.x - arm, cen.y - thick, cen.x + arm, cen.y + thick), box(cen.x - thick, cen.y - arm, cen.x + thick, cen.y + arm)]
        mx, my = cen.x + arm + 22, cen.y
        shadow(c, unary_union(arms + [Point(mx, my).buffer(18, 24)]), 28)
        st, parts, fr = phase('church_apostles', Y)
        cross = unary_union(arms)
        if st == 'done':
            for g in sorted(arms, key=lambda g: -g.bounds[2] + g.bounds[0]):
                prism(c, g, 28, roof=(194, 98, 66), wall=(222, 206, 176), sh=False)
            dome(c, cen.x, cen.y, thick * 1.1, 28, drum=10)
        elif st == 'frame':
            site(c, cross.buffer(3), 111, 10, stones=True); rising(c, cross, 28, fr, 112); crane(c, cen.x, cen.y + 4, 44)
        else:
            site(c, cross.buffer(3), 111, 30)
        # the Founder's mausoleum: a rotunda against the east arm, finished first
        rot = Point(mx, my).buffer(18, 24)
        if st == 'done' or 'mausoleum' in parts:
            prism(c, rot, 22, roof=LEAD, wall=(220, 210, 190), ridge=False, sh=False)
            dome(c, mx, my, 17, 22)
        else:
            site(c, rot.buffer(2), 113, 8, stones=False); rising(c, rot, 22, fr, 114)
        people(c, pg.buffer(15).difference(pg.buffer(2)), 40, 9)
    img = c.im.resize((c.w, c.h), Image.LANCZOS).convert('RGB')
    d = ImageDraw.Draw(img); d.rectangle([8, 8, 128, 34], fill=(30, 24, 18)); d.text((16, 14), f'AF {Y}', fill=(240, 224, 190))
    img.save(out, quality=88); return out

# ---------- harbors, granaries, walls & gates ----------
def ship(c, x, y, ang, L=26, sail=True, seed=0):
    hull = affinity.translate(affinity.rotate(Polygon([(-L / 2, -3.5), (L / 2 - 5, -3.5), (L / 2, 0), (L / 2 - 5, 3.5), (-L / 2, 3.5), (-L / 2 - 2, 0)]), ang, origin=(0, 0)), x, y)
    shadow(c, hull, 4, a=50)
    c.d.polygon(c.T(hull.exterior.coords), fill=(110, 76, 46, 255))
    inner = hull.buffer(-1.4)
    if not inner.is_empty:
        for p in polys(inner): c.d.polygon(c.T(p.exterior.coords), fill=(156, 118, 76, 255))
    if sail:
        m = affinity.translate(affinity.rotate(Point(-L * 0.05, 0), ang, origin=(0, 0)), x, y)
        a = math.radians(ang + 90)
        sw = L * 0.42
        p1 = (m.x + math.cos(a) * sw / 2, m.y + math.sin(a) * sw / 2); p2 = (m.x - math.cos(a) * sw / 2, m.y - math.sin(a) * sw / 2)
        col = [(236, 228, 206), (226, 206, 170), (200, 120, 90)][seed % 3]
        c.d.polygon(c.T([p1, p2, (p2[0], p2[1] - 14), (p1[0], p1[1] - 14)]), fill=col + (235,))
        c.d.line(c.T([(m.x, m.y), (m.x, m.y - 17)]), fill=(80, 56, 36, 255), width=SS)
    for k in range(3):   # cargo: amphorae / grain sacks
        q = affinity.translate(affinity.rotate(Point(-L * 0.3 + k * 4, 0), ang, origin=(0, 0)), x, y)
        c.d.ellipse([(q.x - 1.3) * SS, (q.y - 1.6) * SS, (q.x + 1.3) * SS, (q.y + 0.6) * SS], fill=(214, 196, 150, 255))

def harbor(c, sid, Y, nships, seed):
    s = ST[sid]; pg = c.poly_local(s['geom']['coords'])
    x0, y0, x1, y1 = pg.bounds
    basin = box(x0 + 14, y0 + 12, x1 - 14, y1 - 4)
    c.d.polygon(c.T(pg.exterior.coords), fill=(198, 188, 164, 255))          # quay apron
    c.d.polygon(c.T(basin.exterior.coords), fill=(58, 106, 124, 255))        # still water
    for i in range(30):
        wx, wy = x0 + 16 + hsh(i, seed) * (x1 - x0 - 32), y0 + 14 + hsh(i, seed + 1) * (y1 - y0 - 20)
        c.d.line([wx * SS, wy * SS, (wx + 5) * SS, wy * SS], fill=(96, 146, 160, 200), width=1)
    # quay edge stones on the land (north) side, bollards, sacks, porters
    c.d.line(c.T([(basin.bounds[0], basin.bounds[1]), (basin.bounds[2], basin.bounds[1])]), fill=(150, 138, 112, 255), width=3 * SS)
    for i in range(int((x1 - x0) / 14)):
        bx = x0 + 18 + i * 14
        if bx > x1 - 18: break
        c.d.ellipse([(bx - 1) * SS, (y0 + 9) * SS, (bx + 1) * SS, (y0 + 11) * SS], fill=(80, 70, 56, 255))
        if hsh(i, seed + 3) < 0.6:
            for k in range(3): c.d.ellipse([(bx + 3 + k * 2.2) * SS, (y0 + 3) * SS, (bx + 5 + k * 2.2) * SS, (y0 + 5.5) * SS], fill=(214, 196, 150, 255))
    people(c, box(x0 + 4, y0 + 1, x1 - 4, y0 + 11), 50, seed + 5)
    # rubble moles closing the basin to the sea, with a gap for ships
    gap = (x0 + x1) / 2
    for a, b in (((x0, y1), (gap - 14, y1)), ((gap + 14, y1), (x1, y1))):
        mole = LineString([a, b]).buffer(5, cap_style=1)
        prism(c, mole, 4, roof=(170, 160, 140), wall=(140, 128, 108), ridge=False)
        for i in range(int(mole.length / 6)):
            q = LineString([a, b]).interpolate(i * 3)
            c.d.ellipse([(q.x - 1.6) * SS, (q.y - 5.5) * SS, (q.x + 1.6) * SS, (q.y - 3.5) * SS], fill=(186, 176, 156, 255))
    for side in (x0 + 6, x1 - 6):
        prism(c, LineString([(side, y0 + 10), (side, y1)]).buffer(5, cap_style=2), 4, roof=(178, 168, 146), wall=(140, 128, 108), ridge=False)
    for k, (gx_) in enumerate((gap - 15, gap + 15)):   # small light towers on the mole heads
        prism(c, Point(gx_, y1).buffer(4.5, 12), 14, roof=(200, 190, 170), wall=(176, 162, 136), ridge=False)
        c.d.ellipse([(gx_ - 1.5) * SS, (y1 - 17) * SS, (gx_ + 1.5) * SS, (y1 - 14) * SS], fill=(240, 190, 90, 255))
    bb = basin.buffer(-10)
    for i in range(nships):   # moored ships along the quay, a couple swinging in the basin
        if i < nships * 0.7:
            x = bb.bounds[0] + 10 + i * (bb.bounds[2] - bb.bounds[0] - 20) / max(1, int(nships * 0.7)); y = bb.bounds[1] + 2; ang = 90 + (hsh(i, seed) - 0.5) * 10
        else:
            x = bb.bounds[0] + hsh(i, seed + 7) * (bb.bounds[2] - bb.bounds[0]); y = bb.bounds[1] + 16 + hsh(i, seed + 8) * max(1, bb.bounds[3] - bb.bounds[1] - 18); ang = hsh(i, seed + 9) * 180
        ship(c, x, y + 12, ang, L=24 + 8 * hsh(i, seed + 2), sail=hsh(i, seed + 4) < 0.45, seed=i)
    return pg

def horrea(c, sid, Y):
    s = ST[sid]; pg = c.poly_local(s['geom']['coords'])
    q = list(pg.minimum_rotated_rectangle.exterior.coords)[:4]
    e = [(q[i], q[(i + 1) % 4]) for i in range(4)]; i = 0 if math.dist(*e[0]) >= math.dist(*e[1]) else 1
    a, b = e[i]; ang = math.atan2(b[1] - a[1], b[0] - a[0]); L, Wd = math.dist(*e[i]), math.dist(*e[(i + 1) % 4])
    cen = pg.centroid
    def place(g): return affinity.translate(affinity.rotate(g, ang, origin=(0, 0), use_radians=True), cen.x, cen.y)
    court = place(box(-L / 2 + 10, -Wd / 2 + 10, L / 2 - 10, Wd / 2 - 10))
    shadow(c, pg, 16)
    c.d.polygon(c.T(pg.exterior.coords), fill=(200, 188, 162, 255))
    # ranges of vaulted store rooms around a courtyard, buttressed outer walls, tiled roofs with ridge
    ranges = [place(box(-L / 2, -Wd / 2, L / 2, -Wd / 2 + 10)), place(box(-L / 2, Wd / 2 - 10, L / 2, Wd / 2)),
              place(box(-L / 2, -Wd / 2 + 10, -L / 2 + 10, Wd / 2 - 10)), place(box(L / 2 - 10, -Wd / 2 + 10, L / 2, Wd / 2 - 10))]
    for r in sorted(ranges, key=lambda g: g.centroid.y): prism(c, r, 16, roof=TILE, wall=(204, 178, 140), sh=False)
    for k in range(int(L / 7)):     # store-room doors and buttresses on the south face
        p = place(Point(-L / 2 + 4 + k * 7, Wd / 2))
        c.d.rectangle([(p.x - 1.2) * SS, (p.y - 6) * SS, (p.x + 1.2) * SS, p.y * SS], fill=(76, 56, 38, 255))
    if not court.is_empty:
        people(c, court, int(court.area / 90), 61)
        for k in range(int(court.area / 160)):   # grain carts
            p = court.representative_point() if k == 0 else Point(court.bounds[0] + hsh(k, 63) * (court.bounds[2] - court.bounds[0]), court.bounds[1] + hsh(k, 64) * (court.bounds[3] - court.bounds[1]))
            if not court.contains(p): continue
            c.d.rectangle([(p.x - 3) * SS, (p.y - 2) * SS, (p.x + 3) * SS, (p.y + 1) * SS], fill=(120, 86, 52, 255))
            c.d.ellipse([(p.x - 2.5) * SS, (p.y - 3.5) * SS, (p.x + 2.5) * SS, (p.y - 0.5) * SS], fill=(220, 200, 150, 255))
    return pg

def city_wall(c, Y, gate_poly=None):
    s = ST['wall_founder']; ln = c.line_local(s['geom']['coords'])
    cut = gate_poly.buffer(6) if gate_poly is not None else Point(-99, -99).buffer(1)
    band = ln.buffer(9, cap_style=2).difference(cut)
    for p in polys(band.intersection(box(-50, -50, c.w + 50, c.h + 50))): prism(c, p, 22, roof=(146, 140, 130), wall=(196, 182, 156), ridge=False, outline=(110, 104, 96))
    # crenellations on the parapet
    off = ln.parallel_offset(7, 'right')
    for i in range(int(ln.length / 4)):
        q = off.interpolate(i * 4)
        if cut.contains(q) or not (0 < q.x < c.w and 0 < q.y < c.h): continue
        c.d.rectangle([(q.x - 1) * SS, (q.y - 25) * SS, (q.x + 1) * SS, (q.y - 22) * SS], fill=(232, 226, 212, 255))
    for i in range(int(ln.length / 64)):   # square towers every ~55 m
        q = ln.interpolate(i * 64 + 30)
        if cut.buffer(10).contains(q) or not (-20 < q.x < c.w + 20 and -20 < q.y < c.h + 20): continue
        t = affinity.rotate(box(q.x - 11, q.y - 11, q.x + 11, q.y + 11), 12, origin=(q.x, q.y))
        prism(c, t, 34, roof=(132, 126, 118), wall=(200, 186, 160), ridge=False, outline=(96, 90, 84))
        for k in range(5):
            c.d.rectangle([(q.x - 10 + k * 4.5) * SS, (q.y - 39) * SS, (q.x - 8 + k * 4.5) * SS, (q.y - 35) * SS], fill=(232, 226, 212, 255))
    return ln.buffer(10)

def gate(c, Y):
    pg = c.poly_local(ST['gate_founder']['geom']['coords']); cx, cy = pg.centroid.x, pg.centroid.y
    for dx in (-22, 22):    # two flanking towers
        t = Point(cx + dx * 0.25, cy + dx).buffer(17, 8)
        prism(c, t, 46, roof=(132, 126, 118), wall=(214, 200, 172), ridge=False, outline=(96, 90, 84))
    body = affinity.rotate(box(cx - 10, cy - 14, cx + 10, cy + 14), 12, origin=(cx, cy))
    prism(c, body, 34, roof=MARBLE, wall=(214, 204, 184), ridge=False, outline=MARBLE_D)
    c.d.pieslice([(cx - 7) * SS, (cy + 12 - 26) * SS, (cx + 7) * SS, (cy + 12 - 12) * SS], 180, 360, fill=(60, 46, 34, 255))
    c.d.rectangle([(cx - 7) * SS, (cy + 12 - 19) * SS, (cx + 7) * SS, (cy + 12) * SS], fill=(60, 46, 34, 255))
    # traffic through the gate: carts and walkers on the Mese
    for k in range(6):
        px, py = cx - 30 + k * 12 + hsh(k, 91) * 4, cy + (hsh(k, 92) - 0.5) * 10
        c.d.rectangle([(px - 3) * SS, (py - 1.5) * SS, (px + 3) * SS, (py + 1.5) * SS], fill=(120, 86, 52, 255)) if k % 2 else c.d.ellipse([(px - 0.8) * SS, (py - 1.6) * SS, (px + 0.8) * SS, (py + 0.3) * SS], fill=(150, 60, 50, 255))
    return pg

def barracks(c, Y):
    pg = c.poly_local(ST['barracks_gate']['geom']['coords'])
    ring = pg.difference(pg.buffer(-11, join_style=2))
    c.d.polygon(c.T(pg.exterior.coords), fill=(196, 184, 158, 255))
    inner = pg.buffer(-11, join_style=2)
    for i in range(14):   # soldiers drilling in rows
        x0, y0, x1, y1 = inner.bounds
        px, py = x0 + 6 + (i % 7) * (x1 - x0 - 12) / 6, y0 + 8 + (i // 7) * 8
        c.d.ellipse([(px - 0.8) * SS, (py - 1.6) * SS, (px + 0.8) * SS, (py + 0.3) * SS], fill=(160, 40, 40, 255))
    prism(c, ring, 14, roof=TILE, wall=(206, 186, 150))
    return pg

def render_shore(Y, out):
    c = Canvas(462, 486, 596, 536)
    ground(c, Y); roads(c, Y)
    epic = [c.poly_local(ST[k]['geom']['coords']) for k in ('harbor_julian', 'granary_founder', 'harbor_theodosius', 'horrea_theodosius', 'horrea_alexandrina') if alive(ST[k], Y)]
    keep = unary_union([e.buffer(3) for e in epic]) if epic else None
    occ = [Point(c.P(h['cx'], h['cz'])).buffer(18) for h in D['houses'] if h['built'] <= Y and (h['destroyed'] is None or h['destroyed'] > Y) and c.x0 - 3 < h['cx'] < c.x0 + c.w / S + 3 and c.z0 - 3 < h['cz'] < c.z0 + c.h / S + 3]
    occ += [c.line_local(s['geom']['coords']).buffer(s.get('width', 1.2) * S / 2 + 4) for s in W['structures'] if s['type'] == 'road' and alive(s, Y)]
    occ += [e.buffer(14) for e in epic]
    trees(c, Y, unary_union(occ))
    houses(c, Y, keep)
    if alive(ST['harbor_julian'], Y): harbor(c, 'harbor_julian', Y, 15, 201)
    if alive(ST['harbor_theodosius'], Y): harbor(c, 'harbor_theodosius', Y, 9, 301)
    for k in ('granary_founder', 'horrea_theodosius', 'horrea_alexandrina'):
        if alive(ST[k], Y): horrea(c, k, Y)
    img = c.im.resize((c.w, c.h), Image.LANCZOS).convert('RGB')
    d = ImageDraw.Draw(img); d.rectangle([8, 8, 128, 34], fill=(30, 24, 18)); d.text((16, 14), f'AF {Y}', fill=(240, 224, 190))
    img.save(out, quality=88); return out

def render_gate(Y, out):
    c = Canvas(396, 452, 444, 494)
    ground(c, Y); roads(c, Y)
    g = c.poly_local(ST['gate_founder']['geom']['coords'])
    wall_zone = c.line_local(ST['wall_founder']['geom']['coords']).buffer(26) if Y >= 1 else None
    ep = [g.buffer(20)] + ([c.poly_local(ST['barracks_gate']['geom']['coords']).buffer(3)] if alive(ST['barracks_gate'], Y) else [])
    keep = unary_union(ep + ([wall_zone] if wall_zone is not None else []))
    occ = [Point(c.P(h['cx'], h['cz'])).buffer(18) for h in D['houses'] if h['built'] <= Y and (h['destroyed'] is None or h['destroyed'] > Y) and c.x0 - 3 < h['cx'] < c.x0 + c.w / S + 3 and c.z0 - 3 < h['cz'] < c.z0 + c.h / S + 3]
    occ += [c.line_local(s['geom']['coords']).buffer(s.get('width', 1.2) * S / 2 + 4) for s in W['structures'] if s['type'] == 'road' and alive(s, Y)]
    trees(c, Y, unary_union(occ + [keep]))
    houses(c, Y, keep)
    if alive(ST['barracks_gate'], Y): barracks(c, Y)
    if Y >= 1:
        city_wall(c, Y, g); gate(c, Y)
    img = c.im.resize((c.w, c.h), Image.LANCZOS).convert('RGB')
    d = ImageDraw.Draw(img); d.rectangle([8, 8, 128, 34], fill=(30, 24, 18)); d.text((16, 14), f'AF {Y}', fill=(240, 224, 190))
    img.save(out, quality=88); return out

if __name__ == '__main__':
    what = sys.argv[1]; ys = [int(v) for v in sys.argv[2:]]
    for Y in ys:
        f = {'core': render_core, 'apostles': render_apostles, 'shore': render_shore, 'gate': render_gate}[what](Y, f'/tmp/epic_{what}_af{Y}.jpg'); print(f)
