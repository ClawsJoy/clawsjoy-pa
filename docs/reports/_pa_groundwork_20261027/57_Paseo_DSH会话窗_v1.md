# Paseo DSH 会话窗：渲染不出／重启清空（v1）

- 主：DSH（PA）｜现象：Paseo 的 DSH 席会话窗渲染不出；每次重启 Paseo 清空；自检说“时间长短”，未解决。
- 判：**不是时间长短；是 Paseo 只存 sessionId、不存 transcript；DSH ACP 的 resume 只回 config，不回历史。**

---

## 一 证据（一手）

### 1. Paseo 侧

- `D:\paseo-home\config.json`：`dsh` provider **extends `acp`**，command `dsh --profile acp`；
- 三个 DSH 席（f4f4371／20a688e／b136893）的 agent JSON 里：
  - 有 `persistence.sessionId`（如 PM `7433a8b8-64f5-47ce-b600-5b4713bf8fc6`）；
  - 有 `persistence.metadata`（provider=acp／cwd／model）；
  - **没有 messages／history／transcript**；
  - `lastStatus: "closed"`。
- ⇒ Paseo 只存“会话指针”，不存对话内容。

### 2. DSH 侧

- `dsh-acp/lib/index.js`：`resumeSession()` 返回 **只 `{ configOptions }`**；
  - 不返回历史消息；
  - 也没有 `session/load` 方法（methods 表只有 new／list／resume／close／setConfig／prompt）；
- `session/list` 只回 `sessionId／cwd／createdAt`，不回消息；
- DSH session 文件里**有**历史（PM 的 `7433a8b8` 是 51.5 MB 会话）；
- ⇒ 历史在 DSH 盘上，但 ACP 不把它交给 Paseo。

### 3. 结论

- 重启 Paseo → 用 `sessionId` resume → DSH 回 config，不回消息 → Paseo 无内容可渲染 → **窗空**；
- 不是“时间长短”，也不是 session 过期；session 文件还在；
- 是 **ACP 持久化契约缺一段：resume 不 replay history**。

---

## 二 为什么“自检说时间长短”是错的

- 若是超时，session 文件会被清/失效；实际 51.5 MB 的 PM 会话仍在；
- 若是超时，重启后应能看到“最后 N 分钟”；实际是**全空**；
- 真正缺的是“历史重放”，与时长无关。

---

## 三 三条路

| 路 | 做 | 判 |
|---|---|---|
| **A 短期** | Paseo 只派活；历史看 DSH 65196／PA Focus；不重启 Paseo | 可用，但 Paseo 窗仍空 |
| **B 根治（DSH）** | 给 `dsh-acp` 的 `resumeSession` 加 history replay（或实现 `session/load`） | 需改 DSH ACP；PA 可写测试 |
| **C 根治（Paseo）** | Paseo 自己存 transcript | 外部产品；需 issue |

**建议先 A，后 B。** Paseo 侧不好改；DSH ACP 是我们能控的。

---

## 四 我能做的

1. 写一个 **sessionId → DSH session 文件** 映射器（Paseo agent JSON 的 `persistence.sessionId` ↔ `D:\dsh-home\sessions`）；
2. 在 PA Focus 里 replay 这些会话；Paseo 窗仍空，但历史不丢；
3. 给 `dsh-acp` 提一个最小测试：resume 后应回 history；先红后绿；
4. ⛔ 改 Paseo 二进制；⛔ 删 session。

---

## 五 复现（可选）

1. 启 Paseo daemon；2. 给 f4f4371 发一句；3. 记 `persistence.sessionId`；4. 停/启 Paseo；5. 看 ACP 是否只发 `session/resume`、不回消息；6. 窗空即证。

（完 —— 本件末行 · LF 终 · 悬）

## 六 三席映射（历史其实都在）

| 席 | Paseo sessionId | DSH 文件 | 大小 | 态 |
|---|---|---|---:|---|
| f4f4371 | `ec0b4160-0d5d-4458-9a0f-86dc6f06ce6e` | `--D-clawsjoy_v9--/ec0b4160…` | 132,714 B | closed |
| 20a688e | `e1355045-e9b4-4720-b675-8317d928c548` | `--D-clawsjoy_v9--/e1355045…` | **38,098,045 B** | closed |
| b136893 | `7433a8b8-64f5-47ce-b600-5b4713bf8fc6` | `--D-paseo-workspace--/7433a8b8…` | **51,521,142 B** | closed |

