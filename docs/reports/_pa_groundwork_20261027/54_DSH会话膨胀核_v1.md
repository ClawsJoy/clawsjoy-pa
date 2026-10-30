# DSH 会话膨胀核 v1（2026-10-27 16:5x）

- 主：DSH（PA）｜问题：3080／GUI／这么多会话线程，是否 Paseo CLI 连 DSH 的产物
- 判：**主因是 Paseo 的 dsh provider 每次启动/发送新建 DSH 会话；3080／GUI 只是第二实例与显示面，不是根因。**

---

## 一 读数（D:\dsh-home\sessions）

| 组（cwd） | 会话目录 | 字节 |
|---|---:|---:|
| `D:\paseo-workspace` | **169** | 80,985,085 |
| `C:\Users\flybo` | 65 | 19,949 |
| `内容工坊` | 52 | 17,787 |
| `写小说专栏` | 49 | 16,943 |
| `D:\clawsjoy_v9` | 48 | 38,481,292 |
| **合** | **383 目录 / 368 个 v3** | — |

**体量分布**：

| 大小 | 数 |
|---|---:|
| `< 1 KB` | **277** |
| 1 KB–1 MB | 88 |
| `> 1 MB` | **3**（含 51.5 MB 一条） |

⇒ **277 个是空/一次性会话**；真正长会话只有 3 条。

---

## 二 因

1. **Paseo `dsh` provider**：15 席里 `dsh` 提供方每次 `agent send` 起 DSH CLI；DSH 每次启动建一个 session。
   - Paseo 现 cwd：`paseo-workspace` 4 席／`内容工坊` 4／`写小说专栏` 4／`clawsjoy_v9` 3；
   - 这 4 组共 **318 目录**，占 383 的 **83%** ⇒ 主因成立。
2. **`C:\Users\flybo` 65 个**：不是现 Paseo 席 cwd；是**默认/其他 DSH 启动**（桌面 app、headless、脚本）留下的；
3. **3080**：老板手动起的**第二个 `dsh web`**，不是根因；已关；
4. **GUI**：只**显示**会话列表，不生成 368 条；
5. **8 个 `DeepSeek Harness.exe`** 是桌面 app 的进程组，不是 368 个线程。

---

## 三 判

- **368 条 session ≠ 368 个活线程**；活进程只有桌面 app 一组；
- Paseo 的 DSH provider **没有会话复用**，每次 send 新建 ⇒ 空会话堆积；
- 3080/GUI 只是“看得见”的地方，不是“生出来”的地方；
- `C:\Users\flybo` 组说明**非 Paseo** 的 DSH 启动也在加；⛔ 全算 Paseo。

---

## 四 清（建议，⛔ 现在删）

1. **归档**：`<1KB` 且 >7 天 ⇒ `D:\dsh-home\sessions_archive\<date>\`，附 manifest；
2. 保留 3 条 `>1MB` ＋ 88 条 1KB–1MB；逐条看；
3. Paseo：给 `dsh` provider 配**持久会话/复用**（若 provider 支持）；否则定期 GC；
4. **一个 DSH 宿主**：桌面 app 65196 或 `dsh web`，⛔ 同时两个；
5. PA 卡加 `session_policy`：Paseo/headless=`ephemeral`；web/desktop=`persistent`；
6. ⛔ 删 `D:\npm-global`；⛔ 删大会话。

---

## 五 下一步

- 先出**归档清单**（277 条 <1KB，按组/日期/字节），不删；
- 你批后归档；
- 再让 Paseo provider 侧加会话复用/GC。

（完 —— 本件末行 · LF 终 · 悬）

## 六 不是云端投影（拆包实证）

- 最小会话 `9edf7e32`（`C:\Users\flybo`）压缩 **297 B** → 解压 **163 B**，全文只有：
  `{"type":"session","version":3,"id":...,"createdAt":...,"cwd":"C:\\Users\\flybo","isSeeded":false,"delegationDepth":0}`
- 另一条 `1f522230`（`D:\paseo-workspace`）298 B → 166 B，同形；
- **无** `cloud`／`remote`／`sync`／账号字段；**无消息**；`isSeeded:false`、`delegationDepth:0`；
- 会话文件全在本地 `D:\dsh-home\sessions\<cwd>\<id>\session.v3.jsonl.zstd`；
- `profiles` 配置里 grep `cloud|remote|sync|paseo` 无命中；
- ⇒ **不是“DSH 云端投影回 UI”**；是**本机 DSH 启动写的空壳 session**，GUI 读本地 store。
- 云端只参与模型推理；⛔ 写这些本地 session 文件。
