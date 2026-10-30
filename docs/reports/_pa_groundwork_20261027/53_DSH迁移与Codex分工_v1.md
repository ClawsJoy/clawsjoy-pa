# DSH 迁移与 Codex 分工 v1（2026-10-27 16:0x）

- 问题：DSH 搬 D、Codex 两 home 统一/分工，PA 能不能处理
- 答：**DSH 能备好，不能在当前会话按切换；Codex 先做“明确分工”，不做热统一。**

---

## 一 DSH 预检（一手）

| 项 | 值 |
|---|---|
| 源 | `C:\Users\flybo\.dsh` |
| 文件／字节 | **1,496** ／ **367,800,518 B（≈351 MB）** |
| v3 会话 | **367** |
| D 空闲 | **248.7 GB** |
| 目标 `D:\dsh-home` | **不存在** |
| 当前 DSH | **在跑**（Web GUI；我就是它） |

脚本：`tools/dsh_home_migrate.ps1`（默认 DryRun；`-Go` 才写）。

### DryRun 已过

```
SOURCE ... files=1496 bytes=367800518 v3=367
TARGET D:\dsh-home exists=False
D free GB=248.7
processes using source=0   # 启发式，不等于 DSH 已退
```

---

## 二 为什么我不能现在按“切换”

1. **切换要停的就是 DSH 自身**；停了，这个会话/Web GUI 就断；
2. 当前 DSH 正在写 `C:\Users\flybo\.dsh\sessions`（最新 51.5 MB 会话 15:15）；
3. 热搬 = 复制到一半文件还在变；⛔ 不可作真源；
4. 脚本的进程检查是**启发式**（只看命令行含源路径），⛔ 当“已停”之证。

⇒ 正确顺序：**你退出 DSH → 普通 PowerShell 跑 `-Go` → 脚本复制/校验/改名/设 env/junction → 你启动 `dsh --profile web`**。

---

## 三 脚本做什么（-Go）

1. 复查源／目标／空间；
2. `robocopy SOURCE TARGET /MIR /COPYALL`；
3. 校验：文件数 1,496、字节 367,800,518、v3 367；
4. 源改名 `C:\Users\flybo\.dsh.backup_<timestamp>`；
5. 设 **User** `DSH_HOME=D:\dsh-home`；
6. 建 junction `C:\Users\flybo\.dsh` → `D:\dsh-home`（兼容默认路径；可 `-NoJunction`）；
7. 打印启动：`dsh --profile web`。

### 回滚

- 删 junction → 把 backup 改回 `C:\Users\flybo\.dsh` → 清 User `DSH_HOME`；
- 脚本不自动回滚；失败即停，留 backup。

---

## 四 Codex：两 home 先分工

| 面 | home | 会话 |
|---|---|---|
| CLI | `D:\codex-home\cli`（`CODEX_HOME`） | 37 files，最新 15:30 |
| Desktop | `D:\codex-home\desktop`（`C:\Users\flybo\.codex` junction） | 154 files，最新 15:30 |

- **明确分工**：CLI 用 cli；Desktop 用 desktop；PA 两处只读；⛔ 合并；
- **不现在统一**：8 个 `codex` 进程在跑；合并要停 Desktop/app-server、备份 191 files、改 junction/env、跑 doctor；高风险；
- `codex doctor` 已有 **stale C rows ＋ missing D rows**；⛔ 手改 DB；交 Codex 主人评估 `codex migrate-rollouts`。

---

## 五 我能做／不能做

| 事 | 我能 |
|---|---|
| DSH 预检／脚本／回滚／验收 | ✓ 已备 |
| DSH 热切换 | ⛔（停的就是我） |
| Codex 明确分工文档 | ✓ 现在 |
| Codex 热统一 | ⛔（8 进程在跑；需维护窗） |
| 删 sessions／手改 DB | ⛔ 永不 |

（完 —— 本件末行 · LF 终 · 悬）

## 16:0x 现场更正

- 老板从 `C:\Windows\system32` 跑相对路径 ⇒ `-File` 找不到；正确绝对路径：`D:\clawsjoy_v9\tools\dsh_home_migrate.ps1`。
- 关 DSH **窗** ≠ 退 DSH **应用**：实测仍有 **8 个 `DeepSeek Harness.exe`**（PID 21128 主／16780 host／GPU／renderer／utility）；端口 51729 仍在听。
- 脚本已加固：进程检查匹配 `DeepSeek Harness|app.asar|\.dsh`；DryRun 报 `processes using source=8`，`-Go` 会拒。
- 源字节从 367,800,518 → 367,868,432（会话仍在写）⇒ **热搬证据**。
- 正序：托盘 Quit／停 8 进程 → 验 0 进程＋51729 无监听 → 普通 PowerShell 跑绝对路径 `-Go`。

## 16:16 第二次（/COPY:DAT）与 junction 修复

- `/COPYALL` 改 `/COPY:DAT` 后 robocopy rc=1，但校验：源 **1,496／367,921,913**，目标 **52,294／798,552,636** ⇒ 失败。
- 因：`profiles/node_modules` 下 **482 个 junction** 指向 `D:\npm-global\node_modules\@deepseek-ai\dsh\node_modules\*`；robocopy **跟随 junction** 复制了 5 万文件。
- 校验**在改名之前**失败 ⇒ 源未动、env 未改、未切换；目标已改名 `D:\dsh-home.failed_20261027_1616`。
- 脚本 v3：`/XJ /SL` 不跟随 junction，复制后**重建 482 个 junction**；校验 **1,499 files／368,155,739 B／368 v3／482 junctions**。
- 实测小副本：1,499 files／368,126,797 B ＋ 482 junctions；已安全清理，`D:\npm-global` 完好。
- 当前 DSH 8 进程、端口 56225；`-Go` 仍会拦。

## 16:24 成功

- robocopy rc=1；TARGET 1,499／368,170,274；junctions 482/482；
- 源改名 backup；C junction → D；User DSH_HOME=D；
- 新会话已写 `D:\dsh-home\sessions`（16:25）；实际 GUI 65196；3080 为第二实例，老板已主动关闭；
- 失败目标 52,294 files／798 MB／0 junctions，留作证据，可删。
