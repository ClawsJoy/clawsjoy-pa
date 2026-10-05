# -*- coding: utf-8 -*-
"""P7 · 口径卡生命周期与留痕 —— 判据化测试（CW · 2026-09-29）

四条边界（PM 裁决①）:
  1. 只此一个文件（⛔ 未顺手改别的）
  2. C18: 改一条口径 ⇒ `check()` 的命中集**必须跟着变**；⛔ 不变 ⇒ 判红
  3. 全程临时目录（两处独立 data_dir）· ⛔ 不依赖 live `5102`
  4. 测试自己也有反例: 故意复现第一版 bug（`card = before` 同一副本）
     ⇒ 本文件依赖的两条不变量**必须判红**，否则测试就是装饰层
"""
import json
import os
import sys
import types

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _fresh(monkeypatch, data_dir):
    """把 PA_DATA_DIR 指到临时目录，并清掉缓存的 caliber 模块（store 路径随 env 变）。"""
    monkeypatch.setenv("PA_DATA_DIR", str(data_dir))
    for m in [k for k in list(sys.modules) if k.startswith("core.pa.caliber")]:
        sys.modules.pop(m, None)
    from core.pa import caliber as C
    from core.pa.caliber_store import CaliberStore, CaliberStoreCorrupt, CaliberStoreError

    return C, CaliberStore, CaliberStoreError, CaliberStoreCorrupt


def _pick_pattern_card(cards):
    """挑一张「状态非 confirmed 且 pattern 非空」的卡（`check()` 会命中它）。"""
    for c in cards:
        if c.get("status") != "confirmed" and (c.get("pattern") or "").strip():
            return c
    pytest.fail("种子卡里找不到「非 confirmed 且有 pattern」的卡 ⇒ 本判据的前提被改了")


def _pages_for(card):
    return [{"data": {"body": "本文出现关键词：" + card["pattern"]}}]


# ---------------- 边界 3：隔离 + 真源在场性 ----------------


def test_无store时真源是seed(monkeypatch, tmp_path):
    C, _, _, _ = _fresh(monkeypatch, tmp_path)
    assert C.source() == "seed"
    assert len(C.effective_cards()) > 0
    assert sum(C.counts().values()) == len(C.effective_cards())


def test_有store时真源切到store(monkeypatch, tmp_path):
    C, CaliberStore, _, _ = _fresh(monkeypatch, tmp_path)
    card = _pick_pattern_card(C.effective_cards())
    CaliberStore(str(tmp_path)).apply_change(
        {"id": card["id"], "status": "confirmed", "owner": "PM", "why": "测试"}
    )
    assert (tmp_path / "caliber.json").is_file()
    assert C.source() == "store"


# ---------------- 边界 2：C18 —— 命中集必须跟着变 ----------------


def test_C18_改口径_check命中集必须跟着变(monkeypatch, tmp_path):
    C, CaliberStore, _, _ = _fresh(monkeypatch, tmp_path)
    card = _pick_pattern_card(C.effective_cards())
    pages = _pages_for(card)

    before = C.check(pages)
    assert [h[1] for h in before] == [card["id"]], "改前必须命中该卡（否则本判据无意义）"

    CaliberStore(str(tmp_path)).apply_change(
        {"id": card["id"], "status": "confirmed", "owner": "PM", "why": "原件已复核"}
    )

    after = C.check(pages)
    assert after == [], "把口径改成 confirmed 后仍命中 ⇒ 判红（口径没真生效）"
    assert before != after, "命中集不变 ⇒ 判红（口径改了但拦截行为没跟着变）"


# ---------------- 生命周期 + 留痕 ----------------


def test_变更写回生效且带生命周期字段(monkeypatch, tmp_path):
    C, CaliberStore, _, _ = _fresh(monkeypatch, tmp_path)
    card = _pick_pattern_card(C.effective_cards())
    st = CaliberStore(str(tmp_path))
    r = st.apply_change({"id": card["id"], "status": "confirmed", "owner": "PM", "why": "复核"})

    live = CaliberStore(str(tmp_path)).get(card["id"])  # 重新读盘，不认内存
    assert live["status"] == "confirmed"
    assert live["owner"] == "PM"
    assert live["updated"]
    assert live["change_count"] == 1
    assert r["change"]["prev_status"] == card["status"]
    assert r["change"]["new_status"] == "confirmed"


