# -*- coding: utf-8 -*-
u"""PA 种子之**遗产** —— ⛔ 再灌注；唯存「指纹」＋「清」之器（承 pm_1770 §二.1⒝⒞ · TD f202f89）。

昔（2026-09-10 v0）：首启把「已沉淀条目」灌入画像 ／ 账本（`PaCore._ensure_seed`）。
今 ⇒ **废**（⛔ 再灌）。三条由：
  ⒜ 其为**本席之私记**（甬创 ／ OPC ／ WPS-AI ／ 本机之目录之属）⇒ 入用户之机
     ＝ **以我方之记充机主之实**（与「⛔ 造假」同族）；
  ⒝ 「空库之诚」：净机之面本应「空 ⇒ 拒答（**设计**）」⇒ 种子使其「答非其有」；
  ⒞ 老板之裁（承 pm_1767 §三.2「须并之三件」之首）。

⚠ **本模块 ⛔ 含「灌注」**（昔之 `SEED` ⇒ 拔）。唯存二事（**一处定形**）：
  · `LEGACY_SEED` ／ `LEGACY_LEDGER` —— **旧种子之逐字指纹**（**唯**作「已落种子」之清的尺 ·
    ⛔ 更 · ⛔ 复用 · ⛔ 再灌）；
  · `purge()` —— **一次性之清**（**逐字比** ⇒ ⛔ 以 `source` 前缀扫 —— 那会误删真条）
    ＋ **删前留痕** ＋ **幂等**。

⚠ 其退场（**候** · ⛔ 今删）：凡「已落种子」之机须先过一遍此清 ⇒ 之后本模块可尽删。
   （今留之由：老板之机（≥ `9.0.4`）已有其记 ⇒ **无此尺则清无可依**。）
"""

import sys

#: 旧种子之**逐字指纹**（12 条 · 承 pm_1770 §二.1⒝「`seed.py` 之 12」）—— **⛔ 更 ／ ⛔ 复用**。
#: 比之序 ≡ 写入时之实参（`ProfileStore.add(domain, value, source=…, confidence=…, status=…)`）
#: ⚠ **⛔ 比 `date` ／ `id`** —— 那二者随「何日首启」而异 ⇒ 比之则永不中（清恒空转）。
LEGACY_SEED = (
    ('lesson', 'PPT 形状模板自动映射(v1)被否; 正确=模板优先/人确认 或 freeform HTML 设计', '2026-09-10 老板反馈', 'high', 'confirmed'),
    ('lesson', '视觉品质靠模板库/色板系统(布局/字体/配色/背景), 不靠 agent 手拼', '2026-09-10 老板反馈', 'high', 'confirmed'),
    ('aesthetic', '候选主题: A Electric Studio(蓝橙) / B Swiss Modern(黑白瑞士红) / C Blue Professional / D Dark Botanical; 待老板圈定', '2026-09-10 初筛', 'medium', 'proposed'),
    ('aesthetic', '禁忌待老板给(示例: 禁紫色渐变/禁 emoji 满屏/要留白)', '2026-09-10', 'low', 'proposed'),
    ('style', '问题分析: 根因优先, 拒绝打补丁', '多轮协作明示', 'high', 'confirmed'),
    ('style', '方案偏好: 确定性优先(状态机/纯函数/守卫), 模糊留给必要处', 'F0 内核/熔断等', 'high', 'confirmed'),
    ('style', '诚实底线: 编造数字/假成功不可接受; 未查到/待线下核实 是合法输出', 'PPT 数字审核', 'high', 'confirmed'),
    ('style', '沟通: 结论先行 + 可选项 + 默认项; 少开放式问卷', '本会话模式', 'medium', 'proposed'),
    ('decision', 'principal = ClawsJoy 运营者本人(先用产品喂自己); 光电老板类客户为后续形态', '2026-09-10 就职约定', 'high', 'confirmed'),
    ('decision', 'V9=PA(7x24 陪伴/商量/积累/分派/代理审核); 执行 agent 非常态', '2026-09-10 方向', 'high', 'confirmed'),
    ('product', '架构方向: V9 内分层长出 PA 首层(core/pa), 执行内核完善为被调度服务; 不 fork V10', '2026-09-10 架构讨论', 'medium', 'proposed'),
    ('channel', '7x24 入口候选: WPS 协作@ 派工(与 WPS-AI 桥同链路); GUI 当前可用', 'WPS-AI 调研', 'low', 'proposed'),
)

