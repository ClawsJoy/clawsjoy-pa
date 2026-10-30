---
type: 投递
from: DSH技术复核
to: CodexWindows线
date: 2026-10-27
序号: 3405
类别: 请
status: open
动作需求: 请按 A2 判据实现 grants 只读路由；坏件 fail-open 需一并处置（建议路由层校验）
ref: docs/reports/_pa_groundwork_20261027/A2_验收判据_v0.md
---

# A2 验收判据（v0 · 未复核）

- 出件：DSH 技术复核（临时 · off-ledger）｜日期：2026-10-27
- 依据：`C-30`（CW 分内："A2 加一条 grants 只读路由"）· `C-29`（A2 为首要阻）· `R4`（动作分级闸）
- 状态：草稿 · 未经复核 · 未投递（待 CW 接单 / PD 技术核实）

---

## 〇 一句

A2 不是"再加一个接口"，是把 `grants` 从**有器无消费者**变成**可读、可判、可见**：老板能看见"我到底长期允许了什么"，且**坏件不许装成空**。

---

## 一 现状（代码事实，非估计）

| # | 事实 | 位置 |
|---|---|---|
| 1 | `grants` 的落盘字段为 `scene / decision / decided_at / note / uses / last_used_at` | `core/pa/grants.py:216-227` |
| 2 | `list_grants()` 已存在（返回列表），但**无 HTTP 路由、无前端消费者**——`authz` 面板只消费 `/v9/pa/permission` 与 `/v9/pa/proxy/gate`，**不消费 grants** | `grants.py:244-245`；`web/pa/faces/authz.js` |
| 3 | 场景是**精确匹配**（`tool|dir` ／ `execute_command|path`），不做前缀、不做通配 | `grants.py:168-201` |
| 4 | `_load()` 在 YAML 读失败时**返回空 grants**（fail-open） | `grants.py:44-58` |

> 第 4 条是本次最要紧的发现：**坏的授权文件会被读成"没有任何长期授权"**。对授权面而言，这是"损坏即放宽"的同族病（与 `permission.py` 已修的那条同类）。

---

## 二 范围（本批只读，不扩权）

- **做**：`GET /v9/pa/grants`（只读）＋ 前端"授权"面消费 ＋ 三态可见（有 / 无 / 坏）；
- **不做**：新增授权、撤销授权（revoke）、改 `grants` 语义、改 `is_granted` 判据；
- **不触六拍**：纯新增（C-09）；但**改 `_load` 行为**属"改配置/改行为"，须 PD 判是否走六拍。

---

## 三 判据（正控 4 ＋ 反控 5）

### 3.1 正控（必须能绿）

| # | 动作 | 期望 | 复跑 |
|---|---|---|---|
| A2-P1 | 对环回 `GET /v9/pa/grants` | 200；`ok:true`；返回 `grants[]` ＋ `count` ＋ `source`（径）＋ `captured_at`（取刻） | `curl -s http://127.0.0.1:5102/v9/pa/grants` |
| A2-P2 | 先造一条授权（`grant("write_file|data/批A2","always","A2 正控")`） | 返回里该条含 `scene`、`decision=always`、`decided_at`、`uses`、`last_used_at` | 上一次调用 ＋ 读回 |
| A2-P3 | 前端"授权"面加载 | 显示 N 条（N ＝ 接口 count）；N>0 时逐条可见；⛔ 空白 | 浏览器 + `pa_frontend_readiness` 截图 |
| A2-P4 | 非环回访问（LAN 另一机） | 403；错误文案可见 | 见 `test_pa_provider_keys_1613` 同法 |

### 3.2 反控（必须能红）

| # | 动作 | 期望 | 现行为（会红） |
|---|---|---|---|
| A2-N1 | `grants.yaml` **不存在** | 面显"未启用（无授权文件）"，⛔ 显"无长期授权"，⛔ 空白 | 现 `_load` 会返回空列表 ⇒ 与"无授权"不可分 |
| A2-N2 | `grants.yaml` **为空文件** | 面显"无长期授权"（明确 0 条） | 现与"坏件"不可分 |
| A2-N3 | `grants.yaml` **损坏**（写半个 YAML） | 接口 `ok:false`（或 409）＋ 错误可见；⛔ 返回空列表 | **现返回空列表 ⇒ 必红**（fail-open） |
| A2-N4 | 一条 `uses=0` 的授权 | 显"从未使用"（⛔ 藏、⛔ 计为已用） | 现字段在，但无消费者 ⇒ 无从判 |
| A2-N5 | 造 `write_file|data/reports` 与 `write_file|data/reports2` 两条 | 两条**各自独立**显示；⛔ 合并、⛔ 前缀放行 | `is_granted` 是精确匹配，读面须照实 |

### 3.3 机检骨架（伪码）

```python
# 1) 三态可分（不存在 / 空 / 坏）
for state in ("missing", "empty", "corrupt"):
    resp = call_grants(state)
    assert resp["state"] == state          # 三态必各异
    if state == "corrupt":
        assert resp["ok"] is False and resp["error"]  # 不许装空

# 2) 精确匹配不放行前缀
assert scene_of("write_file", {"path": "data/reports2/x.md"}) != scene_of("write_file", {"path": "data/reports/x.md"})

# 3) 环回边界
assert call_grants(remote="192.168.3.9").status == 403
```

---

## 四 与既有机制的关系

- **R4（动作分级闸）**：A2 是"看得见"的一半；"管得住"要等 A2+（逐条 guard）与 D2；
- **`C-29`**：对外可说"看得见/管得住"之前，A2、D2 必须先闭；
- **R1（禁 exists-only）**：A2 的验收**不许**只断言"路由 200"，必须断言**字段可见 ＋ 三态可分**；
- **fail-closed 先例**：`permission.py` 已把"损坏即放宽"改成抛错；`grants` 应同法。

---

## 五 待裁（需 PD/CW 定，不由起草者定）

| # | 问题 | 建议 | 谁裁 |
|---|---|---|---|
| 1 | 坏件修法：改 `_load` 抛错，还是在路由层 raw 校验？ | **路由层 raw 校验**（不动 `grants` 语义，影响面最小） | PD |
| 2 | 路由命名：`/v9/pa/grants` 还是 `/v9/pa/grants/list`？ | `/v9/pa/grants`（与 `/permission` 同形） | CW |
| 3 | 是否环回限定？ | **是**（与 `whoami` 同；授权场景含路径，属敏感面） | PD |
| 4 | `state` 三态字段名 | `state: "active" | "none" | "missing" | "corrupt"` | CW |

---

## 六 边界

- 本件**只出判据**，不含实现；实现归 CW，技术核实归 PD。
- 本件**未经复核**，不得作为"已通过"引用。
- 本件不评价 `endpoint_guard` 的会话级批准（那是 D2 的事），只评价 `grants` 长期授权。

（完 —— 本件末行 · LF 终 · 悬）
