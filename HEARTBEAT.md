# Heartbeat runbook (one wake = one decade)

1. Read world.json: last era's stats, rejections, events; read its chronicle.
2. Write proposals/era_NNNN.json for the next decade as five factions (emperor, church, merchants, people, army).
   Respond to pressure first (water, food, fire damage, crowding); then ambition.
   Grandeur rule: at least one monumental project in progress every 3 eras.
3. `python3 engine/step.py <file> --dry-run`; revise rejected actions at most 2 rounds; log them under "review".
   Rejections you choose not to fix stay in history.
4. Commit: `python3 engine/step.py <file>`; write chronicle/<from>_<to>.md (Chinese) AND chronicle/en/<from>_<to>.md (English, same {{id}} refs); add every new id to i18n/i18n.json (names_zh, labels_zh, titles_en). Keep proposals/make_era_NNNN.py so the era is reproducible; final state must come from engine/build_all.py.
5. `python3 engine/check.py` must pass; an independent reviewer (separate agent) reads chronicle vs data for contradictions.
6. `python3 engine/render.py`; publish docs/ and changed files.
Brakes: check fails twice in a row → stop, ask the user. Every 10 eras (a century) → pause for the user's direction.

## 建筑语法（从 AF 21 起生效，见 docs/arch-grammar-draft.md）
- 每个 `build` 的建筑（道路、城墙、水渠、港口、街区、拱廊除外）必须带 `dna: {motif, materials, ornament, scale}`；motif 必须在 `rules/motifs.json` 的 `type_map` 里对该类型允许。缺失或不符 → 驳回。
- 材料超出当时风格期调色板只给 warning，记录在 accepted 条目的 `warnings` 里，可以在下一轮修订。
- `spolia_from: [ids]` 只能指向已经毁掉的建筑；`scale: wonder` 面积 ≤ 120 平方单位，每十年最多开工一座。
- 拆除奇观分 ≥ 3 的建筑必须带 `memorial: {kind: stele|rename|chronicle_feature, note}`。
- 用 `grammar.motif_for(faction, era)` 可以按派系口味抽母题；声望只影响提案，不影响裁决。

## 人物层（从 AF 31 起试运行，见 docs/persons-schema.md）
- 每个十年，从本十年事件与建筑里析出 3–5 个具名人物，写入 `persons/af_NNNN.json` 源文件（`world.json` 是派生文件，由 build_all.py 合并生成，不直接写）。
- 人物字段：`{id, name, name_en, born, died, trade, faction, address, address_note, status, last_mentioned, bio, linked}`；`bio` 约 200 字，必须引用真实存在的建筑或事件 `{{id}}`，不许编造地点。
- 人物会变老（每十年 +10 岁）、会死（按年龄与事件/骰子推定）；`last_mentioned` 记最后被提起的十年；连续两个十年无人提起且未被编年史引用 → `status: faded`；被编年史引用过的永不删除。
- 编年史引用人物用 `{{p_xxx}}` 语法；check.py 人物引用校验分支下一 PR 实现。
- 只读引用 proposals/chronicle/engine 数据；属于 A 类（历史推进）。
