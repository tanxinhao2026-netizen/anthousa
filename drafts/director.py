"""Draft director: grows one variant of Anthousa decade by decade, fast.

    python drafts/director.py            # policy from drafts/policy.json, to the year it names

A draft is not canon. It re-runs the whole history from genesis under this branch's own rules
(rules/calibration.json may differ per branch), then writes proposals for every later decade from
the variant's policy. Every proposal still goes through rules.py; rejected tries are retried
elsewhere and the rest are recorded. Chronicles are generated from what actually happened.
"""
import glob, json, math, os, random, subprocess, sys, copy
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "engine"))
from shapely.geometry import Polygon, LineString, Point, box
from shapely.ops import unary_union, nearest_points
from shapely import affinity
from terrain import land, to_xy, elevation
from world import load, save, geom, standing, houses_standing, by_id
import rules
import step as STEP

POL = json.load(open("drafts/policy.json", encoding="utf-8"))
V = POL["variant"]
RND = random.Random(f"draft-{V}")
I18N_PATH = "i18n/i18n.json"
I18N = json.load(open(I18N_PATH, encoding="utf-8"))
FZ = {"emperor": "皇帝", "church": "教会", "merchants": "商人", "people": "平民", "army": "军队"}
FE = {"emperor": "the emperor", "church": "the church", "merchants": "the merchants", "people": "the people", "army": "the army"}
TZ = {"church": "教堂", "forum": "广场", "column": "纪念柱", "cistern": "蓄水池", "harbor": "港", "granary": "粮仓", "market": "市场",
      "warehouse": "货栈", "palace": "宫", "baths": "浴场", "monastery": "修道院", "barracks": "兵营", "fort": "塔堡", "road": "路",
      "district": "街区", "wall": "城墙", "gate": "门", "aqueduct": "水道", "aqueduct_bridge": "拱桥", "farmland": "田"}
SAINTS = [("Polyeuctus", "波利尤克图斯"), ("John Studios", "斯图狄奥斯的约翰"), ("Euphemia", "尤菲米娅"), ("Anastasia", "阿纳斯塔西娅"),
          ("Theodore", "狄奥多"), ("Irene", "伊琳娜"), ("Thomas", "多马"), ("Andrew", "安德烈"), ("Pantaleon", "潘塔莱昂"),
          ("Plato", "柏拉图（殉道者）"), ("Acacius", "阿卡基乌斯"), ("Menas", "梅纳斯"), ("Stephen", "司提反"), ("Agathonicus", "阿加托尼库斯"),
          ("Laurence", "劳伦斯"), ("Romanus", "罗曼努斯"), ("Diomedes", "狄奥墨得斯"), ("Euphrosyne", "尤弗罗西妮"), ("Nicholas", "尼古拉"),
          ("Panteleimon", "潘特雷蒙"), ("Karpos", "卡尔波斯"), ("Phocas", "福卡斯"), ("Isaiah", "以赛亚"), ("Michael", "米迦勒")]
PATRONS = [("Arcadius", "阿卡狄乌斯"), ("Theodosius", "狄奥多西"), ("Marcian", "马尔西安"), ("Leo", "利奥"), ("Zeno", "芝诺"),
           ("Anastasius", "阿纳斯塔修斯"), ("Justin", "查士丁"), ("Justinian", "查士丁尼"), ("Tiberius", "提比略"), ("Maurice", "莫里斯"),
           ("Heraclius", "希拉克略"), ("Pulcheria", "普尔喀丽娅"), ("Eudoxia", "欧多克西娅"), ("Ariadne", "阿里阿德涅"), ("Sophia", "索菲娅"),
           ("Aetius", "埃提乌斯"), ("Aspar", "阿斯帕"), ("Modestus", "莫德斯图斯"), ("Philoxenus", "菲罗克塞努斯"), ("Probus", "普罗布斯")]
_used = {}


def pick(pool, key):
    i = _used.get(key, 0); _used[key] = i + 1
    en, zh = pool[i % len(pool)]
    return (en, zh) if i < len(pool) else (f"{en} {['II','III','IV'][min(2, i // len(pool) - 1)]}", f"{zh}{['二','三','四'][min(2, i // len(pool) - 1)]}世")


