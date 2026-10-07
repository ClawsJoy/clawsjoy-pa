# -*- coding: utf-8 -*-
"""2026-09-10 PA v1 MVP: 跨会话记忆 / 对话打断 / 分派+审核 / 事件 / vault 桥"""
import sys

sys.path.insert(0, ".")
import pytest

from core.pa.pa_core import PaCore


@pytest.fixture()
def pa(tmp_path):
    return PaCore(data_dir=str(tmp_path / "pa"))


def test_cross_session_memory(pa):
    """验证口径1: PA 记住老板决策口径(跨会话=跨 PaCore 实例)。"""
    r = pa.handle(
        "profile_sediment",
        {"domain": "decision", "value": "老板拍板: 审美默认双主题 A+B 出样张", "source": "2026-09-10", "confidence": "high"},
    )
    assert r["ok"]
    pa2 = PaCore(data_dir=str(pa.dir))  # 模拟新会话重新加载
    assert any(e["value"].startswith("老板拍板") for e in pa2.profile.active("decision"))


def test_dialog_interrupt_keeps_context(pa):
    """验证口径3: 对话随时打断/换话题, 上下文不丢。"""
    pa.handle("dialog_post", {"sid": "s1", "text": "先谈 A 主题封面", "topic": "样张A"})
    r2 = pa.handle("dialog_post", {"sid": "s1", "text": "算了, 改谈数据页排版", "topic": "数据页"})
    assert r2["ok"] and r2["dialog"]["topic"] == "数据页"
    ctx = pa.handle("dialog_context", {"sid": "s1"})
    topics = [m.get("topic") for m in ctx["history"] if m.get("role") == "user"]
    assert "样张A" in topics and "数据页" in topics  # 旧话题仍保留


def test_dispatch_pass_with_stub(pa):
    """验证口径2: PA 分派任务(Stub 执行)并代理审核通过。"""
    r = pa.handle("dispatch", {"task_text": "生成一份测试交付物"})
    assert r["ok"]
    assert r["review"]["verdict"] == "pass"
    assert r["result"]["artifact"]
    # 记录可查
    hist = pa.handle("dispatch_history")
    assert any(row["task_id"] == r["contract"]["task_id"] for row in hist["rows"])


def test_dispatch_reject_when_no_artifact(pa):
    class BadEx:
        def run(self, contract):
            return {"ok": False, "artifact": "", "error": "执行器挂了"}

    r = pa.handle("dispatch", {"task_text": "会失败的任务"})
    # 覆盖 executor: 直接调底层审核
    from core.pa.dispatch import dispatch_and_review, make_contract

    contract = make_contract("会失败的任务")
    row = dispatch_and_review(contract, BadEx().run(contract), profile_brief=pa.profile.brief())
    assert row["verdict"] == "reject" and row["reasons"]


def test_sediment_writes_event(pa):
    pa.handle("profile_sediment", {"domain": "style", "value": "测试事件", "confidence": "medium"})
    ev = pa.handle("events_tail", {"n": 10})["events"]
    assert any(e["domain"] == "style" and e["kind"] == "sediment" for e in ev)


def test_vault_ledger_roundtrip(pa, tmp_path):
    """老板可在 vault 文件勾选 -> parse 回写 ledger。"""
    from core.pa.vault_brain import BrainSync

    vault = tmp_path / "vault"
    pa.ledger.add("M3: A/B 双主题 3 页样张(测)", kind="todo")   # ⭐ 去种子（pm_1770 §二.1⒝）后：本测自带其件
    brain = BrainSync(pa.ledger, vault_dir=str(vault))
    md = brain.sync_ledger()
    # 手工把一条 done
    text = open(md, encoding="utf-8").read()
    text = text.replace("- [ ] M3: A/B 双主题", "- [x] M3: A/B 双主题", 1)
    open(md, "w", encoding="utf-8").write(text)
    n = brain.parse_ledger()
    assert n >= 1
    m3 = next(i for i in pa.ledger.items if "M3" in i["title"])
    assert m3["status"] == "done"


def test_vault_asset_and_standup(pa, tmp_path):
    from core.pa.vault_brain import BrainSync

    vault = tmp_path / "vault"
    brain = BrainSync(pa.ledger, vault_dir=str(vault))
    f = tmp_path / "a.pdf"
    f.write_bytes(b"%PDF-1.4 test")
    r = brain.register_asset(str(f), kind="docs")
    assert r["ok"] and r["link"].startswith("![[") and r["size"] == len(b"%PDF-1.4 test")
    pa.ledger.add("核对样例", kind="verify", due="2000-01-01")
    st = brain.daily_standup()
    assert st["overdue"] >= 1
