# 干山线 → CS 线交接包（2026-10-14）

用户已把 CS 线的瓦片页定为主线。本目录是干山线（Xerolophos，上游 main）此后只在本地、**从未推上 main** 的全部成果，外加设计稿。
CS 线按需取用；main 上的 docs/living/ 保持不动，下面每一项都能单独拿。

## 一、可以直接用的（按价值排序）

### 1. 三种新地标卡（v31）—— 直接进登记册
`tools/landmarks/macellum.json`（肉鱼市）、`kiln.json`（砖窑）、`cemetery.json`（城外墓地）
+ 配套 `tools/landmark_shapes.py`（ring/drum 等新形体）、`tools/landmarks.py`（新增 siting：`outside_wall`、`prefer_merge`/`merge_max` 合并地块）。
- 肉鱼市：露天摊子 → 8 年后铺面围成环 + 中央柱廊圆亭；合并相邻地块（拆掉的房子按落成前一年拆，进底账即可）。
- 砖窑：城墙边，1 座 → +6 年添第二座。
- 墓地：只在城墙外，墓碑一年年多，柏树，墓屋。
- 都是 spec 驱动，跑 `landmark_registry.py sync` 即进登记册；严格审计（房屋不压路）0。
- 预览：`preview/v31_new_landmarks.png`、`preview/v31_macellum_block.png`

### 2. 史诗建筑与公共设施设计稿
`notes/epic-system.md`：一套登记册三类建筑（街坊地标 / 公共设施做成网络 / 史诗建筑）。
- 水网：水渠 → 蓄水池 → 宁芙泉 → 街角喷泉，上游没建，下游不出水；粮网：港口 → 粮仓 → 面包台阶。
- 史诗建筑 id = world.json 结构 id，年份只读引擎、不编；先占地、街道绕行；带分期（脚手架 → 落成 → 加建）。
- 很适合瓦片页：瓦片是镜头，这些是内容。

### 3. 狄奥多西广场 / 大宁芙泉 / 梅塞柱廊大道原型（render_xero.py）
时间节点（全部来自引擎）：
- 大宁芙泉 AF44：铺石前庭、水池、两层半圆柱廊壁龛 + 铅灰半穹顶。
- 狄奥多西广场 AF57 拆平堆石 → AF59 铺地 + 四面瓦顶柱廊（梅塞穿过处断开）→ 纪念柱 AF57 起每年升一段、AF57–63 脚手架、AF64 顶上镀金像 → AF60 西口凯旋门跨梅塞。
- 广场生活：错缝石板、梅塞磨出的旧路、铜牛（Forum Tauri）、6 座雕像、柱廊下 10 个布棚、约 70 人。
- 梅塞大道：世界数据“25 m 带柱廊”→ 干山画幅约 30 px（`MESE_W=30`），石板路面 + 两侧瓦顶柱廊 + 大理石柱，支路处断开。
- 代码：`epic_ground()`、`epic_tall()`、`mese_portico()`；坐标用 world.json 脚印：Forum `[[2005,1138],[2147,1138],[2147,1251],[2005,1251]]`，Nymphaeum `[[2180,1066],[2250,1054],[2257,1095],[2187,1108]]`（干山局部坐标 `local = 14.22*(world-(400,356))`）。
- 预览：`preview/epic_forum_v2.jpg`、`epic_forum_theodosius.jpg`、`epic_mese_before_after.jpg`；在线 https://tanxinhao2026-netizen.github.io/anthousa/preview/epic/

### 4. 道路/房屋规则（建议在 CS 的烘焙流程里沿用）
- 硬规则：任何房屋（墙+屋顶）在存续期内都不压在当年存在的路上（`audit_streets.py` strict 必须为 0）。
- 终扫：蓄水池、广场、宁芙泉建成后，穿过它们的小巷封闭（给结束年）；渠桥下只允许大街（s/m）穿拱，小巷不行。
- 史诗地块清场：墙体伸进广场（或宁芙泉外扩 10 px）的房子在开工年拆除 → 正好写进你们底账 `cause=cleared for X`。
- `prune_islands.py`：任一年份与路网断开的小巷/院巷直接放弃。
- 结果（AF60）：禁区冲突 0，压路 0。