# ---------------- geometry helpers ----------------
def rect(cx, cy, w, h, ang):
    p = Polygon([(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)])
    p = affinity.translate(affinity.rotate(p, ang), cx, cy)
    return [[round(x, 1), round(y, 1)] for x, y in list(p.exterior.coords)[:4]]


def road_angle(w, year, x, y):
    rs = standing(w, year, {"road"})
    if not rs:
        return 0
    p = Point(x, y)
    r = min(rs, key=lambda r: geom(r).distance(p)); g = geom(r)
    t = g.project(p); a, b = g.interpolate(max(0, t - 2)), g.interpolate(min(g.length, t + 2))
    return math.degrees(math.atan2(b.y - a.y, b.x - a.x))


def ok(w, s, year):
    return rules.check_structure(w, s, year)


def add(w, s, year):  # keep the in-memory world in step with what the proposal file will build
    s2 = dict(s); s2["built"] = year; s2["destroyed"] = None; s2.setdefault("history", [])
    w["structures"].append(s2)


_HT = {}


def houses_hit(w, year, g):
    from shapely.strtree import STRtree
    key = (id(w), year, len(w["houses"]))
    if key not in _HT:
        _HT.clear()
        ps = [Polygon(h["p"]) for h in houses_standing(w, year)]
        _HT[key] = (STRtree(ps), ps)
    t, ps = _HT[key]
    return sum(1 for i in t.query(g) if ps[i].intersects(g))


def place(w, year, base, size, centers, radius, tries=60, align=True, avoid_houses=0.0):
    """Try positions around the centers; return the first structure rules.py accepts (prefer few houses cleared)."""
    best, last = None, None
    for i in range(tries):
        cx, cy = centers[i % len(centers)]
        r = radius * math.sqrt(RND.random()); a = RND.uniform(0, 2 * math.pi)
        x, y = cx + r * math.cos(a), cy + r * math.sin(a)
        ang = road_angle(w, year, x, y) if align else RND.uniform(-20, 20)
        s = copy.deepcopy(base); s["geom"] = {"type": "polygon", "coords": rect(x, y, size[0], size[1], ang)}
        e = ok(w, s, year)
        if e:
            last = e; continue
        if avoid_houses <= 0:
            return s, None
        hh = houses_hit(w, year, geom(s))
        if best is None or hh < best[0]:
            best = (hh, s)
        if hh == 0 or i > tries * avoid_houses:
            break
    return (best[1], None) if best else (None, last)


def shore_harbor(w, year, base, size, region, tries=120):
    L = land(); edge = L.exterior if L.geom_type == "Polygon" else unary_union([p.exterior for p in L.geoms])
    reg = box(*region)
    seg = edge.intersection(reg)
    if seg.is_empty:
        return None, ["no shore in region"]
    last = None
    for i in range(tries):
        p = seg.interpolate(RND.random() * seg.length)
        q = seg.interpolate(min(seg.length, seg.project(p) + 3)); o = seg.interpolate(max(0, seg.project(p) - 3))
        ang = math.degrees(math.atan2(q.y - o.y, q.x - o.x))
        for side in (1, -1):
            nx, ny = -math.sin(math.radians(ang)) * side, math.cos(math.radians(ang)) * side
            cx, cy = p.x + nx * size[1] * 0.25, p.y + ny * size[1] * 0.25
            s = copy.deepcopy(base); s["geom"] = {"type": "polygon", "coords": rect(cx, cy, size[0], size[1], ang)}
            g = geom(s)
            if g.difference(L).area < 0.45 * g.area:
                continue
            e = ok(w, s, year)
            if not e:
                return s, None
            last = e
    return None, last


def net_point(w, year, target):
    rs = standing(w, year, {"road"})
    net = unary_union([geom(r) for r in rs])
    a, _ = nearest_points(net, Point(*target))
    return (round(a.x, 1), round(a.y, 1))


