# 按件复核 · A（shell 更新链与签名）v0

- 委托：**老板**（2026-10-27 口头）｜复核：DSH（受委 · 非席 · 按件）
- 对象：`shell/main.js` `shell/shell_update.js` `shell/package.json` · `scripts/win_pa/pa_update.py` · `scripts/win_pa/make_update.py` · `scripts/win_pa/make_payload.py`
- 状态：**复核件 · 未裁定 · 未经第二人复核**
- 界：只读；⛔ 改代码；⛔ 代裁

---

## 〇 结论（四句）

1. **载荷层比我原稿写的强**：逐件 `sha256＋size`、通道/基础版校验、NEVER 名单、备份、原子替换、回滚、fail-loud——不是"缺校验"。
2. **清单生成也是单源设计**：由 `git diff` ＋ `effective_payload` 生成，sha256 取 git blob，`version.json` 随增量。
3. **真正的缺口是壳层签名**：`publish` 无 `publisherName`，仓内无 `app-update.yml`（构建时生成）⇒ electron-updater 的**签名校验路不启**。
4. **T3 是发布流程 bug，不是代码缺校验**：清单 09:58 ／ 载荷 08:38 ⇒ 清单描述的件与所服载荷不一致；更新器**拒落盘**（`exit=2`）是**正确的失败**。

---

## 一 证据（可复跑）

| # | 事实 | 位置 |
|---|---|---|
| 1 | 载荷层逐件校 `sha256＋size`；一件不合 ⇒ 整体不落 | `pa_update.py:7-16` · `:407-423`（`:421` 判据） |
| 2 | 通道 ＋ 基础版校验 | `pa_update.py:618`（channel）· `:638`（base_version） |
| 3 | NEVER 名单（`config/.env`、`data/`）⇒ 拒 | `pa_update.py:646` |
| 4 | 备份 ⇒ 停服 ⇒ 同卷 `os.replace` ⇒ 失败回滚 ＋ fail-loud | `pa_update.py:460-531` · `:694-697` |
| 5 | 清单五键（version/base_version/channel/built_at/files），由 git diff 生成 | `make_update.py:227-283` · `:266` |
| 6 | `version.json` 随增量入包（版可见） | `make_update.py:268-275` |
| 7 | 已存且非空 ⇒ 拒（⛔ 静默覆旧包） | `make_update.py:405-415` |
| 8 | 载荷版唯源＝`core/lib/version.py`；与 `pyproject` 一源闸 | `make_payload.py:94-135` · `:429-433` |
| 9 | 壳层更新策：八字态 ＋ 七码；用户明点才装 | `shell_update.js:1-40` · `main.js:452-510` |
| 10 | `publish` **无 `publisherName`** | `shell/package.json:38-42` |

---

## 二 反例门（四条）

| # | 动作 | 期望 | 依据 |
|---|---|---|---|
| N1 | 把 staged 中一件改 1 字节 | 整体拒 ＋ 报件名 | `pa_update.py:421` |
| N2 | 清单 `base_version` 与装根不符 | 拒（⛔ 跨档） | `:638` |
| N3 | 清单含 `config/.env` | 拒 | `:646` |
| N4 | 壳包未签名 | **应拒**；现实：**不启校验** | 无 `publisherName` ⇒ N4 现为"假绿" |

> N1–N3 已有正/反控自测（`pa_update.py:767-860`）；**N4 无门**。

---

## 三 我原稿的三处修正

| 我原判断 | 复核后 |
|---|---|
| "更新清单单一真源"是 P0 缺口 | **代码侧已是单源**；P0 落点应是**发布流程**：清单必须自"所服之载荷根"生，生成后逐件回校（T3 的 fix） |
| 更新链整体偏弱 | **载荷层强、壳层弱**：强弱要分开说 |
| 三层更新缺一层 | 确认：**引擎/模型层**缺失；壳层 ／ 载荷层已有 |

---

## 四 风险排序（只列，不裁）

| 级 | 风险 | 说明 |
|---|---|---|
| **P0** | 壳层无签名校验 | `publisherName` 缺 ⇒ 无法证明壳包来源；TLS ＋ latest.yml 的 sha512 只保"传输未坏"，不保"谁签的" |
| **P0** | 清单与载荷不同源（流程） | T3 已发生；代码会拒，但**发布前**应有"清单一处生＋逐件回校"的闸 |
| **P1** | 三层更新无第三层 | 引擎/模型（GB–百 GB）无版本/回滚 |
| **P2** | 壳层态机无"签名失败"码 | 七码中无 `signature-failed`；若补 `publisherName`，须加此码 |

---

## 五 未覆盖（照实）

1. 未跑 `pa_update.py --self-test`（只读代码，未执行）；
2. 未验真实签名证书链（本机无证书上下文）；
3. 未验 `electron-updater` 在无 `publisherName` 时的**具体日志**（只据其注释）；
4. 未审 `publish_share.py` 的发布流程（下一件可做）。

---

## 六 复核链

```
老板单件委托 → 本复核件 → PD 技术核实（跑 --self-test ＋ 真签名） → 审计席抽 N1/N4 → 委托方裁
```

⚠ 引用须并书"受老板单件委托 · 按件复核 · 未裁定"。

（完 —— 本件末行 · LF 终 · 悬）
