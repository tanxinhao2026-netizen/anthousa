# Public works & epic buildings — integration design (draft, 2026-10-13)
User asked (23:45): start designing how public facilities and epic buildings join in. Design only; no code until CS goal 3 lands.

## What exists
- world.json (engine) already carries the epic set as structures with built years: palace_great, hippodrome, forum_founder + col_founder + milion (AF1), church_peace (1), church_apostles (11), aq_great + 3 aqueduct bridges + nymphaeum_great (11), baths_constantius (25), church_megale (30), horrea_theodosius (34), harbor_theodosius (33), cistern_modestus (41), nymphaeum_maius (44), horrea_troadensia (46), horrea_alexandrina (55), forum_theodosius (57), harbors, walls, gates.
- living/ draws only Xerolophos + its fixed landmarks; CS tiles page shows arena/palace/theatre as tiles content.
- Gap: epic buildings are points/polygons in the engine, not buildings with shape, stages and life in the city.

## Principle
One registry, three classes (all spec cards in gen/landmarks/*.json, read by landmark_registry):
1. local (exists): bread steps, church, fountain, inn, kiln, macellum, cemetery — placed on lots.
2. public works = NETWORKS: water (aqueduct → cisterns → nymphaea → fountains), grain (harbors → horrea → bread steps), baths, walls/gates. Spec adds `serves` {kind, radius|capacity} and `fed_by` (upstream id). Engine ledger already counts water/food caps; the network makes them visible: a fountain only runs when its cistern is built, a bread step only queues when a horrea feeds it.
3. epic (monumental): class `epic`, size `own_block`. They are FIXED by history (id = world.json structure id, keeps built/destroyed from engine — never invent dates). They RESERVE ground before streets: streets_xero/tiles route around their footprint, district_rules reads their influence (palace → fine, hippodrome → shops/taverns, forum → market).

## Epic spec fields (beyond the landmark card)
- engine_id (link to world.json structure; built year read from there)
- footprint: real proportions in metres → city px (hippodrome ~450×120 m; Hagia Sophia first basilica ~ 120×70 m incl. atrium; forum ~ 100 m oval)
- parts: shape vocabulary extended with large primitives: oval_forum (colonnade ring + column), circus (track, spina, carceres, sphendone, kathisma link to palace), palace (terraces, courts, halls), great_basilica (timber roof, atrium), aqueduct arcade, harbor mole.
- stages tied to chronicle events (construction scaffold → dedication → fire / repair) — 360 Megale Ekklesia dedication, 404 fire is out of timeline.
- lens: how each view shows it (keyframe painting overlay / procedural parts / tiles LOD: far = silhouette, mid = parts, near = detail + people).
- life hooks: scenes (races at the hippodrome, bread dole, liturgy), street names (Mese, "by the Milion").

## Order (proposal)
1. After CS goal 3: map each world.json monumental structure to a spec card (data only, engine dates).
2. Networks first (water, grain): cheap, data already in ledger, makes existing landmarks "connected".
3. One epic piece end-to-end as template: Forum of Constantine (oval + porphyry column, on the Mese, AF1) — smallest, central, touches tiles + main.
4. Then Hippodrome + Great Palace pair, Megale Ekklesia (AF30), Forum of Theodosius (AF57).
Out of timeline: Forum of Arcadius (403), Justinian's Hagia Sophia (537).

## Open questions for user
- Where epic buildings are drawn: main living page, CS tiles, or both (registry shared, render per lens).
- Scale honesty: real metre proportions vs. readable exaggeration.
