# 真账／真 ref／真壳 v1（2026-10-27 19:5x）

- 主：DSH（PA · Lead）｜命题：不停在“内存账＋悬空 commit”
- 判：**真账落 1 行；真 ref 可达；真壳热键实测 56ms/520×84；主页面因活端 root 不同未载。**

---

## 一 真账

- 路径：`data/v9/pa/harness_runs.jsonl`（371 B / 1 行）
- run：`pa-run-93505d1d9d02`；harness=`dsh`；status=`ok`；rc=0；stdout=`PA-H2B-OK`
- receipt_sha16：**`89a8250da5b9d799`**；cost 0；session `dsh-headless-…`（PA 代 id）
- 这是 **真 DSH headless 跑 + FileRunLedger 落盘**，非 mock；行内无 v3/v4 私有格式。

---

## 二 真 ref

- branch **`pa-v1.1`** ＝ **`873a72d21f9b5c543e6f8714eacda75abfdb2f78`**；parent HEAD 8e23b02；
- 未 checkout／未 push／未改工作树；`git merge-base --is-ancestor` rc0；
- payload 新：10,772 件／495.85 MB；`version.json.commit` ＝ **873a72d…**（equal=True，可达真 ref）；
- 旧载荷两份保留：`payload.prev_20261008` ／ `payload.prev_20261027_1946`；
- `make_payload --out payload --check` ⇒ **判：合**。

---

## 三 真壳

- 真 Electron 启动（`PACKAGED=false · ROOT=D:\clawsjoy_v9\dist\pa_shell\payload`）；
- 热键注册成功：`CommandOrControl+Shift+Space`；Summon 浮窗 **520×84 frame:false** 就绪；
- **真按热键**（keybd_event）日志：
  `召出：hotkey ⇒ 热键→显 56 ms ／ 页内 43.7 ms ／ 外框 520x84 ／ 内容 520x84 ／ 盒 520x84 ／ 焦点 paSummonIn`
- 测试后已停 Electron；5102 活端未停；未影响当前 PA。

### 真壳之界

- 主页面**未载**：活端 5102 之 root ＝ `D:\clawsjoy_v9\version.json`，壳之 payload root ＝ `D:\clawsjoy_v9\dist\pa_shell\payload\version.json` ⇒ identity `foreign-root`；
- 这不是热键/Summon 缺陷；是**开发态壳 payload 与活端 root 不同**。全页真壳测须停 5102 让壳起 payload 网关，或改端口副本；
- 未停活端，避免打断当前 PA。

---

## 四 未完

1. **全页真壳**：需停 5102／同 root；下一步；
2. **①b** 1,454 候选：删候老板；
3. `payload.prev` 2 份（约 991 MB）：全页壳测后删；
4. H3–H5：移 Paseo/Obsidian、v3/v4 回归、全包依赖扫描。

---

## 五 结论

**真账、真 ref 已落地；真壳热键/520×84 已实测；全页真壳卡在活端 root 不同，非代码缺陷。**
下一步：停 5102 做一次全页真壳 → 恢复 → PA 主迭代。

（完 —— 本件末行 · LF 终 · 悬）

---

## 六 全页真壳（20:1x 补测 · 停服维护窗）

- 停 5102 repo 网关于 19:5x；壳起 **payload 网关**（`pid 28028`），首启约 2–3 分钟；
- identity **ok**（got=want=`dist\pa_shell\payload\version.json`）；
- 壳日志 `页已载：http://127.0.0.1:5102/web/pa.html`；`/web/pa.html` **200 / 62,254 B**；
- 真按热键：`召出：hotkey ⇒ 56ms（页内 43.4ms）／外框 520x84／内容 520x84／盒 520x84／焦点 paSummonIn`；
- 全页载入后 `/v9/pa/registry` 初为 **0/0/0**（payload 无 `data/tmp/pa_registry_pilot_v2.json`）；复制 pilot 到 `payload/data/tmp/` 后 → **20/2/18**；
- **载荷缺口**：pilot 册未入载荷；真装包须 seed（或 `PA_REGISTRY_PILOT` 指真源），否则 Agents 面 0 卡；
- 测毕停壳、停 payload 网关；repo 网关已恢复，**5102 200 / counts 20/2/18**。
