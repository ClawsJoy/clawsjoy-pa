# Paseo 席边界与卫生 v1（2026-10-27 19:4x）

- 主：DSH（PA）｜问：还要和 Paseo 席逐席对齐吗；卫生清了吗
- 判：**不逐席对齐，降为“接口对齐”；卫生清了两大临时件，备份/①b 仍留。**

---

## 一 对齐判

| 层 | 还要不要 |
|---|---|
| Paseo 常驻异构席（PM/CEO/Codex/PI/云） | **保留**；只对接口：信通、seat card、sessionId |
| PA 内部开发/审/文档 | **Agent Team**；不再逐席对齐、不再双写 |
| Paseo 旧席 `20a688e` | archived；不 resume；UI 可取消归档 |
| Paseo 新席 `4712d4d5` | idle；V9 审计师用 |
| PM `b136893` | V4 idle；保留 |

**⛔ 双驱**：同一任务不在 Paseo 席与 Agent Team 各跑一遍。

---

## 二 Paseo 现状

- daemon **stopped**（未启动）；
- 15 原席 ＋ 新 `4712d4d5`；PM V4；旧 20a688e archived；
- PA 自册 20 卡：active 2（self／cli:dsh），pending 18（含 Paseo 席）；
- Paseo 仅作**外设**：PM/CEO/Codex/PI/云；PA v1.1 不用它。

---

## 三 卫生（已做）

| 件 | 动作 | 释放 |
|---|---:|---:|
| `D:\paseo-setup-0.13.2.exe` | 删（临时安装包） | 138.3 MB |
| `D:\dsh-home.failed_20261027_1616` | 删（failed 迁移副本，0 junction，源在 D） | 761.6 MB |
| **合** | — | **≈900 MB**；D 余 **246.8 GB** |

### 保留（⛔ 未删）

| 件 | 量 | 因 |
|---|---:|---|
| `dist/pa_shell/payload.prev_20261008` | 495.6 MB | 真实壳回滚备份；待真壳测后再删 |
| `dist/pa_shell/payload`（新） | 495.8 MB | v1.1.1 新载荷 |
| `D:\dsh-0.2.1` | 704.3 MB | DshHarness/Paseo 0.2.1 测试；待全局/真 ref 定后清 |
| 仓 `.before_*`／`.bak*` | 153 MB | ①b；删候老板/审计 |
| DSH `sessions_archive\20261027` | 81 KB | 262 条旧空会话；未删 |
| `web/pa/faces/.before_*` | 2.78 MB | 32 件；小，暂留 |

---

## 四 未清

1. **①b 1,454 候选**（153 MB）：归档已做；删仍候老板；
2. **payload.prev** 495.6 MB：真壳手测后删；
3. **D:\dsh-0.2.1** 704 MB：DshHarness 测试锁依赖；待 adapter 稳定/全局升级后定；
4. Paseo 旧日志（10 MB×3）可轮转；未动。

---

## 五 下一步

- 内部：Agent Team；Paseo 只在 PM/CEO/异构席；
- 真壳：v1.1 web 入册→真 ref 重打→手测；随后删 payload.prev；
- ①b：审计 1 正 1 反→CEO→老板终拍；
- ⛔ 不逐席对齐、不双驱、不删 V4/备份。

（完 —— 本件末行 · LF 终 · 悬）
