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
        nx, ny = (by - ay), -(bx - ax)   # outward normal for cw ring (y down)
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
    c.d.polygon(c.T(F.exterior.coords), fill=(222, 214, 196, 255))
    inn = F.buffer(-12)
    x0, y0, x1, y1 = inn.bounds; k = 0
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
    # porphyry column: base, 7 drums with laurel bands, statue of the Founder
    x, y = c.P(*ST['col_founder']['geom']['coords'])
    H = 37 / M   # ~37 m column (historic order of magnitude) -> px
    c.d.polygon(c.T([(x, y), (x + 4, y), (x + 4 + H * 0.55, y + H * 0.38), (x + H * 0.55, y + H * 0.38)]), fill=(50, 34, 18, 110))
    prism(c, box(x - 7, y - 5, x + 7, y + 5), 9, roof=MARBLE, wall=(214, 206, 188), ridge=False)
    for i in range(7):
        z0 = 9 + i * (H - 14) / 7; z1 = z0 + (H - 14) / 7
        c.d.rectangle([(x - 3.6) * SS, (y - z1) * SS, (x + 3.6) * SS, (y - z0) * SS], fill=(118, 46, 52, 255))
        c.d.rectangle([(x + 1.6) * SS, (y - z1) * SS, (x + 3.6) * SS, (y - z0) * SS], fill=(92, 34, 40, 255))
        c.d.rectangle([(x - 3.8) * SS, (y - z0 - 1) * SS, (x + 3.8) * SS, (y - z0) * SS], fill=(200, 170, 90, 255))
    c.d.rectangle([(x - 4.5) * SS, (y - H + 3) * SS, (x + 4.5) * SS, (y - H + 5) * SS], fill=MARBLE + (255,))
    c.d.rectangle([(x - 1.4) * SS, (y - H - 4) * SS, (x + 1.4) * SS, (y - H + 3) * SS], fill=(214, 176, 70, 255))
    c.d.ellipse([(x - 1.3) * SS, (y - H - 6.5) * SS, (x + 1.3) * SS, (y - H - 3.8) * SS], fill=(226, 190, 84, 255))
    for a in range(7):   # radiate crown
        t = math.pi * (0.15 + 0.7 * a / 6)
        c.d.line([x * SS, (y - H - 5) * SS, (x - math.cos(t) * 3) * SS, (y - H - 5 - math.sin(t) * 3) * SS], fill=(240, 206, 100, 255), width=SS)

def milion(c, Y):
    pg = c.poly_local(ST['milion']['geom']['coords']).buffer(4, join_style=2)
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
    prism(c, kb, 26, roof=LEAD, wall=MARBLE, ridge=True, outline=MARBLE_D)
    return outer

def palace(c, Y):
    pg = c.poly_local(ST['palace_great']['geom']['coords'])
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
        for p in polys(band):
            prism(c, p, hgt, roof=[(204, 194, 170), (150, 160, 100), (196, 184, 156)][k], wall=(176, 156, 120), ridge=False, sh=False)
    # rows of halls and residences along each terrace
    for k in range(3):
        hgt = 14 - k * 4
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
    prism(c, hall, 30, roof=TILE, wall=(222, 210, 186))
    dome(c, cen.x + 30, cen.y + 10, 13, 18, drum=6)
    gate = affinity.translate(box(-14, -8, 14, 8), up[0] + 6, up[1] + 6)
    prism(c, gate, 24, roof=LEAD, wall=MARBLE, ridge=False, outline=MARBLE_D)
    dome(c, gate.centroid.x, gate.centroid.y, 8, 24)
    # sea wall along the lower terrace
    low = LineString([q[2], q[3]]).buffer(3, cap_style=2)
    prism(c, low, 12, roof=(196, 180, 150), wall=(170, 150, 118), ridge=False)
    return pg

def basilica(c, coords, Y, name, atrium=True, length_k=1.0, roof_h=26, wonder=False):
    pg = c.poly_local(coords)
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
        basilica(c, ST['church_peace']['geom']['coords'], Y, 'peace', atrium=True, roof_h=24)
        if Y >= 30: basilica(c, ST['church_megale']['geom']['coords'], Y, 'megale', atrium=True, roof_h=34, wonder=True)
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
        for g in sorted(arms, key=lambda g: -g.bounds[2] + g.bounds[0]):
            prism(c, g, 28, roof=(194, 98, 66), wall=(222, 206, 176), sh=False)
        dome(c, cen.x, cen.y, thick * 1.1, 28, drum=10)
        # the Founder's mausoleum: a rotunda against the east arm
        prism(c, Point(mx, my).buffer(18, 24), 22, roof=LEAD, wall=(220, 210, 190), ridge=False, sh=False)
        dome(c, mx, my, 17, 22)
        people(c, pg.buffer(15).difference(pg.buffer(2)), 40, 9)
    img = c.im.resize((c.w, c.h), Image.LANCZOS).convert('RGB')
    d = ImageDraw.Draw(img); d.rectangle([8, 8, 128, 34], fill=(30, 24, 18)); d.text((16, 14), f'AF {Y}', fill=(240, 224, 190))
    img.save(out, quality=88); return out

if __name__ == '__main__':
    what = sys.argv[1]; ys = [int(v) for v in sys.argv[2:]]
    for Y in ys:
        f = (render_core if what == 'core' else render_apostles)(Y, f'/tmp/epic_{what}_af{Y}.jpg'); print(f)