## 二、数据（只作参考，别直接覆盖）
`data/xerolophos/`：东扩后的干山（画幅 1820→2420，加了 2053 座引擎东侧房子 `houses_east.json`，新路 牛场北街/南坡大路/老西路）。
注意：东扩时整张路网按种子重排了，故事里的街名和 v30 不同，肉鱼市位置也变了；如果 CS 已有自己的干山底账，**以 CS 为准，只取规则和代码**。

## 三、流水线（干山线）
streets_xero → prune_islands → audit_streets fixpo → landmarks → blocks_xero → name_streets → place_scenes → render_xero（`render_xero.py epic 43 56 60 64` 出广场分期图）。
房屋行 h：[id, ?, 建, 拆, 脚印8数, …, h[7]高, h[8]街区功能, h[9]类型或 'lm:<地标id>', …]；详见 `notes/house-system.md`、`notes/landmark-system.md`、`notes/versions.md`。

## 四、没做完的
- 东扩与史诗绘制还没接进任何页面 JS（living 页仍按 1820 宽）。
- 竞技场、大皇宫、圣使徒等其余史诗建筑只有设计，没有原型。
- 孤立小段 22（多为北边一条街没碰到画幅边，旧问题），离路远的房子 15。

——Hark（干山线）

---
## 补交 ②（2026-10-14 晚）：帝国中心与圣使徒教堂原型
`tools/epic_core.py`，独立脚本，直接读 world.json + anthousa_world3d.json（地形、水、引擎房屋），坐标比例与干山相同（14.22 px / 世界单位，约 0.84 m/px）。
`python3 epic_core.py core 0 1 30 60`、`python3 epic_core.py apostles 10 11`。
年份全部来自引擎，不新编：
- **君士坦丁广场 + 斑岩柱**（forum_founder / col_founder，AF1）：椭圆双层瓦顶柱廊，梅塞穿过处两座大理石拱门，中心错缝大理石铺地、约 90 人；柱约 37 m：基座 + 7 节斑岩鼓石，每节金色月桂箍，顶上镀金立像与放射冠。
- **米利翁**（AF1）：四面拱门 + 铅穹顶。
- **竞技场**（AF1，约 450 m）：北端 12 道起跑门（carceres），南端半圆看台（sphendone），中央分隔墙（spina）带雕像与两头折返柱，8 级台阶看台上约 900 名观众，东侧皇帝包厢（kathisma）朝向大皇宫，场内四色战车。
- **大皇宫**（AF1）：三级台地向海跌落，每级一排殿宇（瓦/铅顶），列柱庭院带花园与水池，带拱顶的会堂、穹顶殿、北侧铜门（Chalke）圆顶门楼、临海护墙。
- **圣和平教堂**（AF1）与 **大教堂**（church_megale，AF30）：前庭柱廊 + 喷泉、中殿高侧窗、侧廊、东端半圆后殿；大教堂南侧露出拜扎斯旧墙石砌的地基（引擎原文）。
- **圣使徒教堂**（AF11）：十字形、交叉处鼓座穹顶，东端创城者陵墓圆堂；旁边水渠画出拱洞。
- **梅塞柱廊**沿用 CS 已采用的分期（1–2 年立架、3 年起瓦顶），在广场与集市段断开。
- 共用：`prism`（斜投影立体块，含带洞多边形自动拆分）、`dome`、`colonnade`、`people`、`trees`（空地上的灌木/橄榄，避开房、路和建筑）。
预览：`preview/epic_core_af0_af1.jpg`、`epic_core_af30.jpg`、`epic_core_af60.jpg`、`epic_apostles_af10_11.jpg`。
已知：大皇宫内部布局是程序生成的示意，不是考古平面；竞技场观众是常驻装饰，没有赛日节律。
——Hark（干山线）
