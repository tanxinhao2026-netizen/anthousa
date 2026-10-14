#!/usr/bin/env python3
"""Render Xerolophos keyframe base images from the street ledger + hill kit sprites,
so the far view and the deep-zoom composed layer are the same drawing."""
import json, math, sys
sys.path.insert(0, '/workspace/projects/618d22bb-ba67-4a65-bd41-39bbe9c6f6cd/gen')
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

X = '/workspace/projects/618d22bb-ba67-4a65-bd41-39bbe9c6f6cd/living/xerolophos/'
W, H = 2420, 2048; W0 = 1820
D = json.load(open(X + 'houses.json')); HS = D['houses']; late = D['late']
OLD = json.load(open(X + 'houses_v12.json'))['houses']
_E = json.load(open(X + 'houses_east.json')); late = dict(late, **{k: v for k, v in _E['late'].items() if k not in late})
S = json.load(open(X + 'streets.json'))
K = X + 'kits/hill/'
sheet = Image.open(K + 'houses.webp').convert('RGBA'); HM = json.load(open(K + 'houses.json'))
shops = Image.open(K + 'shops.webp').convert('RGBA'); SM = json.load(open(K + 'shops.json'))
props = Image.open(K + 'props.webp').convert('RGBA'); PM = {m['k']: m for m in json.load(open(K + 'props.json'))}
JU = json.load(open(X + 'junctions.json'))
orig = {k: Image.open(X + f'xero_af{k}_v12.jpg').convert('RGB') for k in (40, 50, 60)}

def hsh(n, k=0):
    x = (n * 2654435761 + k * 40503) & 0xffffffff; x ^= x >> 15; x = (x * 2246822519) & 0xffffffff; x ^= x >> 13
    return x / 2 ** 32
def wall_x(y): return 587 - 0.2357 * y

# ---- terrain: AF40 painting with the old scattered houses wiped to bare ground ----
t = orig[40].copy()
m = Image.new('L', (W0, H), 0); md = ImageDraw.Draw(m)
for h in OLD:
    p = h[4]; cx = sum(p[0::2]) / 4; cy = sum(p[1::2]) / 4
    if cx < wall_x(cy) + 20: continue
    if h[2] <= 40 < h[3]:
        q = [(cx + (p[i] - cx) * 1.9, cy + (p[i + 1] - cy) * 1.9) for i in range(0, 8, 2)]
        md.polygon(q, fill=255)
m = m.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(4))
# ground fill: hill dust tinted toward the painting's dry-hill colour
a40 = np.asarray(orig[40]).astype(float)
hill = a40[700:1100, 800:1000].reshape(-1, 3).mean(0)
gt = Image.open(K + 'ground.webp').convert('RGB').resize((48, 48), Image.LANCZOS)
g = Image.new('RGB', (W, H))
for x in range(0, W, 48):
    for y in range(0, H, 48): g.paste(gt, (x, y))