def test_留痕append_only且首条改前值不被改写(monkeypatch, tmp_path):
    C, CaliberStore, _, _ = _fresh(monkeypatch, tmp_path)
    card = _pick_pattern_card(C.effective_cards())
    cid, orig = card["id"], card["status"]
    st = CaliberStore(str(tmp_path))
    st.apply_change({"id": cid, "status": "confirmed", "owner": "PM", "why": "一"})
    st.apply_change({"id": cid, "status": "unverified", "owner": "DSH", "why": "二"})

    h = CaliberStore(str(tmp_path)).history(cid)
    assert len(h) == 2, "留痕不是 append-only（条数不对）"
    assert h[0]["prev_status"] == orig, "首条的改前值被后续变更改写了 ⇒ 判红"
    assert h[0]["new_status"] == "confirmed"
    assert h[1]["prev_status"] == "confirmed"
    assert h[1]["new_status"] == "unverified"
    for rec in h:
        assert rec["owner"] and rec["why"], "留痕必须带 owner/why"


@pytest.mark.parametrize(
    "rec,frag",
    [
        ({"status": "confirmed", "owner": "PM", "why": "x"}, "缺 id"),
        ({"id": "#1b", "status": "confirmed", "why": "x"}, "owner"),
        ({"id": "#1b", "status": "confirmed", "owner": "PM"}, "why"),
        ({"id": "#1b", "status": "已核实", "owner": "PM", "why": "x"}, "status"),
        ({"id": "#不是卡#", "status": "confirmed", "owner": "PM", "why": "x"}, "找不到卡片"),
        ({"id": "#1", "op": "add", "status": "confirmed", "owner": "PM", "why": "x"}, "已存在"),
    ],
)
def test_缺字段或非法一律拒且不落盘(monkeypatch, tmp_path, rec, frag):
    C, CaliberStore, Err, _ = _fresh(monkeypatch, tmp_path)
    st = CaliberStore(str(tmp_path))
    with pytest.raises(Err) as ei:
        st.apply_change(rec)
    assert frag in str(ei.value)
    assert not (tmp_path / "caliber.json").exists(), "被拒的变更单⛔ 不得留下 store 文件"
    assert not (tmp_path / "caliber_changes.jsonl").exists(), "被拒的变更单⛔ 不得留下留痕"


def test_store损坏必须抛而不是静默回种子(monkeypatch, tmp_path):
    C, CaliberStore, _, Corrupt = _fresh(monkeypatch, tmp_path)
    st = CaliberStore(str(tmp_path))
    (tmp_path / "caliber.json").write_text("{ 不是 json", encoding="utf-8")
    with pytest.raises(Corrupt):
        st.cards()


# ---------------- 边界 4：测试自己的反例 ----------------


def _buggy_store_module():
    """把线上源码退回第一版写法：`card = cards[idx]` → `card = before`（同一个 dict 副本）。

    第一版症状：① 改的是副本、**列表元素没被改** ⇒ 写回旧值
                ② 「改前值」与卡片是同一对象 ⇒ 被自己覆盖 ⇒ **记不到改前**
    """
    src_path = os.path.join(ROOT, "core", "pa", "caliber_store.py")
    src = open(src_path, encoding="utf-8").read()
    anchor = "            card = cards[idx]"
    assert anchor in src, "锚点失效：caliber_store.py 结构已变，本反例需同步（⛔ 别让它静默通过）"
    buggy = src.replace(anchor, "            card = before")
    assert buggy != src
    mod = types.ModuleType("cw_buggy_caliber_store")
    mod.__file__ = "cw_buggy_caliber_store.py"
    exec(compile(buggy, "cw_buggy_caliber_store.py", "exec"), mod.__dict__)
    return mod


def test_反例自证_第一版缺陷必须被本文件判红(monkeypatch, tmp_path):
    """若本文件的断言**抓不到**这个缺陷，那它只是装饰层。"""
    C, CaliberStore, _, _ = _fresh(monkeypatch, tmp_path)
    card = _pick_pattern_card(C.effective_cards())
    cid, orig = card["id"], card["status"]

    # --- 对照：正确实现满足两条不变量 ---
    good = CaliberStore(str(tmp_path / "good")).apply_change(
        {"id": cid, "status": "confirmed", "owner": "PM", "why": "x"}
    )
    assert good["change"]["prev_status"] == orig != good["change"]["new_status"]
    assert CaliberStore(str(tmp_path / "good")).get(cid)["status"] == "confirmed"

    # --- 反例：第一版实现**违反**同样两条不变量 ⇒ 断言必须能判红 ---
    B = _buggy_store_module()
    bad_dir = tmp_path / "bug"
    bst = B.CaliberStore(str(bad_dir))
    bad = bst.apply_change({"id": cid, "status": "confirmed", "owner": "PM", "why": "x"})

    assert bad["change"]["prev_status"] == bad["change"]["new_status"] == "confirmed", \
        "第一版应把「改前值」覆盖成新值（症状①）"
    assert bst.get(cid)["status"] == orig, "第一版应写回旧值（症状②）"

    inv1 = (bad["change"]["prev_status"] != bad["change"]["new_status"])
    inv2 = (bst.get(cid)["status"] == "confirmed")
    assert not inv1 and not inv2, "反例未被判红 ⇒ 本文件的判据没有分辨力（装饰层）"
    assert (good["change"]["prev_status"] != good["change"]["new_status"]) and \
           (CaliberStore(str(tmp_path / "good")).get(cid)["status"] == "confirmed")

