# 帝都版：自上而下。皇帝每十年把一条笔直的帝国中轴向西推一段，沿轴每隔一段开一座广场、立一根柱；
# 两侧划方格街区；每隔一个十年起一座奇观；水靠一条接一条的新水道，粮靠国家粮仓（年金制，粮仓容量更大）。
k = (y0 - 41) // 10 + 1                       # this decade's stage of the axis
# when the first axis meets the walls, the emperor starts a second one, north-west from the Forum of Constantine
AXES = [((611.0, 454.0), POL["axis_angle"], 9), ((520.0, 400.0), 215, 6), ((560.0, 470.0), 160, 5)]
for AX0, angd, nseg in AXES:
    if k <= nseg:
        break
    k -= nseg
ANG = math.radians(angd)
seg = 38
a = (AX0[0] + math.cos(ANG) * seg * (k - 1), AX0[1] + math.sin(ANG) * seg * (k - 1))
b = (AX0[0] + math.cos(ANG) * seg * k, AX0[1] + math.sin(ANG) * seg * k)
titles = []
if land().buffer(-4).contains(Point(*b)):
    s = {"id": gid("axis"), "type": "road", "name": f"Imperial Axis, stage {k}", "width": 2.6,
         "geom": {"type": "line", "coords": [[round(a[0], 1), round(a[1], 1)], [round(b[0], 1), round(b[1], 1)]]}}
    tmp = copy.deepcopy(w); gs = gates_for(tmp, y0, LineString(s["geom"]["coords"]), "emperor", k)
    e = ok(w, s, y0)
    if not e:
        E.build("emperor", s, y0, "The emperor drives the colonnaded axis another half kilometre west, through whatever stands in the way.",
                "皇帝把带柱廊的中轴大道再向西推半公里，挡路的一律拆除", name_zh=f"帝国中轴·第{k}段")
        titles.append(("中轴西进", "The Axis Marches West"))
    else:
        E.fail(s["name"], e)
    if k % 2 == 0:
        en, zh = pick(PATRONS, "forum")
        f = building(E, y0 + 2, "emperor", "forum", "peristyle", (16, 12), [b], 10, (f"Forum of {en}", f"{zh}广场"),
                     f"A forum for {en} at the new end of the axis, ringed with porticoes.", f"在中轴新的尽头为{zh}开广场，四周环以柱廊", orn=3, scale="monumental", avoid=0)
        if f:
            c = geom(f).centroid
            building(E, y0 + 3, "emperor", "column", "column_monument", (3, 3), [(c.x, c.y)], 3, (f"Column of {en}", f"{zh}纪念柱"),
                     f"A porphyry column for {en} stands in the forum's centre.", f"广场中央立起{zh}的斑岩纪念柱", orn=3, scale="monumental", label=False, avoid=0)
    # planned quarters on both sides of the axis
    for side in (1, -1):
        cx = (a[0] + b[0]) / 2 - math.sin(ANG) * 34 * side; cy = (a[1] + b[1]) / 2 + math.cos(ANG) * 34 * side
        if land().buffer(-5).contains(Point(cx, cy)):
            district(E, y0 + 1, "emperor", (cx, cy), (40, 50), ang=angd, grid=2, road_w=1.6)
n_ = 0
while district_room(E.w, y0) < pop / 9 * 0.7 and n_ < 2:
    grow_space(E, y0 + 4, "emperor", (-1, RND.uniform(-0.5, 0.5)), size=(60, 50), grid=2); n_ += 1
# a wonder every other decade
if k % 2 == 1 and k > 1:
    en, zh = pick(SAINTS, "won")
    m = RND.choice(["rotunda", "domed_basilica"])
    building(E, y0 + 5, "emperor", "church", m, (10, 10), [AX0, a], 60, (f"Great Church of St {en}", f"圣{zh}大教堂"),
             f"The emperor raises a domed church for St {en} that every ship on the sea can see.", f"皇帝为圣{zh}修一座海上每条船都望得见的穹顶大教堂", orn=3, scale="wonder", avoid=0)
    titles.append(("奇观", "A Wonder"))
# water: the state builds aqueducts
if water < want:
    if not new_aqueduct(E, y0 + 1, "emperor", "Another imperial aqueduct comes down from the Thracian hills.", "又一条帝国水道从色雷斯山地引下",
                        name=pick([(f"Aqueduct of {a_}", f"{b_}水道") for a_, b_ in PATRONS], "aqn")):
        cistern(E, y0 + 3, "emperor", [a, b, CITY_C], 60, size=(14, 12))
    titles.append(("水", "Water by Decree"))
# food: the annona
if food < want:
    building(E, y0 + 2, "emperor", "granary", "basilica", (12, 6), [(560, 505), (480, 505), a], 50, pick([(f"Horrea of {a_}", f"{b_}粮仓") for a_, b_ in PATRONS], "hor"),
             "State granaries for the free bread of the annona.", "国家粮仓，供年金制的免费面包", label=False, orn=1)
    if food < want - 40000:
        h = harbor(E, y0 + 1, "emperor", (380, 470, 700, 560))
    titles.append(("年金", "The Annona"))
# the emperor's wall, far west, once (AF 70)
if y0 <= 70 <= y1:
    build_wall(E, 70, "army", wall_line([(40.9925, 28.9080), (40.9960, 28.9150), (41.0180, 28.9120), (41.0310, 28.9250), (41.0430, 28.9320), (41.0480, 28.9380)]),
               ("Wall of the Emperors", "帝王长城"), "The emperor rings a city not yet built with a wall far beyond the houses.", "皇帝在房屋还远未长到的地方，为一座尚不存在的城市圈起城墙")
    titles.append(("帝王长城", "The Emperors' Wall"))
if RND.random() < 0.4:
    building(E, y0 + 6, "emperor", "palace", "peristyle", (14, 10), [(660, 500), (620, 510), b], 40, pick([(f"Palace of {a_}", f"{b_}宫") for a_, b_ in PATRONS], "pal"),
             "Another palace for the court, its gardens running down to the sea.", "为宫廷再建一座宫殿，花园一直铺到海边", orn=3, scale="monumental")
E.title = titles[0] if titles else ("帝国的十年", "An Imperial Decade")