def make_road(w, year, base, target, width=1.4, start=None):
    s0 = start or net_point(w, year, target)
    for jit in range(8):
        tx, ty = target[0] + RND.uniform(-6, 6) * (jit > 0), target[1] + RND.uniform(-6, 6) * (jit > 0)
        s = copy.deepcopy(base); s["geom"] = {"type": "line", "coords": [list(s0), [round(tx, 1), round(ty, 1)]]}; s["width"] = width
        if LineString(s["geom"]["coords"]).length < 3:
            return None, ["too short"]
        e = ok(w, s, year)
        if not e:
            return s, None
    return None, e


def gates_for(w, year, line, faction, idx):
    """Gates wherever a new wall would cross a standing road."""
    out = []
    for r in standing(w, year, {"road"}):
        x = geom(r).intersection(line)
        if x.is_empty:
            continue
        for pt in (list(x.geoms) if hasattr(x, "geoms") else [x]):
            c = pt.centroid
            out.append({"id": f"gate_{V[:3]}_{idx}_{len(out)}", "type": "gate", "name": f"Gate of the {r['name']}",
                        "geom": {"type": "polygon", "coords": rect(c.x, c.y, 3, 3, 0)},
                        "dna": {"motif": "gatehouse", "materials": ["ashlar", "brick"], "ornament": 1, "scale": "civic"}})
    return out


# ---------------- era assembly ----------------
class Era:
    def __init__(self, w, y0):
        self.w, self.y0, self.acts, self.notes, self.rej = w, y0, [], [], []

    def build(self, faction, s, year, why, why_zh, label=None, name_zh=None, label_zh=None):
        s = dict(s); s.setdefault("name", s["id"])
        if label:
            s["label"] = label
        self.acts.append({"op": "build", "faction": faction, "year": year, "structure": s, "why": why})
        add(self.w, s, year)
        I18N["names_zh"][s["id"]] = name_zh or s["name"]
        if label:
            I18N["labels_zh"][s["id"]] = label_zh or name_zh or label
        self.notes.append((faction, s["id"], s["type"], why_zh, why))

    def demolish(self, faction, sid, year, why, memorial=None):
        a = {"op": "demolish", "faction": faction, "id": sid, "year": year, "why": why}
        if memorial:
            a["memorial"] = memorial
        self.acts.append(a)
        s = by_id(self.w, sid); s["destroyed"] = year

    def fail(self, what, reasons):
        self.rej.append({"what": what, "reasons": (reasons or [])[:2]})


def dna(motif, mats, orn=1, scale="civic"):
    return {"motif": motif, "materials": mats, "ornament": orn, "scale": scale}


def palette(year):
    import grammar
    return grammar.era(grammar.style_era(year))["palette"]


def stats(w, y):
    cap = rules.capacities(w, y)
    return rules.population(w, y), cap["food"], cap["water"]


def district_room(w, y):
    """Rough count of free house slots left in the districts."""
    ds = standing(w, y, {"district"})
    area = unary_union([geom(d) for d in ds]).intersection(land().buffer(-2)).area if ds else 0
    blocked = sum(geom(s).area for s in standing(w, y, rules.BUILDING_TYPES | {"farmland"}))
    slots = (area - blocked) / (rules.CAL["house_spacing_units"]["value"] ** 2) * 0.55
    return slots - len(houses_standing(w, y))



# ---------------- shared moves (policies call these) ----------------
CITY_C = (560, 450)


def gid(kind):
    _used[kind + "#"] = _used.get(kind + "#", 0) + 1
    return f"{V[:3]}_{kind}_{_used[kind + '#']}"