#: 旧账本种子之**逐字指纹**（3 条 · 承 pm_1770 §二.1⒝「`pa_core.py:35-42` 之三条」）
#: 比之序 ≡ `(title, kind, note)`（⚠ **⛔ 比 `id` ／ `created` ／ `status`** —— 同上之由）。
LEGACY_LEDGER = (
    ('口径卡汇总: 甬创/OPC 待核实清单 #1-#10 逐项状态', 'verify', 'vault 收件箱 OPC 调研/PPT 文案'),
    ('WPS-AI v1.4.7 插件内关闭自动更新(updater 拉作者 OSS)', 'todo', ''),
    ('M3: A/B 双主题 3 页样张 -> 视觉确认 -> 审美沉淀', 'todo', ''),
)

_SEED_SET = frozenset(LEGACY_SEED)
_LEDGER_SET = frozenset(LEGACY_LEDGER)


def _is_seed_entry(e):
    u"""某画像条目 ⇒ 是否**逐字**为旧种子（唯 5 元组**全同** · 承「逐字比」）。"""
    return (e.get("domain"), e.get("value"), e.get("source"),
            e.get("confidence"), e.get("status")) in _SEED_SET


def _is_seed_item(it):
    u"""某账本条目 ⇒ 是否**逐字**为旧种子（唯 `(title, kind, note)` **全同**）。"""
    return (it.get("title"), it.get("kind"), it.get("note", "")) in _LEDGER_SET


def purge(profile, ledger, events=None, note=u"去种子（承 pm_1770 §二.1⒝⒞）"):
    u"""清「已落之种子」（**一次性** · 逐字比 · 删前留痕 · 幂等）⇒ 返 `(n_prof, n_ledg)`。

    契约（承 pm_1770 §二.1⒞ 三条）：
      ⒜ **逐字比**：唯「五元组 ／ 三元组**全同**」者删 ⇒ ⛔ 以 `source` 前缀扫
         （`"2026-09-10 老板反馈"` 那一类 —— 老板自己亦可有同源之**真条** ⇒ 扫则误删）；
      ⒝ **删前留痕**：所删之**原值** ⇒ 入 `events`（`kind="legacy_seed_purged"`）∧ 以 stderr 报数；
      ⒞ **幂等**：无中 ⇒ **⛔ 写盘**（⛔ 刷新 `updated` ／ ⛔ 造空事件）⇒ 再跑无果。

    ⚠ 本器**唯清** —— ⛔ 灌（承 pm_1770 §二.1⒝：昔之灌注 ⇒ 拔）。
    """
    hit_p = [e for e in profile.entries if _is_seed_entry(e)]
    hit_l = [it for it in ledger.items if _is_seed_item(it)]
    if not (hit_p or hit_l):
        return 0, 0
    if events is not None:                                  # ⒝ 删前留痕（⛔ 阻清）
        try:
            events.append(u"fact", u"legacy_seed_purged",
                          {u"profile": [dict(e) for e in hit_p],
                           u"ledger": [dict(it) for it in hit_l],
                           u"why": note},
                          source=u"core.pa.seed.purge")
        except Exception as _e:                             # noqa: BLE001 — 留痕败 ⛔ 阻清
            sys.stderr.write("[seed] 留痕 ⛔ 成：%s\n" % str(_e)[:200])
    if hit_p:
        profile.entries = [e for e in profile.entries if not _is_seed_entry(e)]
        profile.save()
    if hit_l:
        ledger.items = [it for it in ledger.items if not _is_seed_item(it)]
        ledger.save()
    return len(hit_p), len(hit_l)
