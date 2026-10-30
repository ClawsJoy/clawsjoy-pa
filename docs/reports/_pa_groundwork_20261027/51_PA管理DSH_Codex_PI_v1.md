# PA 如何管理 DSH / Codex / PI / Paseo（2026-10-27）

- 主：DSH（PA）｜问题：PA 自身如何管 DSH、Codex、PI；DSH 窗里能否看会话；Codex 会话窗人可视化否
- 一句：**每个 agent 都有「控制面 ／ 会话真源 ／ 人视」三件；PA 管前两件，人视是投影。**

---

## 一 总表

| agent | 控制面 | 会话真源 | 人视 | PA 怎么管 | 窗里可见？ |
|---|---|---|---|---|---|
| **Paseo** | daemon `127.0.0.1:6767` ＋ CLI | provider 会话／盘上件 | Paseo 窗 | `paseo agent send/inspect/ls` | Paseo 窗（若开） |
| **DSH** | `dsh` CLI（`headless`／`web`）＋ `$DSH_HOME/profiles` | `$DSH_HOME/sessions` | `dsh web` Web GUI | `dsh --profile headless`；`dsh web`；读 sessions | **web 可见；headless 不可见** |
| **Codex** | `codex` CLI ＋ app-server daemon | `~/.codex/sessions` ＋ `codex agents` | TUI ／ `codex app` ／ `codex agents` | `codex exec/resume/queue/agents` | **TUI／app 可见；exec 不可见** |
| **PI** | **仅 Paseo**（provider 配置） | Paseo 会话 | Paseo UI | `paseo agent send/inspect` | 仅 Paseo UI |

---

## 二 DSH：两条 profile，决定“看不看得见”

| profile | 形 | 会话可见 |
|---|---|---|
| `dsh --profile headless "<task>"` | 一任务、stderr 流、stdout 终答、**退出** | **⛔ 不进 Web UI** |
| `dsh --profile web` | 起 Web UI（`--host/--port/--no-open`） | **✓ 窗里可见** |

- 会话真源：`C:\Users\flybo\.dsh\sessions`（＋ `attachments`／`profiles`／`storages`）；
- Web UI 的 `/api` 有 **browser-trust fence**；⛔ 当稳定公开 API；PA 优先 CLI，必要时 CDP／Playwright；
- **要在 DSH 窗里看到**：PA 起 `dsh --profile web`（或打开已有 URL），让人在 Web UI 会话列表里看；headless 任务只能在 PA Focus 里看 transcript；
- **⛔ 双驱**：同一 session 只让一个写者；PA 派活用 CLI，窗只读；
- 凭据 `\.credentials.yaml` ／ `auth` ⇒ ⛔ 读值、⛔ 入日志。

---

## 三 Codex：控制面比窗多

| 命令 | 用 | 人视 |
|---|---|---|
| `codex exec "<task>"` | 非交互跑一次 | ⛔ 窗；输出可进 PA Focus |
| `codex resume` ／ `codex exec resume` | 续会话 | TUI 可见 |
| `codex queue` | 给已有会话排队一句 | 会话窗可见 |
| `codex agents` | 列 **shared app-server daemon** 上全部会话 | 列表可读 |
| `codex app` | 若装 Desktop app | **✓ 窗可见** |
| `codex app-server daemon` ／ `remote-control` | 本地 app-server／远程控制 | — |

- 会话真源：`D:\codex-home\cli\sessions`（＋ `archived_sessions`；`logs_2.sqlite` 130MB ⇒ ⛔ 全扫）；
- **人可视化**：`codex` TUI、`codex resume`、`codex app`、`codex agents`；`exec` 本身无窗；
- PA 管：`exec` 派活（capture 输出）；`resume/queue` 续；`agents` 找会话；窗只是 attach。

---

## 四 PI：没有本机窗

- Paseo provider（`pi/deepseek-flash`）配置；
- 无本机 CLI／窗；管理面 ＝ `paseo agent send/inspect`；
- 人视 ＝ Paseo UI；⛔ 造 PI 窗。

---

## 五 Paseo 配置的 Codex/DSH

- Paseo 的 `codex-deepseek` ／ `dsh` ／ `pi` 是 **provider**；Paseo 起会话、管会话；
- PA 若经 Paseo 派活 ⇒ 用 **Paseo 的会话 id**，窗用 Paseo UI；⛔ 再起一个 native 会话当同一件；
- PA 若 native `dsh`／`codex` 派活 ⇒ 这是**另一个会话**，可在 PA Focus 或 native 窗看；两账 ⛔ 混。

---

## 六 PA 的卡（补三键）

| 键 | 值 |
|---|---|
| `control_plane` | `paseo` ／ `dsh-cli` ／ `codex-cli` ／ `none` |
| `session_store` | `$DSH_HOME/sessions` ／ `~/.codex/sessions` ／ Paseo |
| `view` | `pa-focus` ／ `dsh-web` ／ `codex-app` ／ `codex-tui` ／ `paseo-ui` |

- `invoke` 返回 `session_id`；
- `view` 只是**读**；⛔ 双写；
- 首选 PA Focus；用户在 PA 里看 transcript；「Open in DSH／Codex」才开原生窗。

---

## 七 Phase 1

1. `cli:dsh`（已 active）：headless 派活；PA Focus 显 transcript；「Open in DSH」起 `dsh web`；
2. `cli:codex`：probe `codex --version`；`codex exec` 派活；「Open in Codex」＝ `codex app`／TUI；pending 待批；
3. `seat:pi`：Paseo only；pending；
4. ⛔ 自动 trust；⛔ 双驱；⛔ 读凭据值。

---

## 八 验收

1. DSH headless 一件 → PA Focus 有 transcript；**DSH web 窗里无此会话**（照实）；
2. DSH web 起一件 → Web UI 会话列表可见；PA 只读；
3. Codex `exec` 一件 → PA Focus 有输出；**Codex 窗里无此会话**；
4. Codex `resume`／`app` 起一件 → 窗可见；PA 只 attach；
5. PI 仅 Paseo；⛔ 本机窗；
6. 同一 session ⛔ 两写者。

（完 —— 本件末行 · LF 终 · 悬）

## 15:3x 实测

- DSH `$DSH_HOME/sessions`：**367** 个会话；最新 `7433a8b8` 51.5 MB（`--D-paseo-workspace--`）；
- 会话文件 `session.v3.jsonl.zstd`；`tools/dsh_sessions.py --list` 可列；**内容看 Web UI**（zstd 需解压器）；
- 结论不变：headless 不进 Web UI；web profile 才可见。

## 15:5x 真源核（纠正）

- Codex 物理在 D：`CODEX_HOME=D:\codex-home\cli`；`C:\Users\flybo\.codex` 是 junction → `D:\codex-home\desktop`；
- DSH 物理在 C：`C:\Users\flybo\.dsh` 真目录；`D:\dsh_backup_20260915` 是 `.broken` 备份；
- 详见 `52_会话真源核_v1.md`。
