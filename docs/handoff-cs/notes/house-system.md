# 房屋体系设计 (draft 2026-10-12, proposed to user, awaiting go-ahead)

Problem (user, v23): districts differ but weakly — every house is the same hipped box; only palette/lot size change.

Chain: 街区 district → 地块 lot (shape, frontage, corner, depth) → 建筑类型 typology → 构件 parts → 财富/时代/年龄 modifiers.

Typologies (each must read at whole-city zoom by silhouette + lot ground, not colour):
- 铺面连排 taberna row: one continuous ridge along the street, shared gables, 2 storeys, colonnade strip on main avenues, awnings/stalls.
- 院宅 courtyard house: O/U roof ring around open court with green/impluvium + tree; lot wall; 1–3 per block.
- 公寓楼 insula: 3–4 storeys, big footprint, near markets/dense centre, long shadow.
- 作坊院 workshop yard: low shed roof + dirt yard, kiln smoke, stacks (amphorae, timber), lean-tos.
- 民居小屋 casa: small 1 storey gable, clusters of 2–4 sharing walls, small yard.
- 兵营长屋 barrack halls; 菜园小屋 hut + plot rows; 新街坊标准屋 identical module, same orientation and tile.
Rules: lot shape → type candidates; district → probability table; wealth gradient (baths, avenues, high ground) → storeys/size; old quarter irregular + accretion, new quarter regular.
Time within a house's own life (ids/years fixed): 地基→木架→墙→屋顶→完工→加层/加建→老旧→废墟/拆除.
Data: house row gets typ, storeys, wealth, seed; one shared house_types.json read by both render_xero.py and index.html (ends the STYLE/HSTYLE duplication).
Phases: P1 types + lot→type + shared spec + roof forms; P2 lot ground (court, yard, plots, stalls); P3 life evolution + wealth; P4 district kits (palace marble, harbour warehouses).
