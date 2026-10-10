# 史实版：按真实君士坦丁堡的节奏长。地标按年份落在真实经纬度上（AF = 公元 - 329），
# 其余十年由瓶颈驱动：水不够修蓄水池/水道，粮不够修港，地方不够向西扩街区。
LM = {
 64: [("emperor", "forum", "peristyle", (14, 10), (41.0106, 28.9640), ("Forum of Theodosius", "狄奥多西广场"), "The emperor lays out a second great forum on the Mese, with a triumphal arch.", "皇帝在中央大道上开出第二座大广场，立起凯旋门", 3, "monumental")],
 73: [("emperor", "column", "column_monument", (3, 3), (41.0047, 28.9440), ("Column of Arcadius", "阿卡狄乌斯纪念柱"), "A spiral column for Arcadius rises on the Xerolophos hill.", "为阿卡狄乌斯立起螺旋纪念柱", 2, "monumental")],
 92: [("emperor", "cistern", "cistern", (20, 7), (41.0256, 28.9439), ("Cistern of Aetius", "埃提乌斯蓄水池"), "The prefect Aetius digs a vast open reservoir by the Charisian road.", "城守埃提乌斯在城北挖出巨大的露天蓄水池", 0, "civic")],
 121: [("church", "church", "basilica", (6, 4), (41.0390, 28.9426), ("Church of the Blachernae", "布拉赫奈教堂"), "By the holy spring at Blachernae the empress builds a church for the Virgin's robe.", "皇后在布拉赫奈圣泉旁为圣母袍修教堂", 3, "civic")],
 130: [("people", "cistern", "cistern", (12, 12), (41.0255, 28.9520), ("Cistern of Aspar", "阿斯帕蓄水池"), "General Aspar pays for a square reservoir on the fifth hill.", "将军阿斯帕出资，在第五丘修方形蓄水池", 0, "civic")],
 134: [("church", "monastery", "monastery", (8, 6), (40.9967, 28.9283), ("Monastery of Stoudios", "斯图狄奥斯修道院"), "The consul Stoudios founds a monastery near the Golden Gate.", "执政官斯图狄奥斯在金门附近建修道院", 2, "civic")],
 162: [("emperor", "cistern", "cistern", (14, 12), (41.0170, 28.9370), ("Cistern of Mocius", "莫基乌斯蓄水池"), "Anastasius digs the largest open cistern of all on the seventh hill.", "阿纳斯塔修斯在第七丘挖出最大的露天蓄水池", 0, "civic")],
 198: [("church", "church", "domed_basilica", (6, 6), (41.0026, 28.9725), ("Saints Sergius and Bacchus", "圣塞尔吉乌斯与巴克斯教堂"), "Justinian raises a domed octagon by the palace for two soldier saints.", "查士丁尼在皇宫旁为两位军人圣徒修穹顶八角堂", 3, "monumental")],
 203: [("emperor", "cistern", "cistern", (11, 6), (41.0084, 28.9779), ("Basilica Cistern", "地下水宫"), "Under the Stoa Basilica a forest of columns holds the palace's water.", "在大巴西利卡下面，一片石柱林托着皇宫的水", 1, "civic")],
}
CE = y0 + 329
titles = []
# 1) the walls of Theodosius (413 = AF 84)
if y0 <= 84 <= y1:
    ok_ = build_wall(E, 84, "army", wall_line([(40.9930, 28.9150), (40.9962, 28.9225), (41.0178, 28.9196), (41.0300, 28.9330), (41.0395, 28.9395), (41.0440, 28.9440)]),
                     ("Walls of Theodosius", "狄奥多西城墙"), "With the Goths a day's ride away, the regency builds a land wall two kilometres west of Constantine's.",
                     "哥特人一天就能骑到城下，摄政府在君士坦丁城墙以西两公里修起新的陆墙")
    titles.append(("新城墙", "The New Walls"))
# 2) scheduled real landmarks
for y, items in LM.items():
    if y0 <= y <= y1:
        for f, t, m, sz, ll, nm, we, wz, orn, sc in items:
            x, yy = to_xy(*ll)
            s = building(E, y, f, t, m, sz, [(x, yy)], 6, nm, we, wz, orn=orn, scale=sc, avoid=0.2)
            if not s:
                s = building(E, y, f, t, m, sz, [(x, yy)], 18, nm, we, wz, orn=orn, scale=sc, avoid=0.2)
