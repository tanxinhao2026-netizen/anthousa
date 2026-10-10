# 商港版：自下而上。商人每十年在金角湾和马尔马拉海岸再挖一两座港，港后面是货栈和市场，
# 房子跟着码头长，沿岸成带；没人出钱修新城墙；木屋密集，火灾更常见（规则里火灾概率更高）。
REG = [(560, 330, 680, 390), (380, 470, 560, 560), (440, 250, 600, 360), (250, 470, 420, 560), (330, 150, 520, 290), (150, 470, 300, 560)]
titles = []
nh = 2 if food < want else 1
for i in range(nh):
    reg = REG[((y0 - 41) // 10 * 2 + i) % len(REG)]
    h = harbor(E, y0 + 1 + i, "merchants", reg, size=(16, 11))
    if h:
        c, r = near(h, 14)
        building(E, y0 + 2 + i, "merchants", "warehouse", RND.choice(["basilica", "insula"]), (8, 4), c, r,
                 pick([(f"Warehouses of {a_}", f"{b_}货栈") for a_, b_ in PATRONS], "wh"), "Warehouses crowd the new quay.", "新码头后面挤满货栈", label=False, orn=0)
        building(E, y0 + 3 + i, "people", "market", "market_row", (8, 5), c, r + 6,
                 pick([("Fish Market", "鱼市"), ("Spice Row", "香料街"), ("Silk Stoa", "丝绸柱廊"), ("Timber Yard Market", "木料市"), ("Wine Exchange", "酒市"), ("Grain Exchange", "粮食交易所")], "mk"),
                 "Stalls and shops follow the ships.", "摊铺跟着船来", label=False, orn=1)
        hc = geom(h).centroid
        # houses follow the quays: a new quarter just inland of the harbor
        dx, dy = CITY_C[0] - hc.x, CITY_C[1] - hc.y; n = math.hypot(dx, dy) or 1
        cen = (hc.x + dx / n * 28, hc.y + dy / n * 28)
        district(E, y0 + 2 + i, "people", cen, (46, 32), ang=road_angle(w, y0, *cen))
titles.append(("新码头", "New Quays"))
if water < want:
    if water < want - 70000 and RND.random() < 0.5:
        new_aqueduct(E, y0 + 3, "people", "The guilds club together for a new channel from the hills.", "行会凑钱，从山里再引一条水渠",
                     name=pick([("Guild Aqueduct", "行会水道"), ("Aqueduct of the Merchants", "商人水道"), ("Harbor Aqueduct", "港口水道")], "aqn"))
    else:
        cistern(E, y0 + 4, "merchants", [CITY_C, (500, 420)], 70, size=(9, 7))
    titles.append(("买水", "Buying Water"))
if district_room(E.w, y0) < pop / 9 * 0.6:
    grow_space(E, y0 + 5, "people", (-1, RND.uniform(-0.7, 0.7)), size=(50, 36))
if RND.random() < 0.35:
    en, zh = pick(SAINTS, "saint")
    building(E, y0 + 6, "church", "church", "basilica", (5, 3), [CITY_C, (500, 450)], 80, (f"St {en} of the Sailors", f"水手的圣{zh}堂"),
             f"Sailors build a small church for St {en}.", f"水手们为圣{zh}修一座小教堂", orn=1, label=False)
E.title = titles[0]
