# 按件复核 · A2（grants 只读面）v0

- 委托：**老板**（2026-10-27 口头）｜复核：DSH（受委 · **非席** · 按件）
- 对象：`core/pa/grants.py`（244 行）· `web/pa/faces/authz.js`（155 行）· `core/pa/gateway_routes.py`（88 路由）· `C-29`／`C-30` · R4（v3）
- 状态：**复核件 · 未裁定 · 未经第二人复核**
- 界：只读；不改代码；不代裁；不投递

---

## 〇 结论（三句）

1. **A2 未实现**：`/v9/pa/grants` 路由 **0 条**；`list_grants()` **无调用点**；`authz` 面板只消费 `/permission` 与 `/proxy/gate`。
2. **`_load()` fail-open**：文件缺 ／ 非 dict ／ 读失败 ⇒ 三条路径都返回**空 grants** ⇒ 坏件被读成"没有任何长期授权"。
3. 所以 A2 的验收**不能**只断言"路由 200"；必须断言**坏件可红**（R1 之族）。

---

## 一 证据（可复跑）

| # | 事实 | 位置 | 复跑 |
|---|---|---|---|
| 1 | 无 `/v9/pa/grants` 路由 | `gateway_routes.py` 全文 | `grep -n "v9/pa/grants" core/pa/gateway_routes.py` ⇒ 0 |
| 2 | `list_grants()` 唯定义、无调用 | `grants.py:244` | `grep -rn "list_grants(" .` ⇒ 1（定义处） |
| 3 | `authz` 面板只消费三端 | `authz.js:12`（gate／approve／perm）· `:80` `:86` `:98` `:142` | 读 `web/pa/faces/authz.js` |
| 4 | `_load()` 三条 fail-open 返回 | `grants.py:41-55`（`:44` 缺件 ／ `:50` 非 dict ／ `:55` 读失败） | 读 `grants.py:41-56` |
| 5 | 场景为**精确匹配**（⛔ 前缀、⛔ 通配） | `grants.py:168-201` | 读 `scene_of`／`is_granted` |
| 6 | 落盘字段 | `scene／decision／decided_at／note／uses／last_used_at` | `grants.py:216-227` |

---

## 二 反例门（三条 · **现行为必红**）

| # | 动作 | 期望 | 现行为 |
|---|---|---|---|
| N1 | 把 `data/v9/pa/grants.yaml` 写成半个 YAML | 接口 `ok:false`（或 409），错误可见 | **返回空列表** ⇒ 红 |
| N2 | 分别造：文件不存在 ／ 空文件 | 两态**可分**（"未启用" vs "无长期授权"） | 两态**不可分** ⇒ 红 |
| N3 | 造 `write_file|data/reports` 与 `write_file|data/reports2` 两条 | 读面**各自独立**显示；⛔ 合并、⛔ 前缀放行 | 无读面 ⇒ 无从判 |

---

## 三 最小实现选项（只列，不代裁）

| 项 | 选项 A（荐） | 选项 B |
|---|---|---|
| 坏件处置 | **路由层 raw 校验**（不动 `grants` 语义） | 改 `_load` 抛错（影响所有调用方） |
| 路由 | `GET /v9/pa/grants`（与 `/permission` 同形） | `/v9/pa/grants/list` |
| 边界 | **唯环回**（与 `whoami` 同） | 全局 JWT 闸即可 |
| 出参 | `{ok, grants[], count, source, state, captured_at}`；`state ∈ active／none／missing／corrupt` | 仅在 `ok:false` 时给 `error` |
| 前端 | `authz` 面加一节"长期授权"（⛔ 新建面） | 另立面 |

---

## 四 与 R4／C-29 的关系（照实）

- **R4（v3）**：只读侧已证、写侧待验；A2 是"**看得见**"的一半，**不构成** R4 写侧证据。
- **C-29**：对外说"看得见／管得住"须 A2、D2 先闭；本件只谈 A2。
- **C-30**：A2 归 **CW `b2a5182`**（修 PA 功能）；本复核**不替代**其实现与 PD 技术核实。

---

## 五 未覆盖（照实）

1. 撤销／新增授权（revoke）——本批只读；
2. `endpoint_guard` 的会话级批准（D2）；
3. 多用户／远端 JWT 的 owner 判据；
4. 浏览器真复检（本次只读代码，未起前端）。

---

## 六 复核链（本件走到哪）

```
老板单件委托 → 本复核件（证据＋反例门） → PD 技术核实（diff／自测门） → 审计席抽 1 正控 ＋ 1 反控 → 委托方裁
```

⚠ 本件**未经第二人复核**；引用时须并书"受老板单件委托 · 按件复核 · 未裁定"。

---

## 七 边界

- 本件**只出证据与判据**，⛔ 裁定、⛔ 改代码、⛔ 改台账、⛔ 自审自判。
- 本件**未投递**；是否转 CW／PD 由老板一句定。

（完 —— 本件末行 · LF 终 · 悬）
