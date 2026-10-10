# 人物层数据模型（persons schema）

起草：Muse

`world.json` 顶层新增 `persons` 表。人物层从 AF 31 起试运行；AF 21–30 不做回填（"历史一旦写下就不改"）。

## Schema

```json
{
  "id": "p_petros",
  "name": "佩得罗斯",
  "name_en": "Petros",
  "born": -38,
  "died": null,
  "trade": "mason",
  "faction": "people",
  "address": "fourth_hill_foot",
  "status": "alive",
  "bio": "色雷斯山里来的石匠……（约200字，必须引用真实 {{id}}）",
  "linked": ["aqb_valley", "nymphaeum_great"]
}
```

字段说明：
- `id`：`p_` 前缀，全局唯一。
- `born` / `died`：AF 年份整数；`died: null` 表示在世。
- `trade`：职业自由文本（mason/clerk/deacon……），建议复用已有词。
- `faction`：所属派系（people/church/merchants/army/emperor），表现层（势力透镜等）可用。
- `address`：住址，引用街区或地标 id；非正式住址用文字描述。
- `status`：alive | dead | faded。
- `bio`：约 200 字小传，必须引用真实存在的建筑或事件 `{{id}}`；不许编造不存在的地点。
- `linked`：关联的建筑/事件 id 数组；建议 `check.py` 校验引用存在。

## 生命周期

1. **析出**：每十年 heartbeat 从本十年事件与建筑里析出 3–5 人，优先与重大事件（灾难、奇观、大型工程）相关的人。
2. **变老**：每十年年龄 +10。
3. **死亡**：按年龄与事件判定（高龄自然死亡；灾难十年按事件波及范围判定）。
4. **淡出**：连续两个十年无人提起、且未被编年史引用 → `status: faded`（保留记录，不删除）。
5. **永存**：被编年史（中/英）引用过的人物永不删除、永不淡出。

## 示例

**佩得罗斯**，58 岁，石匠（AF 20 年析出）：
色雷斯山里来的石匠，跟着水渠进的城。在 `{{aqb_valley}}` 那段 560 米的谷地拱廊干了六年，专管拱顶合龙——第 14 年一次坭方压断了他左手两根手指，皇帝的工程师赔了三个月工钱。现在住第四山丘脚下的棚屋，手指使不上劲，只能带学徒。小儿子在 `{{nymphaeum_great}}` 当守水人，是他托工头求来的差事。他常说：这水渠里有一段拱，是他儿子将来要守的水流过的。