# ---------------- P8：可改字段集 与 留痕字段集 必须对齐 ----------------


def test_P8_每个被改字段都必须有prev_(monkeypatch, tmp_path):
    """对本次请求里出现的**每个**可改字段，留痕必须存在 `prev_<字段>`。"""
    C, CaliberStore, _, _ = _fresh(monkeypatch, tmp_path)
    from core.pa import caliber_store as S

    card = _pick_pattern_card(C.effective_cards())
    cid = card["id"]
    base = {"id": cid, "status": card["status"], "owner": "PM", "why": "P8 逐字段"}
    cases = [
        ("status", {"status": "confirmed"}),
        ("owner", {"owner": "DSH"}),
        ("note", {"note": "P8 新注"}),
        ("pattern", {"pattern": "P8新正则"}),
        ("topic", {"topic": "P8 新题"}),
        ("supersedes", {"supersedes": "#0"}),
    ]
    for field, extra in cases:
        rec = dict(base)
        rec.update(extra)
        CaliberStore(str(tmp_path)).apply_change(rec)
        entry = CaliberStore(str(tmp_path)).history(cid)[-1]
        assert ("prev_" + field) in entry, "留痕缺 prev_%s（P8 判据）" % field
        assert ("new_" + field) in entry, "留痕缺 new_%s（P8 判据）" % field
        assert S.audit_prev_coverage(rec, entry) == [], "audit 未过: %s" % field
        assert set(S.MUTABLE_FIELDS) <= set(S.MUTABLE_FIELDS)


def test_P8_一次请求改多字段则每字段都要有prev_(monkeypatch, tmp_path):
    C, CaliberStore, _, _ = _fresh(monkeypatch, tmp_path)
    from core.pa import caliber_store as S

    card = _pick_pattern_card(C.effective_cards())
    rec = {"id": card["id"], "status": "confirmed", "owner": "DSH",
           "note": "多字段", "topic": "多字段题", "why": "P8 多字段"}
    CaliberStore(str(tmp_path)).apply_change(rec)
    entry = CaliberStore(str(tmp_path)).history(card["id"])[-1]
    assert S.audit_prev_coverage(rec, entry) == []
    for f in ("status", "owner", "note", "topic"):
        assert ("prev_" + f) in entry and ("new_" + f) in entry, "缺 %s 的 prev_/new_" % f


def test_P8_反例自证_旧版留痕必须被判红(tmp_path):
    """复现 PM 04:57 真跑那两行的形态（只有 owner 新值、⛔ 无 prev_owner）⇒ 判据必须判红。"""
    from core.pa import caliber_store as S

    rec = {"id": "#1b", "status": "unverified", "owner": "PM", "why": "x"}
    v1_entry = {
        "ts": "2026-09-29 04:57:06", "id": "#1b", "op": "update", "owner": "PM", "why": "x",
        "prev_status": "unverified", "new_status": "unverified",
        "prev_note": None, "new_note": None, "prev_pattern": None, "new_pattern": None,
    }
    assert "prev_owner" not in v1_entry
    missing = S.audit_prev_coverage(rec, v1_entry)
    assert missing == ["owner"], "旧版留痕（无 prev_owner）必须被判红，实得 %r" % missing

    # 对照：新实现补上该字段
    st = S.CaliberStore(str(tmp_path))
    st.apply_change({"id": "#1b", "status": "unverified", "owner": "DSH", "why": "P8"})
    e2 = st.history("#1b")[-1]
    assert "prev_owner" in e2 and e2["prev_owner"] is None and e2["new_owner"] == "DSH"
    assert S.audit_prev_coverage(
        {"id": "#1b", "status": "unverified", "owner": "DSH", "why": "P8"}, e2) == []