def ab_hang(coords, sag):
    g = LineString(coords); e0, e1 = elevation(*coords[0]), elevation(*coords[-1]); n = max(2, int(g.length // 2)); segs, cur = [], None
    for i in range(n + 1):
        f = i / n; p = g.interpolate(f, normalized=True)
        hang = elevation(p.x, p.y) < e0 + (e1 - e0) * f - sag
        if hang and cur is None: cur = max(0, f - 1.0 / n)
        if not hang and cur is not None: segs.append((cur, min(1, f + 1.0 / n))); cur = None
    if cur is not None: segs.append((cur, 1))
    return g, segs


def substring(g, a, b):
    from shapely.ops import substring as ss
    return ss(g, a, b, normalized=True)


def new_aqueduct(E, year, faction, why, why_zh, name=("New Aqueduct", "新水道"), src_box=(40, 120, 260, 330), end_box=(380, 330, 600, 470)):
    w = E.w
    sag = rules.CAL.get("aqueduct_arcade_rule", {}).get("sag_m", 6)
    for t in range(80):
        sx, sy = RND.uniform(src_box[0], src_box[2]), RND.uniform(src_box[1], src_box[3])
        ex, ey = RND.uniform(end_box[0], end_box[2]), RND.uniform(end_box[1], end_box[3])
        if not land().contains(Point(sx, sy)) or elevation(sx, sy) < elevation(ex, ey) + 6:
            continue
        mid = [(sx + (ex - sx) * f + RND.uniform(-25, 25), sy + (ey - sy) * f + RND.uniform(-25, 25)) for f in (0.33, 0.66)]
        coords = [[round(a, 1), round(b, 1)] for a, b in [(sx, sy)] + mid + [(ex, ey)]]
        g, segs = ab_hang(coords, sag)
        if sum(b - a for a, b in segs) * g.length > 120:  # more than ~1.4 km of arcades: too dear, look again
            continue
        bridges, okb = [], True
        for k, (a, b) in enumerate(segs):
            sub = substring(g, a, b).buffer(0.7, cap_style=2)
            if sub.geom_type != "Polygon":
                okb = False; break
            bs = {"id": gid("arcade"), "type": "aqueduct_bridge", "name": f"Arcade of the {name[0]}",
                  "geom": {"type": "polygon", "coords": [[round(x, 1), round(y, 1)] for x, y in list(sub.exterior.coords)[:-1]]}}
            if ok(w, bs, year):
                okb = False; break
            bridges.append(bs)
        if not okb:
            continue
        aq = {"id": gid("aq"), "type": "aqueduct", "name": name[0], "geom": {"type": "line", "coords": coords}}
        tmp = dict(w); tmp["structures"] = list(w["structures"])
        for b in bridges:
            add(tmp, b, year)
        if ok(tmp, aq, year):
            continue
        for b in bridges:
            E.build(faction, b, year, "Arcades carry the channel across the low ground.", "低洼处架起拱桥托住水渠", name_zh=f"{name[1]}拱桥")
        E.build(faction, aq, year, why, why_zh, label=name[0], name_zh=name[1])
        return True
    E.fail(name[0], ["no route found that falls evenly with affordable arcades"])
    return False


def cistern(E, year, faction, centers, radius, size=(10, 8), name=None, why=None, why_zh=None):
    en, zh = name or pick(PATRONS, "cis")
    s = {"id": gid("cis"), "type": "cistern", "name": f"Cistern of {en}", "dna": dna("cistern", [m for m in ("brick",) if m in palette(year)] or palette(year)[:1], 0, "civic")}
    s, e = place(E.w, year, s, size, centers, radius, avoid_houses=0.5)
    if not s:
        E.fail("cistern", e); return False
    E.build(faction, s, year, why or f"An open reservoir named for {en} stores the aqueduct's winter flow.",
            why_zh or f"以{zh}命名的露天蓄水池，存下冬季水道的来水", label=f"Cistern of {en}", name_zh=f"{zh}蓄水池")
    return True


def harbor(E, year, faction, region, size=(20, 13), name=None, why=None, why_zh=None):
    en, zh = name or pick(PATRONS, "har")
    s = {"id": gid("har"), "type": "harbor", "name": f"Harbor of {en}"}
    s, e = shore_harbor(E.w, year, s, size, region)
    if not s:
        E.fail("harbor", e); return None
    E.build(faction, s, year, why or f"A new harbor named for {en} takes the grain ships the old quays turn away.",
            why_zh or f"新港以{zh}命名，接下旧码头容不下的运粮船", label=f"Harbor of {en}", name_zh=f"{zh}港")
    return s


def near(s, d=14):
    c = geom(s).centroid
    return [(c.x, c.y)], d


def building(E, year, faction, t, motif, size, centers, radius, name, why, why_zh, orn=1, scale="civic", label=True, mats=None, avoid=0.5):
    en, zh = name
    s = {"id": gid(t), "type": t, "name": en, "dna": dna(motif, mats or palette(year)[:2], orn, scale)}
    s, e = place(E.w, year, s, size, centers, radius, avoid_houses=avoid)
    if not s:
        E.fail(en, e); return None
    E.build(faction, s, year, why, why_zh, label=en if label else None, name_zh=zh)
    return s


def district(E, year, faction, center, size, ang=0, name=None, road_w=1.4, grid=0):
    """A new quarter: a road out to it from the network, then the zone, optionally a street grid inside."""
    en, zh = name or pick(PATRONS, "dis")
    w = E.w
    r, e = make_road(w, year, {"id": gid("road"), "type": "road", "name": f"Street of {en}"}, center, road_w)
    if r:
        E.build(faction, r, year, f"A street is laid out toward the new quarter of {en}.", f"修一条街通往{zh}新区", name_zh=f"{zh}街")
    d = {"id": gid("dis"), "type": "district", "name": f"Quarter of {en}", "geom": {"type": "polygon", "coords": rect(center[0], center[1], size[0], size[1], ang)}}
    if grid:
        d["spacing"] = rules.CAL["house_spacing_units"]["value"] * 0.95
    g = Polygon(d["geom"]["coords"]).intersection(land().buffer(-2))
    if g.is_empty or g.area < 200:
        E.fail(d["name"], ["the quarter would be at sea"]); return False
    if g.geom_type == "MultiPolygon":
        g = max(g.geoms, key=lambda q: q.area)
    d["geom"]["coords"] = [[round(x, 1), round(y, 1)] for x, y in g.exterior.coords]
    e = ok(w, d, year)
    if e:
        E.fail(d["name"], e); return False
    E.build(faction, d, year, f"Houses are let to settle the quarter of {en}.", f"划出{zh}区，任人建房", name_zh=f"{zh}区")
    for k in range(grid):  # straight cross streets, the planner's hand
        a = math.radians(ang + 90 * (k % 2)); off = (k // 2 - 0.5) * size[1] / 3
        cx, cy = center[0] - math.sin(math.radians(ang)) * off * (k % 2 == 0), center[1] + math.cos(math.radians(ang)) * off * (k % 2 == 0)
        L = size[0] * 0.45
        s = {"id": gid("road"), "type": "road", "name": f"Planned street of {en}",
             "geom": {"type": "line", "coords": [[round(cx - math.cos(a) * L, 1), round(cy - math.sin(a) * L, 1)], [round(cx + math.cos(a) * L, 1), round(cy + math.sin(a) * L, 1)]]}, "width": road_w}
        if not ok(w, s, year):
            E.build(faction, s, year, "A straight street is ruled across the new quarter.", "新区里拉出一条笔直的街", name_zh=f"{zh}直街")
    return True


_LB = []


def _landb():
    if not _LB:
        _LB.append(land().buffer(-3))
    return _LB[0]


def frontier(E, year, direction, step_units=45):
    """Where the built area should grow next: just beyond the current districts in the variant's direction."""
    ds = standing(E.w, year, {"district"})
    u = unary_union([geom(d) for d in ds])
    from shapely.prepared import prep
    ub, lb = prep(u.buffer(2)), prep(_landb())
    dx, dy = direction
    best = None
    for k in range(40):
        c = u.centroid
        t = RND.uniform(-0.6, 0.6)
        vx, vy = dx * math.cos(t) - dy * math.sin(t), dx * math.sin(t) + dy * math.cos(t)
        # walk from the centre to the edge of the built area, then step out
        p = Point(c.x, c.y)
        for i in range(400):
            q = Point(c.x + vx * i, c.y + vy * i)
            if not ub.contains(q):
                p = q; break
        cand = (p.x + vx * step_units * 0.55, p.y + vy * step_units * 0.55)
        if lb.contains(Point(*cand)):
            gl = box(cand[0] - 25, cand[1] - 20, cand[0] + 25, cand[1] + 20).intersection(land()).area
            if best is None or gl > best[0]:
                best = (gl, cand)
    return best[1] if best else None


def wall_line(pts_latlon):
    coords = [to_xy(a, b) for a, b in pts_latlon]
    g = LineString(coords).intersection(land().buffer(-0.5))
    if g.geom_type == "MultiLineString":
        g = max(g.geoms, key=lambda q: q.length)
    return [[round(x, 1), round(y, 1)] for x, y in g.coords]


def build_wall(E, year, faction, coords, name, why, why_zh):
    w = E.w
    line = LineString(coords)
    gates = gates_for(w, year, line, faction, len(E.acts))
    tmp = dict(w); tmp["structures"] = list(w["structures"])
    for gt in gates:
        add(tmp, gt, year)
    tmp["_pending_gates"] = gates
    s = {"id": gid("wall"), "type": "wall", "name": name[0], "geom": {"type": "line", "coords": coords}, "label": name[0]}
    e = ok(tmp, s, year)
    if e:
        E.fail(name[0], e); return False
    for gt in gates:
        E.build(faction, gt, year, f"A gate where the {gt['name'][12:]} passes the new wall.", "新城墙与道路相交处开门", name_zh=f"{gt['name'][12:]}门")
    E.build(faction, s, year, why, why_zh, label=name[0], name_zh=name[1])
    return True


def grow_space(E, year, faction, direction, size=(55, 40), grid=0, tries=3):
    for t in range(tries):
        c = frontier(E, year, direction)
        if c and district(E, year, faction, c, size, ang=road_angle(E.w, year, *c) if not grid else POL.get("grid_angle", 0), grid=grid):
            return True
    return False

# ---------------- the variant's decisions ----------------
def decade(w, y0):
    y1 = y0 + 9
    E = Era(w, y0)
    pop, food, water = stats(w, y0 - 1)
    want = pop * 1.5 + 2000
    pal = palette(y0)
    exec(open("drafts/policy.py", encoding="utf-8").read(), {**globals(), "E": E, "w": w, "y0": y0, "y1": y1, "pop": pop,
         "food": food, "water": water, "want": want, "pal": pal})
    return E


def chronicle(E, era, res):
    y0, y1 = era["from"], era["to"]
    st = res["stats"]; pop = st["population"]
    zh = [f"## {era['title']}（建城 {y0}—{y1} 年）", "",
          f"> 草稿分支「{POL['name_zh']}」自动生成：提案由派系策略写出，规则引擎裁决，以下只记录真正发生的事。", ""]
    en = [f"## {era['title_en']} (AF {y0}–{y1})", "",
          f"> Draft branch \"{POL['name_en']}\", generated: factions propose by policy, the rules engine rules, and this records only what happened.", ""]
    acc = {a["id"] for a in res["accepted"]}
    for f, sid, t, wz, we in E.notes:
        if sid not in acc:
            continue
        zh.append(f"- {FZ.get(f, f)}：{wz}（{{{{{sid}}}}}）")
        en.append(f"- {FE.get(f, f).capitalize()}: {we} ({{{{{sid}}}}})")
    for ev in res["events"]:
        if ev["type"] == "fire":
            zh.append(f"- 第 {ev['year']} 年大火，烧毁 {ev['houses']} 座房屋。"); en.append(f"- A fire in AF {ev['year']} burned {ev['houses']:,} houses.")
        elif ev["type"] == "earthquake":
            zh.append(f"- 第 {ev['year']} 年地震，倒塌建筑 {len(ev['structures'])} 座。"); en.append(f"- An earthquake in AF {ev['year']} threw down {len(ev['structures'])} buildings.")
        else:
            zh.append(f"- 第 {ev['year']} 年瘟疫，{ev['houses']} 户人家死绝或逃散。"); en.append(f"- Plague in AF {ev['year']} emptied {ev['houses']:,} houses.")
    nrej = len(res["rejected"]) + len(E.rej)
    zh += ["", f"十年末城里有 {pop:,} 人，粮食上限 {st['food']:,}，水 {st['water']:,}，房屋 {st['houses']:,} 座。" + (f"被规则驳回或放弃的提案 {nrej} 件。" if nrej else "")]
    en += ["", f"At the decade's end the city held {pop:,} people; food ceiling {st['food']:,}, water {st['water']:,}, houses {st['houses']:,}." + (f" {nrej} proposals were rejected or abandoned." if nrej else "")]
    open(f"chronicle/{y0}_{y1}.md", "w", encoding="utf-8").write("\n".join(zh) + "\n")
    open(f"chronicle/en/{y0}_{y1}.md", "w", encoding="utf-8").write("\n".join(en) + "\n")


def run(*a):
    r = subprocess.run([sys.executable, *a], capture_output=True, text=True)
    if r.returncode not in (0, 1):
        print(r.stdout[-3000:], r.stderr[-3000:]); sys.exit(1)
    return r


STATE = "drafts/_state.json"


def save_state(y_next):
    json.dump({"used": _used, "rnd": [RND.getstate()[0], list(RND.getstate()[1]), RND.getstate()[2]], "y_next": y_next}, open(STATE, "w"))
    json.dump(I18N, open(I18N_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def main():
    import time
    T0, BUDGET = time.time(), float(os.environ.get("BUDGET", "1e9"))
    to = POL["to_year"]
    if "--resume" in sys.argv and os.path.exists(STATE):
        st = json.load(open(STATE)); _used.update(st["used"]); RND.setstate((st["rnd"][0], tuple(st["rnd"][1]), st["rnd"][2]))
        w = load(); y0 = st["y_next"]
        assert w["eras"][-1]["to"] + 1 == y0, "world.json and state disagree"
        return grow_from(w, y0, to, T0, BUDGET)
    for f in glob.glob("proposals/era_*.json"):  # earlier drafts of this branch are regenerated
        if json.load(open(f))["era"]["from"] > POL["fork_after"]:
            os.remove(f)
    props = sorted(glob.glob("proposals/era_*.json"), key=lambda p: json.load(open(p))["era"]["from"])
    run("engine/genesis.py")
    import io, contextlib
    for p in props:
        with contextlib.redirect_stdout(io.StringIO()):
            STEP.main(p)
    w = load()
    return grow_from(w, w["eras"][-1]["to"] + 1, to, T0, BUDGET)


def grow_from(w, y0, to, T0, BUDGET):
    import time
    while y0 <= to:
        if time.time() - T0 > BUDGET:
            save_state(y0); print("PAUSED at", y0, flush=True); sys.exit(3)
        E = decade(w, y0)
        title, title_en = getattr(E, "title", ("十年", "A decade"))
        era = {"era": {"from": y0, "to": y0 + 9, "title": title}, "actions": E.acts, "growth_floor": POL.get("growth_floor", 150)}
        if E.rej:
            era["review"] = [{"round": 1, "abandoned": E.rej}]
        path = f"proposals/era_{y0:04d}.json"
        json.dump(era, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
        I18N["titles_en"][str(y0)] = title_en
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            STEP.main(path)
        w = load(); last = w["eras"][-1]; res = last
        chronicle(E, {"from": y0, "to": y0 + 9, "title": title, "title_en": title_en}, last)
        print(f"AF {y0}-{y0+9} {title}: pop {res['stats']['population']:,} food {res['stats']['food']:,} water {res['stats']['water']:,} "
              f"+{len(res['accepted'])} acc, {len(res['rejected'])} rej, {len(E.rej)} abandoned, events {[e['type'] for e in res['events']]}", flush=True)
        y0 += 10
        save_state(y0)
    r = run("engine/check.py"); print(r.stdout.strip()[-2500:])


if __name__ == "__main__":
    main()