# Nika riot (532 = AF 203): the Great Church burns; Justinian's Hagia Sophia (537 = AF 208)
if y0 <= 203 <= y1 and by_id(w, "church_megale") and by_id(w, "church_megale").get("destroyed") is None:
    E.demolish("people", "church_megale", 203, "Burned in the Nika riot.", {"kind": "chronicle_feature", "note": "The old Great Church burned in the Nika riot; its name passes to the new church."})
    titles.append(("尼卡暴动", "The Nika Riot"))
if y0 <= 208 <= y1:
    x, yy = to_xy(41.0086, 28.9802)
    s = building(E, 208, "emperor", "church", "domed_basilica", (10, 9), [(x, yy)], 4, ("Hagia Sophia", "圣索菲亚大教堂"),
                 "On the ashes Justinian raises a dome that seems hung from heaven.", "查士丁尼在灰烬上建起一座仿佛从天上悬下的穹顶", orn=3, scale="wonder", avoid=0)
    titles.append(("圣索菲亚", "Hagia Sophia"))
# 3) the bottleneck of the decade
short = min(("water", water), ("food", food), key=lambda k: k[1])
if water < want:
    if water < want - 60000 and len(standing(w, y0, {"aqueduct"})) < 4:
        new_aqueduct(E, y0 + 2, "emperor", "A second channel from the Thracian hills doubles the city's water.", "从色雷斯山地再引一条水渠", name=pick([("Aqueduct of Theodosius", "狄奥多西水道"), ("Aqueduct of Justinian", "查士丁尼水道"), ("Aqueduct of Heraclius", "希拉克略水道")], "aqn"))
    else:
        cistern(E, y0 + 3, "people", [CITY_C, (480, 400), (420, 430)], 70)
    titles.append(("储水", "Storing Water"))
if food < want:
    h = harbor(E, y0 + 1, "merchants", (380, 470, 700, 560))
    if h:
        c, r = near(h, 16)
        building(E, y0 + 2, "emperor", "granary", "basilica", (9, 5), c, r, ("Horrea " + h["name"][10:], h["name"][10:] + "粮仓"),
                 "State granaries rise behind the new quays.", "新码头后面建起国家粮仓", label=False)
    titles.append(("海上粮路", "The Sea Road for Grain"))
n_ = 0
while district_room(E.w, y0) < pop / 9 * 0.7 and n_ < 3:
    grow_space(E, y0 + 4, "people", (-1, RND.uniform(-0.4, 0.4)), size=(70, 55)); n_ += 1
if n_:
    titles.append(("向西", "Westward"))
# churches and baths as the city fills
if pop > 120000 and RND.random() < 0.6:
    en, zh = pick(SAINTS, "saint")
    building(E, y0 + 5, "church", "church", RND.choice(["basilica", "basilica", "cross_in_square"] if CE > 600 else ["basilica"]), (6, 4),
             [CITY_C, (470, 420), (400, 440)], 80, (f"St {en}", f"圣{zh}教堂"), f"A parish church for St {en} serves the new streets.", f"为圣{zh}修一座堂区教堂", orn=2, label=False)
if RND.random() < 0.3:
    building(E, y0 + 6, "people", "baths", "basilica", (8, 6), [CITY_C, (450, 420)], 80, pick([("Baths of Zeuxippus II", "宙克西帕斯浴场二期"), ("Baths of Arcadius", "阿卡狄乌斯浴场"), ("Baths of Dagistheus", "达吉斯特乌斯浴场")], "bath"),
             "Public baths for a growing quarter.", "为新街区修公共浴场", label=False)
if not E.acts:
    building(E, y0 + 5, "church", "monastery", "monastery", (8, 6), [(330, 420), (300, 460)], 60, pick([(f"Monastery of {a}", f"{b}修道院") for a, b in SAINTS], "mon"),
             "Monks settle among the gardens inside the new walls.", "修士们在新城墙内的园地间定居", label=False)
E.title = (titles[0] if titles else ("平常的十年", "A Quiet Decade"))
