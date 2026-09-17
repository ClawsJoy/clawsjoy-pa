# -*- coding: utf-8 -*-
"""合入门槛：已确认的子串误伤判据不得复活（2026-09-13 立）。

依据：跨三个模块三次独立命中 ——
  1. _is_vault_write 把 vault **读**判成写（路径命中 ≠ 写意图）
  2. cu_learning_impl.py "ask" in t 命中 **task**
  3. sandbox_ops.py "test_" in filepath_str 命中 **contest_a.md**
且第 3 条的同一行里本来就有 endswith("_test.py") 的正确写法 —— 说明这是**系统性写法**，不是个人疏忽。
因此：**每条判据必须配防误伤用例，且这些已知坏写法不许复活。**
"""
import sys

sys.path.insert(0, ".")

BANNED = [
    ('"ask" in', "core/tools/cu_learning_impl.py"),
    ('"test_" in filepath_str', "core/gateway/sandbox_ops.py"),
    ('"sop" in _blob', "core/gateway/v9_bridge/tool_runner.py"),
]


def test_FAULT_no_known_substring_false_positives():
    """① 先能失败：三个已确认的子串误伤写法不得复活。"""
    for pat, path in BANNED:
        # 只看**代码行**：注释里引用坏写法是说明，不是复活（第一版漏了这点，被自己的注释误报）
        code = [
            ln
            for ln in open(path, encoding="utf-8").read().split(chr(10))
            if ln.strip() and not ln.strip().startswith("#")
        ]
        hits = [ln.strip()[:70] for ln in code if pat in ln]
        assert not hits, "子串误伤写法复活：%s in %s -> %s" % (pat, path, hits)


def test_PASS_the_fixes_are_in_place():
    """② 再能通过：修法在位。"""
    assert " ask " in open("core/tools/cu_learning_impl.py", encoding="utf-8").read()
    assert "basename" in open("core/gateway/sandbox_ops.py", encoding="utf-8").read()


def test_routing_config_import_present():
    """静默失败修复：context_manager 必须真的能拿到 _load_v9_routing_config。"""
    src = open("core/context/context_manager.py", encoding="utf-8").read()
    assert "from core.gateway.v9_bridge.routing_config import" in src


def test_routing_config_is_now_reachable():
    """端到端：该函数确实能加载并返回配置（此前该模块从未被任何模块 import）。"""
    from core.gateway.v9_bridge.routing_config import _load_v9_routing_config

    cfg = _load_v9_routing_config()
    assert isinstance(cfg, dict)