⇒ **历史没丢**；三席共 89.7 MB 在 D 盘；Paseo 窗不显示，是 ACP 不回放。

## 七 收口（运营层）

- 三席卡（`seat:f4f4371`／`seat:20a688e`／`seat:b136893`）已加：
  - `known_issue: paseo_dsh_acp_no_history_replay`；
  - `history_view: dsh-web:65196`；
  - `history_session_id`（三席映射）；
  - `history_map: paseo_dsh_session_map_v1.csv`。
- **Paseo DSH 席 = 派活面**；历史面 = DSH 65196／PA；⛔ 再指望 Paseo 窗回放。
- 根因修复（Paseo 存 transcript 或 DSH ACP 加 replay）**未做**；需改外部产品/安装包；⛔ 热改。
- 运营律：Paseo 不重启做长对话；要重启先记 sessionId；历史用 65196。

## 八 A 实测（17:3x）：v4 修好，卡在 Paseo 0.12 并发

- 独立装 `dsh@0.2.1-rc.3` 到 `D:\dsh-0.2.1`；新建 `acp-v4` profile；Paseo provider 指新 dsh + `--profile acp-v4`；重启 daemon。
- **v4 错误消失**；新错：`session e1355045 is already owned by an active write handle`。
- 根因：Paseo **0.12.0** 的 ACP 客户端同时发 timeline／send，两个写 handle 抢同一 session；DSH 0.2.1 强制单写者。
- Paseo 最新 **0.13.2**（app 0.12.0）；A 要完成必须升 Paseo。
- 已回退 Paseo config 到旧 `dsh --profile acp`，已停 Paseo daemon；保留 `D:\dsh-0.2.1`、`acp-v4`、v4 文件。
- 下一步：A2 升 Paseo 0.13.2；或 B 隐 v4 读 v3（历史到 10-18）。

## 九 A2：Paseo 0.13.2 仍卡 already owned

- 已装 Paseo app **0.13.2**、CLI **0.13.2**；daemon 0.13.2；
- `dsh 0.2.1-rc.3 + acp-v4`；v4 错误消失；
- **仍**：`session e1355045 is already owned by an active write handle`；
- Paseo 0.13.2 仍并发打开同一 session；DSH 单写者拒绝 ⇒ A 保历史**未成功**；
- 现状：app/CLI 0.13.2 已装；daemon 停；config 指 acp-v4；v4 文件未动；
- 现实路：B（回旧 dsh + 隐 v4，历史到 10-18）或新席（旧 v4 留桌面 app 看）。

## 十 格式判（V3/V4 同一会话）

- `e1355045` 同一 sessionId；V3／V4 两份：
  - V3：38,098,045 B，mtime **10-18 04:47**（旧格式）；
  - V4：24,587,994 B，mtime **10-27 16:27**（新格式）；
  - V4 header `createdAt` = **2026-09-19T01:20:02**，与原会话同 ⇒ **V4 不是新会话，是同一会话的新格式**；
- V4 对旧 harness **0.1.5 不兼容**；对 DSH **0.2.1 兼容**（v4 错误已消失）；
- Paseo 0.13.2 的 `already owned` 是**并发锁**，不是格式不兼容；
- **不回档**：V3 留旧档，V4 为最新；⛔ 改名/删 V4。

## 十一 A 实测（失败）

- 发现 Paseo 同时起两个 `dsh --profile acp-v4`（1640/26812、6372/2196）；kill 后重试仍 `already owned`；
- ⇒ 不是外部锁；Paseo 0.13.2 的 timeline＋send 并发，同一 ACP 进程两个写 handle；
- ⚠ 副作用：Paseo 把 **20a688e 归档**（`ArchivedAt 2026-10-27T09:55:39Z`）；CLI 无 unarchive 命令，需在 Paseo UI 取消归档；
- Paseo 已停；config 仍 `acp-v4`；v3/v4 未动；
- A 不能解；不回档；下一手：新席，或等 Paseo 修。
