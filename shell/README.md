# shell/ —— ClawsJoy PA 桌面壳（Electron）

承 **pm_1672 §五.1**（① 载荷入包 ⇒ ② 首启起服 ⇒ ③ `version.json` 之接 ⇒ ④ 单实例 ＋ 窗态记忆
⇒ ⑤ `shell.openPath` 开落点目录 ⇒ ⑥ 出包）＋ **§五.2**（双层更新之交界）。

## 一层一物（**一处定形** · ⛔ 二处各写）

| 物 | 真源 | 由 |
|---|---|---|
| **ROOT** | `process.resourcesPath/payload` | 装根 ＝ **载荷之根**（⛔ 依外之仓根） |
| **版** | 载荷内 `core/lib/version.py:__version__` | ⛔ 取 `package.json` 之版（**二者异层**） |
| **装根 `version.json`** | `installer_post.version_payload`（**建时**由 `make_payload.py` 落） | 与 `version.py` 同源（由「一源之闸」＋既有齿锁）；壳首启唯核（⛔ 自造） |
| **端口** | `scripts/win_pa/port_lite.py`（**薄径**读 `config/system/system_unified.yaml`） | ⛔ 字面 |
| **落点目录** | `core/lib/feedback_target.py:feedback_dir` 之**同序** | env `PA_FEEDBACK_DIR` ⇒ `config/feedback_target.yaml:dir` ⇒ `data/pa/feedback` |
| **机器面之日志** | `%LOCALAPPDATA%\ClawsJoyPA\shell\shell.log` | 技术因入库（⛔ 上面 —— 承「用户面唯人话 ＋ 去处」） |
| **窗态** | `%LOCALAPPDATA%\ClawsJoyPA\shell\window.json` | 与装根无关（载荷层之更新 ⛔ 洗之） |

## 桥（页内侧之约 · 承 pm_1657 §二.2 ／ CW `web/pa/faces/feedback.js`）

`preload.js` 出 **`window.paShell.openFeedbackDir()`**：**参 ＝ 无**（径由壳自算 ⇒ 桥 ⛔ 触他径）；
返 `Promise<{ok:true,path}>` ∨ `{ok:false,code,message}`；失败之面 ⛔ 静默（面必明书因 ＋ 去处）。

## 双层更新之交界（⛔ 相撞）

* **壳层** ＝ `electron-updater`（`publish` 之 `provider: generic` ／ `url` ／ `channel: internal`）——
  整包级（含 `resources/payload` 之一份新载荷）⇒ **壳层之版 ≥ 其载荷之版** 方合（⛔ 反向下洗）。
* **载荷层** ＝ `scripts/win_pa/pa_update.py`（增量 · ≈ 百 KB 量级）⇒ 唯动 `ROOT` 下之件。
* ⚠ 壳层之更新**必**把 `resources/payload` 之件换回壳内之版 ⇒ 载荷层之增量**须以「壳内载荷之版」为基**。

## 步

```bat
python -X utf8 -B scripts\win_pa\make_payload.py --ref a121e90 --out dist\pa_shell\payload --go --gate
cd shell
npm install                     :: 首次（或自既有 node_modules 复制）
npx electron-builder --win --x64 --dir      :: 解包之形（快 · 证「载荷入包」）
npx electron-builder --win nsis --x64       :: 安装器（NSIS · 每用户）
```

出包须设镜像（本机一手）：`ELECTRON_MIRROR` ＋ `ELECTRON_BUILDER_BINARIES_MIRROR`（皆 npmmirror）。

## 自测

```bat
set CLAWSJOY_ROOT=<载荷之径>
set CLAWSJOY_SHELL_SELFTEST=1
node_modules\electron\dist\electron.exe .
:: 出 SHELL_RESULT {...}（root ／ port ／ 落点之一致 ／ 首启 ／ 版之一致 ／ 起服 ／ 页载 ／ 开目录 ／ 停服 ／ 重启）
```
⚠ 自测**必**以「改过端口之载荷副本」为根（⛔ 撞活端 `5102`）。