ga = np.asarray(g).astype(float); ga = ga - ga.reshape(-1, 3).mean(0) + hill
noise = np.asarray(Image.effect_noise((W // 64, H // 64), 40).resize((W, H), Image.BICUBIC)).astype(float)[..., None]
ga = ga * 0.55 + hill * 0.45 + (noise - 128) * 0.12
g = Image.fromarray(np.clip(ga, 0, 255).astype(np.uint8))
terrain = Image.composite(g.crop((0, 0, W0, H)), t, m)
def _pad(im):
    o = g.copy(); seam = Image.linear_gradient('L').rotate(90).resize((80, H))
    o.paste(im, (0, 0)); o.paste(g.crop((W0 - 80, 0, W0, H)), (W0 - 80, 0), seam)
    return o
terrain = _pad(terrain)
orig = {k: _pad(v) for k, v in orig.items()}

# burnt ground for the fire years: the bare terrain charred, no old painted houses
_bn = np.asarray(Image.effect_noise((W // 16, H // 16), 60).resize((W, H), Image.BICUBIC)).astype(float)[..., None]
_ta = np.asarray(terrain).astype(float)
burnt = Image.fromarray(np.clip(_ta * 0.42 + np.array([38, 32, 28]) * 0.5 + (_bn - 128) * 0.25, 0, 255).astype(np.uint8))
def patch(img, src, poly, grow=10, feather=6):
    mm = Image.new('L', (W, H), 0); ImageDraw.Draw(mm).polygon([tuple(p) for p in poly], fill=255)
    mm = mm.filter(ImageFilter.MaxFilter(grow * 2 + 1)).filter(ImageFilter.GaussianBlur(feather))
    return Image.composite(src, img, mm)

STY = {'m': ((118, 104, 86, 190), (174, 163, 144, 255)), 's': ((140, 118, 88, 110), (200, 182, 146, 215)),
       'c': ((140, 118, 88, 90), (203, 186, 150, 190)), 'l': (None, (205, 189, 154, 165))}
def streets_layer(Y):
    L = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    for pas in (0, 1):
        for q in S:
            x1, y1, x2, y2, w, k, y = q[:7]
            if y > Y or (len(q) > 7 and q[7] and q[7] <= Y): continue
            col = STY[k][pas]
            if col is None: continue
            ww = w + 2 if pas == 0 else w
            d.line([(x1, y1), (x2, y2)], fill=col, width=int(ww))
            r = ww / 2; d.ellipse([x2 - r, y2 - r, x2 + r, y2 + r], fill=col); d.ellipse([x1 - r, y1 - r, x1 + r, y1 + r], fill=col)
    return L.filter(ImageFilter.GaussianBlur(0.8))

SHACKS = [(495, 1240), (1140, 1240)]
cache = {}
def sprite(k, w, h):
    key = (k, w, h)
    if key not in cache:
        if k[0] == 'p': mm = PM[k[1]]; src = props
        else: mm = (SM if k[0] else HM)[k[1]]; src = shops if k[0] else sheet
        cache[key] = src.crop((mm['x'], 0, mm['x'] + mm['w'], mm['h'])).resize((w, h), Image.LANCZOS)
    return cache[key]

SS = 2  # supersample
# ---- houses are drawn from their own footprint: walls rise from the lot, the roof sits on top (hip roof along the long side).
# What you see is exactly the body the street audit checks, so a house can never be drawn over a road.
STYLE = {  # block function -> house look (keep in sync with index.html HSTYLE)
    'market': dict(wall=[(236, 222, 192), (228, 206, 166)], roof=[(198, 104, 58), (206, 118, 64), (188, 96, 56)], awn=1.0, flat=0.05),
    'shops': dict(wall=[(234, 220, 190), (224, 204, 168)], roof=[(192, 100, 60), (180, 92, 56)], awn=0.5, flat=0.06),
    'fine': dict(wall=[(244, 238, 226), (238, 230, 214)], roof=[(200, 112, 66), (190, 104, 62)], court=1, flat=0.0),
    'workshop': dict(wall=[(196, 162, 116), (184, 150, 106), (204, 172, 128)], roof=[(142, 86, 58), (128, 90, 66), (150, 100, 70)], flat=0.45, kiln=0.35),
    'water': dict(wall=[(216, 222, 220), (226, 228, 222)], roof=[(176, 98, 66), (166, 92, 64)], flat=0.12),
    'garrison': dict(wall=[(198, 196, 188), (186, 184, 178)], roof=[(150, 92, 72), (140, 96, 80)], flat=0.15),
    'planned': dict(wall=[(228, 214, 188)], roof=[(184, 94, 58)], flat=0.0),
    'garden': dict(wall=[(206, 182, 140), (196, 172, 132)], roof=[(166, 100, 66)], flat=0.5),
}
WALL = [(228, 212, 182), (216, 194, 156), (238, 228, 206), (204, 176, 136), (224, 204, 172), (210, 200, 184)]
ROOF = [(186, 94, 60), (172, 86, 54), (198, 112, 70), (160, 80, 52), (180, 102, 66), (150, 96, 72)]
LX, LY = -0.6, -0.8   # light from the north-west
def shade(c, k): return tuple(max(0, min(255, int(v * k))) for v in c)
import house_types as HT_
def house_parts(h, Y=None):
    by, P, sh = HT_.geom(h)
    if Y is not None: P = HT_.at(P, Y)
    M = {'fill': None, 'edge': 'edge', 'line': 'ridge'}
    out = [('shadow', sh)]
    for kind, lay, poly, col, *_ in P:
        out.append((M[kind] or ('wall' if lay == 'w' else 'roof'), poly, col))
    return by, out
def draw_parts(d, sd_, parts, a_mul=1.0):
    S_ = lambda poly: [(x * SS, y * SS) for x, y in poly]
    for kind, poly, *c in parts:
        if kind == 'shadow':
            from_ = poly; hl = S_(from_[:4]) + S_(from_[4:])
            sd_.polygon(S_(hullp(poly)), fill=(50, 32, 14, 70))
        elif kind == 'edge': d.line(S_(poly + poly[:1]), fill=c[0] + (int(255 * a_mul),), width=1)
        elif kind == 'ridge': d.line(S_(poly), fill=c[0] + (int(255 * a_mul),), width=2)
        else: d.polygon(S_(poly), fill=c[0] + (int(255 * a_mul),))
def hullp(pts):
    pts = sorted(set(pts))
    def cr(o, a, b): return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p_ in pts:
        while len(lo) >= 2 and cr(lo[-2], lo[-1], p_) <= 0: lo.pop()
        lo.append(p_)
    for p_ in reversed(pts):
        while len(up) >= 2 and cr(up[-2], up[-1], p_) <= 0: up.pop()
        up.append(p_)
    return lo[:-1] + up[:-1]

# ---- epic public work: the Mese as an imperial colonnaded avenue (world.json r_mese: 25 m between porticoes, AF1)
from shapely.geometry import LineString as _LS, Polygon as _PG, box as _box, Point as Point_
from shapely.ops import unary_union as _uu
_CITY = json.load(open(X + 'city.json'))
_MESE = _LS(next(r['pts'] for r in _CITY['roads'] if r['id'] == 'r_mese'))
_INQ = _PG([(wall_x(-50) + 8, -50), (W + 50, -50), (W + 50, H + 50), (wall_x(H + 50) + 8, H + 50)])
def _polys(g):
    if g.is_empty: return []
    return [g] if g.geom_type == 'Polygon' else [q for q in getattr(g, 'geoms', []) if q.geom_type == 'Polygon']
def mese_portico(big0, Y):
    big = Image.new('RGBA', big0.size, (0, 0, 0, 0)); _r = _mese_portico(big, Y); big0.alpha_composite(big); return _r
def _mese_portico(big, Y):
    cut = _uu([_LS([(q[0], q[1]), (q[2], q[3])]).buffer(q[4] / 2 + 1.2, cap_style=2) for q in S
               if q[4] != 30 and q[6] <= Y and not (len(q) > 7 and q[7] and q[7] <= Y) and _MESE.distance(_LS([(q[0], q[1]), (q[2], q[3])])) < 17])
    band = _MESE.buffer(15, cap_style=2).difference(_MESE.buffer(9, cap_style=2)).difference(cut).intersection(_INQ)
    if Y >= 57: band = band.difference(FORUM.buffer(1))
    inner = _MESE.buffer(9.4, cap_style=2).exterior
    ridge = _MESE.buffer(12.2, cap_style=2).exterior
    d = ImageDraw.Draw(big, 'RGBA'); T = lambda P: [(x * SS, y * SS) for x, y in P]
    paving = _MESE.buffer(9, cap_style=2).intersection(_INQ)
    for pg in _polys(paving): d.polygon(T(pg.exterior.coords), fill=(214, 204, 184, 255))
    # slab joints across the carriageway
    L = _MESE.length
    for i in range(int(L // 5)):
        a = _MESE.interpolate(i * 5); b = _MESE.interpolate(i * 5 + 0.5)
        dx, dy = b.x - a.x, b.y - a.y; n_ = math.hypot(dx, dy) or 1; nx, ny = -dy / n_, dx / n_
        if not _INQ.contains(a): continue
        d.line(T([(a.x - nx * 8.6, a.y - ny * 8.6), (a.x + nx * 8.6, a.y + ny * 8.6)]), fill=(176, 164, 142, 120), width=1)
    d.line(T(_MESE.coords), fill=(160, 146, 122, 150), width=1)  # crown of the road
    for pg in _polys(band):
        sh_ = [(x + 1.4, y + 1.6) for x, y in pg.exterior.coords]
        d.polygon(T(sh_), fill=(60, 40, 20, 90))
    for pg in _polys(band):
        d.polygon(T(pg.exterior.coords), fill=(186, 108, 72, 255))
        d.line(T(pg.exterior.coords), fill=(120, 66, 44, 255), width=1)
    for ln in (ridge,):
        g_ = ln.intersection(band)
        for seg in ([g_] if g_.geom_type == 'LineString' else getattr(g_, 'geoms', [])):
            if seg.geom_type == 'LineString': d.line(T(seg.coords), fill=(138, 74, 48, 255), width=2)
    # columns on the street edge: marble drums every ~3.6 px (about 3 m)
    for ring in (inner,):
        n = int(ring.length // 3.6)
        for i in range(n):
            pt = ring.interpolate(i * 3.6)
            if not band.buffer(0.8).contains(pt): continue
            x, y = pt.x * SS, pt.y * SS
            d.ellipse([x - 1.6 + 2.2, y - 1.2 + 2.6, x + 1.6 + 2.2, y + 1.2 + 2.6], fill=(70, 50, 30, 90))
            d.ellipse([x - 1.5, y - 1.5, x + 1.5, y + 1.5], fill=(240, 234, 220, 255))

# ---- epic buildings (world.json fixed footprints): Forum of Theodosius (AF57, Forum Tauri), Nymphaeum Maius (AF44)
FORUM = _PG(late['forum_theodosius']['p']); NYMPH = _PG(late['nymphaeum_maius']['p'])
MARBLE = (236, 230, 216); TILE = (186, 108, 72); TILE_D = (138, 74, 48)
def _ring_band(poly, d0, d1): return poly.buffer(-d0, join_style=2).difference(poly.buffer(-d1, join_style=2))
def epic_ground(big0, Y):
    big = Image.new('RGBA', big0.size, (0, 0, 0, 0)); _r = _epic_ground(big, Y); big0.alpha_composite(big); return _r
def _epic_ground(big, Y):
    d = ImageDraw.Draw(big, 'RGBA'); T = lambda P, z=0: [(x * SS, (y - z) * SS) for x, y in P]
    if Y >= 57:
        x0, y0, x1, y1 = FORUM.bounds
        if Y < 59:   # site cleared, rubble and stone heaps
            d.polygon(T(FORUM.exterior.coords), fill=(170, 150, 118, 255))
            for i in range(26):
                hx, hy = x0 + 8 + hsh(i, 1) * (x1 - x0 - 16), y0 + 8 + hsh(i, 2) * (y1 - y0 - 16)
                d.ellipse(T([(hx - 3, hy - 2), (hx + 3, hy + 2)]), fill=(206, 198, 180, 255))
        else:
            d.polygon(T(FORUM.exterior.coords), fill=(214, 204, 184, 255))
            inn = FORUM.buffer(-10, join_style=2); ix0, iy0, ix1, iy1 = inn.bounds
            k = 0
            for gx in range(int(ix0), int(ix1), 6):
                for gy in range(int(iy0), int(iy1), 4):
                    k += 1; v = int(hsh(k, 7) * 18) - 9; off = 3 if (gy // 4) % 2 else 0
                    d.rectangle([(gx + off) * SS, gy * SS, (gx + off + 5.6) * SS, (gy + 3.6) * SS], fill=(228 + v, 220 + v, 202 + v, 255))
            my_ = _MESE.interpolate(_MESE.project(Point_((x0 + x1) / 2, 1190))).y
            d.rectangle([ix0 * SS, (my_ - 7) * SS, ix1 * SS, (my_ + 7) * SS], fill=(200, 190, 170, 120))   # the Mese worn across the square
            d.line([ix0 * SS, (my_ - 7) * SS, ix1 * SS, (my_ - 7) * SS], fill=(176, 164, 142, 255), width=2)
            d.line([ix0 * SS, (my_ + 7) * SS, ix1 * SS, (my_ + 7) * SS], fill=(176, 164, 142, 255), width=2)
            d.polygon(T(inn.exterior.coords), outline=(170, 156, 132, 255))
            # statues on bases along the axis, the bronze bull of the Forum Tauri south of the road
            for i, (fx, fy) in enumerate(((0.2, 0.3), (0.8, 0.3), (0.2, 0.84), (0.8, 0.84), (0.36, 0.3), (0.64, 0.3))):
                sx_, sy_ = x0 + fx * (x1 - x0), y0 + fy * (y1 - y0)
                d.ellipse([(sx_ + 0.5) * SS, (sy_ - 0.5) * SS, (sx_ + 5) * SS, (sy_ + 2) * SS], fill=(60, 40, 20, 70))
                d.rectangle([(sx_ - 2) * SS, (sy_ - 1.5) * SS, (sx_ + 2) * SS, (sy_ + 1.5) * SS], fill=(190, 180, 160, 255))
                d.rectangle([(sx_ - 2) * SS, (sy_ - 3) * SS, (sx_ + 2) * SS, (sy_ - 1.5) * SS], fill=(214, 206, 188, 255))
                d.ellipse([(sx_ - 1) * SS, (sy_ - 8) * SS, (sx_ + 1) * SS, (sy_ - 3) * SS], fill=(120, 104, 70, 255))
            bx_, by_ = x0 + 0.5 * (x1 - x0), y0 + 0.78 * (y1 - y0)
            d.rectangle([(bx_ - 6) * SS, (by_ - 2.5) * SS, (bx_ + 6) * SS, (by_ + 2.5) * SS], fill=(196, 186, 166, 255))
            d.rectangle([(bx_ - 6) * SS, (by_ - 4) * SS, (bx_ + 6) * SS, (by_ - 2.5) * SS], fill=(218, 210, 192, 255))
            d.ellipse([(bx_ - 4.5) * SS, (by_ - 8) * SS, (bx_ + 3.5) * SS, (by_ - 4) * SS], fill=(92, 74, 46, 255))
            d.ellipse([(bx_ + 2.5) * SS, (by_ - 9) * SS, (bx_ + 5.5) * SS, (by_ - 6) * SS], fill=(92, 74, 46, 255))
            for lx in (-3.5, -1.5, 1.2, 3):
                d.line([(bx_ + lx) * SS, (by_ - 5) * SS, (bx_ + lx) * SS, (by_ - 3.6) * SS], fill=(92, 74, 46, 255), width=3)
            # market awnings in the colonnade's lee and people crossing
            for i in range(10):
                side = i % 2; t = 0.12 + 0.76 * hsh(i, 21)
                ax_ = ix0 + t * (ix1 - ix0); ay_ = (iy0 + 2) if side == 0 else (iy1 - 6)
                if abs(ay_ - my_) < 10: continue
                col = [(196, 74, 52), (214, 184, 120), (110, 132, 160), (226, 222, 210)][i % 4]
                d.rectangle([ax_ * SS, ay_ * SS, (ax_ + 7) * SS, (ay_ + 4) * SS], fill=col + (255,))
                d.line([ax_ * SS, (ay_ + 4) * SS, (ax_ + 7) * SS, (ay_ + 4) * SS], fill=(90, 60, 40, 200), width=2)
            for i in range(70):
                px_, py_ = ix0 + hsh(i, 31) * (ix1 - ix0), iy0 + hsh(i, 32) * (iy1 - iy0)
                if abs(py_ - my_) < 9 and hsh(i, 33) < 0.5: px_ = ix0 + hsh(i, 34) * (ix1 - ix0)
                col = [(150, 60, 50), (60, 80, 120), (220, 214, 196), (110, 90, 60), (170, 130, 60)][i % 5]
                d.ellipse([(px_ + 0.3) * SS, (py_ + 0.1) * SS, (px_ + 2.3) * SS, (py_ + 1.1) * SS], fill=(60, 40, 20, 60))
                d.ellipse([(px_ - 0.7) * SS, (py_ - 1.3) * SS, (px_ + 0.7) * SS, (py_ + 0.3) * SS], fill=col + (255,))
            # peristyle on four sides, open where the Mese passes through
            band = _ring_band(FORUM, 0, 9).difference(_MESE.buffer(9, cap_style=2))
            for pg in _polys(band): d.polygon(T([(x + 1.4, y + 1.6) for x, y in pg.exterior.coords]), fill=(60, 40, 20, 90))
            for pg in _polys(band):
                d.polygon(T(pg.exterior.coords), fill=TILE + (255,)); d.line(T(pg.exterior.coords), fill=TILE_D + (255,), width=1)
            inband = _ring_band(FORUM, 9, 11.5).difference(_MESE.buffer(9, cap_style=2))
            for pg in _polys(inband): d.polygon(T(pg.exterior.coords), fill=(70, 50, 30, 70))
            hi = _ring_band(FORUM, 1.5, 4.5).difference(_MESE.buffer(9, cap_style=2))
            for pg in _polys(hi): d.polygon(T(pg.exterior.coords), fill=(214, 136, 96, 120))
            rid = FORUM.buffer(-4.5, join_style=2).exterior.intersection(band)
            for seg in ([rid] if rid.geom_type == 'LineString' else getattr(rid, 'geoms', [])):
                if seg.geom_type == 'LineString': d.line(T(seg.coords), fill=TILE_D + (255,), width=2)
            inner = FORUM.buffer(-9.4, join_style=2).exterior
            for i in range(int(inner.length // 3.6)):
                pt = inner.interpolate(i * 3.6)
                if band.buffer(0.8).contains(pt): d.ellipse([pt.x * SS - 1.5, pt.y * SS - 1.5, pt.x * SS + 1.5, pt.y * SS + 1.5], fill=MARBLE + (255,))
    if Y >= 44:   # Nymphaeum Maius: basin in front, exedra behind
        c = NYMPH.centroid; x0, y0, x1, y1 = NYMPH.bounds
        d.polygon(T(NYMPH.buffer(5, join_style=2).exterior.coords), fill=(210, 200, 180, 255))
        d.polygon(T(NYMPH.exterior.coords), fill=(226, 218, 200, 255))
        basin = _box(x0 + 5, c.y - 1, x1 - 7, y1 - 6).intersection(NYMPH.buffer(-4, join_style=2))
        d.polygon(T(basin.exterior.coords), fill=MARBLE + (255,))
        d.polygon(T(basin.buffer(-2.2, join_style=2).exterior.coords), fill=(88, 150, 176, 255))
        for i in range(5):
            wx = x0 + 10 + i * (x1 - x0 - 20) / 4
            d.line(T([(wx, c.y + 4), (wx + 0.5, c.y + 9)]), fill=(214, 236, 244, 200), width=2)
def epic_tall(big0, Y):
    big = Image.new('RGBA', big0.size, (0, 0, 0, 0)); _r = _epic_tall(big, Y); big0.alpha_composite(big); return _r
def _epic_tall(big, Y):
    d = ImageDraw.Draw(big, 'RGBA'); T = lambda P, z=0: [(x * SS, (y - z) * SS) for x, y in P]
    if Y >= 44:   # exedra: half ring of two-storey columns, half dome
        c = NYMPH.centroid; x0, y0, x1, y1 = NYMPH.bounds; r = (x1 - x0) / 2 - 3; cx, cy = c.x, c.y
        arc = [(cx + r * math.cos(a), cy + 0.55 * r * math.sin(a)) for a in [math.pi + i * math.pi / 24 for i in range(25)]]
        h = 16
        back = [(cx + r * math.cos(a), cy + 0.55 * r * math.sin(a)) for a in [math.pi + i * math.pi / 24 for i in range(25)]]
        d.polygon(T([(cx + r, cy), (cx + r + 5, cy + 3), (cx + r + 5, cy - 0.55 * r + 3)]), fill=(60, 40, 20, 70))
        d.polygon(T(back, 0) + T(back[::-1], h), fill=(222, 210, 188, 255))   # inner face of the curved back wall
        for i in range(1, 24, 3):   # niches with statues
            x, y = back[i]; d.rectangle([(x - 1.2) * SS, (y - 13) * SS, (x + 1.2) * SS, (y - 9) * SS], fill=(150, 136, 112, 255))
            d.rectangle([(x - 1.2) * SS, (y - 6) * SS, (x + 1.2) * SS, (y - 2) * SS], fill=(150, 136, 112, 255))
        for i in range(0, 25, 2):
            x, y = arc[i]
            for z0, z1 in ((0, 7.5), (8.5, 15.5)): d.line(T([(x, y)], z0) + T([(x, y)], z1), fill=MARBLE + (255,), width=3)
        d.line(T(arc, 8), fill=(170, 154, 130, 255), width=2)
        dome = [(cx + r * 0.92 * math.cos(a), cy - 2 + 0.5 * r * math.sin(a)) for a in [math.pi + i * math.pi / 24 for i in range(25)]]
        d.polygon(T(dome, h) + T([(cx, cy - 2)], h + 7), fill=(150, 150, 146, 255))
        d.line(T(arc, h), fill=(120, 110, 96, 255), width=2)
    if Y >= 57:   # Column of Theodosius rises a drum-course a year, statue on top when finished (AF64 = AD 394)
        x0, y0, x1, y1 = FORUM.bounds; cx, cy = (x0 + x1) / 2, y0 + 26
        d.polygon(T([(cx + 3, cy + 3), (cx + 30, cy + 14), (cx + 32, cy + 10), (cx + 5, cy - 1)]), fill=(60, 40, 20, 70))
        d.polygon(T([(cx - 5, cy - 5), (cx + 5, cy - 5), (cx + 5, cy + 5), (cx - 5, cy + 5)]), fill=(196, 188, 170, 255))
        d.polygon(T([(cx - 5, cy + 5), (cx + 5, cy + 5)], 0) + T([(cx + 5, cy + 5), (cx - 5, cy + 5)], 9), fill=(206, 198, 182, 255))
        d.polygon(T([(cx - 5, cy - 5), (cx + 5, cy - 5), (cx + 5, cy + 5), (cx - 5, cy + 5)], 9), fill=MARBLE + (255,))
        hmax = 9 + 52 * min(1, (Y - 57 + 1) / 8)
        d.rectangle([(cx - 3.2) * SS, (cy - hmax) * SS, (cx + 3.2) * SS, (cy - 9) * SS], fill=(236, 230, 216, 255))
        d.rectangle([(cx + 1.0) * SS, (cy - hmax) * SS, (cx + 3.2) * SS, (cy - 9) * SS], fill=(196, 188, 170, 255))
        z = 9
        while z < hmax - 1: d.line([(cx - 3.2) * SS, (cy - z) * SS, (cx + 3.2) * SS, (cy - z - 2.4) * SS], fill=(160, 146, 120, 255), width=2); z += 3.0
        if Y < 64:   # scaffold and crane
            for sx in (-4, 4): d.line([(cx + sx) * SS, (cy - 9) * SS, (cx + sx) * SS, (cy - hmax - 3) * SS], fill=(124, 92, 58, 255), width=1)
            for zz in range(11, int(hmax) + 2, 4): d.line([(cx - 4) * SS, (cy - zz) * SS, (cx + 4) * SS, (cy - zz) * SS], fill=(124, 92, 58, 255), width=1)
        else:
            d.rectangle([(cx - 3.4) * SS, (cy - hmax - 1.6) * SS, (cx + 3.4) * SS, (cy - hmax) * SS], fill=MARBLE + (255,))
            d.polygon([((cx - 1.3) * SS, (cy - hmax - 1.6) * SS), ((cx + 1.3) * SS, (cy - hmax - 1.6) * SS), ((cx + 0.8) * SS, (cy - hmax - 8) * SS), ((cx - 0.8) * SS, (cy - hmax - 8) * SS)], fill=(176, 144, 70, 255))
            d.ellipse([(cx - 1) * SS, (cy - hmax - 10) * SS, (cx + 1) * SS, (cy - hmax - 8) * SS], fill=(176, 144, 70, 255))
    if Y >= 60:   # Arch of Theodosius over the Mese at the forum's west entrance
        x0 = FORUM.bounds[0]; my = _MESE.interpolate(_MESE.project(Point_(x0, 1190))).y
        ax0, ax1, ay0, ay1, h = x0 - 5, x0 + 5, my - 17, my + 17, 18
        d.polygon(T([(ax0 + 2, ay0 + 2), (ax1 + 6, ay0 + 2), (ax1 + 6, ay1 + 3), (ax0 + 2, ay1 + 3)]), fill=(60, 40, 20, 80))
        for k in range(3):   # three piers seen end-on with vaults between
            pass
        d.polygon(T([(ax0, ay1), (ax1, ay1)]) + T([(ax1, ay1), (ax0, ay1)], h), fill=(214, 206, 188, 255))
        d.polygon(T([(ax0, ay0), (ax1, ay0), (ax1, ay1), (ax0, ay1)], h), fill=MARBLE + (255,))
        for f in (0.25, 0.5, 0.75):
            yy = ay0 + (ay1 - ay0) * f
            d.line(T([(ax0, yy), (ax1, yy)], h), fill=(196, 186, 166, 255), width=1)
        for k, (yy0, yy1) in enumerate(((ay0 + 2, ay0 + 9), (ay0 + 12, ay1 - 12), (ay1 - 9, ay1 - 2))):
            pass
def render(Y, crop=None):
    base = terrain.copy()
    if Y >= 42:
        for sx, sy in SHACKS: base = patch(base, g, [(sx-95,sy-75),(sx+95,sy-75),(sx+95,sy+75),(sx-95,sy+75)], 4, 12)
    if Y >= 41: base = patch(base, orig[50], late['cistern_modestus']['p'], 14)
    if 48 <= Y < 54: base = patch(base, burnt, late['fire_ruins']['p'], 6, 14)
    if Y >= 52: base = patch(base, orig[60], late['arian_meeting']['p'], 16)
    if Y >= 54: base = patch(base, orig[60], late['cistern_carriers']['p'], 10)
    base = base.convert('RGBA'); base.alpha_composite(streets_layer(Y))
    big = base.resize((W * SS, H * SS), Image.BICUBIC)
    mese_portico(big, Y); epic_ground(big, Y)
    sh = Image.new('RGBA', big.size, (0, 0, 0, 0)); sdr = ImageDraw.Draw(sh)
    lay = Image.new('RGBA', big.size, (0, 0, 0, 0)); dl = ImageDraw.Draw(lay)
    items = []
    for hh_ in HS:
        if not (hh_[2] <= Y < hh_[3]): continue
        by, parts = house_parts(hh_, Y)
        items.append((by, 'h', parts, hh_[2] == Y))
    for jx, jy, jyr, kind in JU:
        if jyr > Y: continue
        ks = {'well': [(16, 0, 0, 8), (15, 6, 3, 6)], 'stall': [((12 if (jx + jy) % 2 else 17), 0, 0, 8)], 'oven': [(0, 0, 0, 8)]}[kind]
        for pk, dx, dy, sz in ks:
            mm = PM[pk]; sc = sz / max(mm['w'], mm['h'])
            items.append((jy + dy + 2, 'p', (jx + dx, mm['w'] * sc, mm['h'] * sc, ('p', pk)), False))
    items.sort(key=lambda t: t[0])
    for by, kind, data, new in items:
        if kind == 'h':
            draw_parts(dl, sdr, [q for q in data if q[0] == 'shadow'])
    big.alpha_composite(sh.filter(ImageFilter.GaussianBlur(1.2)))
    for by, kind, data, new in items:
        if kind == 'h': draw_parts(dl, sdr, [q for q in data if q[0] != 'shadow'], 0.6 if new else 1.0)
        else:
            cx, w, hh, k = data
            sp = sprite(k, max(2, int(w * SS)), max(2, int(hh * SS)))
            lay.alpha_composite(sp, (int((cx - w / 2) * SS), int((by - hh) * SS)))
    big.alpha_composite(lay); epic_tall(big, Y)
    out = big.resize((W, H), Image.LANCZOS).convert('RGB')
    if crop: return out
    out.save(X + f'xero_af{Y}.jpg', quality=86)
    return len(items)

if __name__ == '__main__' and len(sys.argv) > 1 and sys.argv[1] == 'epic':   # python3 render_xero.py epic 43 56 60 64
    for y_ in sys.argv[2:]:
        o = render(int(y_), crop=True); o.save('/tmp/epic_full_%s.jpg' % y_, quality=88)
        o.crop((1900, 960, 2340, 1320)).resize((1320, 1080), Image.LANCZOS).save('/tmp/epic_%s.jpg' % y_, quality=90)
    sys.exit()
if __name__ == '__main__' and len(sys.argv) > 1 and sys.argv[1] == 'test':
    o = render(50, crop=True); o.crop((380, 950, 780, 1300)).resize((1200, 1050), Image.LANCZOS).save('/tmp/h_close.jpg', quality=90)
    o.crop((450, 150, 1250, 750)).save('/tmp/h_far.jpg', quality=88); sys.exit()
# ---- ground + timed overlays: the page draws streets and houses itself for every single year
def overlay(name, src, poly, grow, feather, y0, y1):
    mm = Image.new('L', (W, H), 0); ImageDraw.Draw(mm).polygon([tuple(p) for p in poly], fill=255)
    mm = mm.filter(ImageFilter.MaxFilter(grow * 2 + 1)).filter(ImageFilter.GaussianBlur(feather))
    bb = mm.getbbox(); rg = src.convert('RGBA'); rg.putalpha(mm)
    rg.crop(bb).save(X + name, quality=82)
    return dict(f=name, x=bb[0], y=bb[1], a=y0, b=y1)
def ground_files():
    terrain.save(X + 'xero_ground.jpg', quality=86)
    OV = [overlay('ov_cistern_modestus.webp', orig[50], late['cistern_modestus']['p'], 14, 6, 41, 999)]
    for i, (sx, sy) in enumerate(SHACKS):
        OV.append(overlay('ov_shack%d.webp' % i, g, [(sx-95,sy-75),(sx+95,sy-75),(sx+95,sy+75),(sx-95,sy+75)], 4, 12, 42, 999))
    OV.append(overlay('ov_fire.webp', burnt, late['fire_ruins']['p'], 6, 14, 48, 54))
    OV.append(overlay('ov_arian.webp', orig[60], late['arian_meeting']['p'], 16, 6, 52, 999))
    OV.append(overlay('ov_cistern_carriers.webp', orig[60], late['cistern_carriers']['p'], 10, 6, 54, 999))
    json.dump(OV, open(X + 'ground.json', 'w'))
ground_files()
HT_.export(HS, X + 'houses_geom.json'); print('houses_geom.json written')
for Y in (40, 50, 60):
    print(Y, render(Y))
