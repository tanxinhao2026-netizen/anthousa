"""Close-up check of houses/landmarks: python3 ../../gen/zoom_view.py out.png x,y,year [x,y,year ...] (run in living/xerolophos)"""
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import house_types as HT
from PIL import Image, ImageDraw
H = json.load(open('houses.json'))['houses']
def view(cx, cy, Y, r=32, S=10):
    im = Image.new('RGB', (2 * r * S, 2 * r * S), (196, 176, 136)); d = ImageDraw.Draw(im)
    T = lambda P: [((x - cx + r) * S, (y - cy + r) * S) for x, y in P]
    items = []
    for h in H:
        p = h[4]
        if not (h[2] <= Y < h[3]) or abs(p[0] - cx) > r + 10 or abs(p[1] - cy) > r + 10: continue
        by, P, sh = HT.geom(h); items.append((by, HT.at(P, Y)))
    for by, P in sorted(items, key=lambda t: t[0]):
        for kind, lay, poly, col, *_ in P:
            if kind == 'fill': d.polygon(T(poly), fill=tuple(col))
            elif kind == 'edge': d.line(T(poly + poly[:1]), fill=tuple(col), width=2)
            else: d.line(T(poly), fill=tuple(col), width=3)
    return im.resize((320, 320), Image.LANCZOS)
V = [tuple(float(v) for v in a.split(',')) for a in sys.argv[2:]]
out = Image.new('RGB', (320 * min(3, len(V)), 320 * ((len(V) + 2) // 3)))
for i, (x, y, Y) in enumerate(V): out.paste(view(x, y, int(Y)), (320 * (i % 3), 320 * (i // 3)))
out.save(sys.argv[1])
