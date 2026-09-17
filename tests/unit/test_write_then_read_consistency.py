# -*- coding: utf-8 -*-
"""写后读一致性回归（2026-09-13 bug #6）。

事故：PA 用 obsidian_knowledge(write_note, append=True) 追加完 P11–P13 后回读核对，
连续 3 次 read 都返回 `l4_cached: true` + **追加前的 4362 字符**，只能诚实说「不能作为已就位的证据」。

根因（两个条件同时成立才会死人）：
  1. `obsidian_knowledge` 在 `_TOOL_EXEC_READISH` 里 → 读结果进 `_tool_exec_cache`；
  2. `_tool_stat_sig` 只认 read_file/list_dir → 对 vault 读返回 None → **缓存条目永不失效**；
  3. vault 写（write_note/update_sop/...）**不调** `_invalidate_read_content_cache`（只有 sandbox 写会调）。
→ vault 读缓存整会话不失效，写完再读必拿旧快照。**必现，不是竞态。**
"""
import sys

sys.path.insert(0, ".")
from core.gateway import shared_state as ss


def _cleanup(sid):
    ss._tool_exec_cache.pop(sid, None)


def test_vault_write_invalidates_read_cache(monkeypatch, tmp_path):
    """写成功 → 读缓存必须失效（这是本 bug 的主修）。"""
    sid = "t_bug6_a"
    _cleanup(sid)
    ss.tool_exec_cache_put(
        sid, "obsidian_knowledge", {"action": "read", "sop_key": "PA/x.md"}, {"success": True, "content": "OLD"}
    )
    assert ss.tool_exec_cache_get(sid, "obsidian_knowledge", {"action": "read", "sop_key": "PA/x.md"}) is not None
    ss._invalidate_read_content_cache(sid)  # 等价于 _mark_vault_write 里的调用
    assert ss.tool_exec_cache_get(sid, "obsidian_knowledge", {"action": "read", "sop_key": "PA/x.md"}) is None
    _cleanup(sid)


def test_vault_read_cache_expires_on_mtime_change(monkeypatch, tmp_path):
    """第二道保险：vault 读也要参与 mtime 校验。"""
    vault = tmp_path / "vault"
    (vault / "PA").mkdir(parents=True)
    f = vault / "PA" / "x.md"
    f.write_text("OLD", encoding="utf-8")
    from core.gateway import precision_inject as pi

    monkeypatch.setattr(pi, "_vault_path", lambda: str(vault))
    sid = "t_bug6_b"
    _cleanup(sid)
    args = {"action": "read", "sop_key": "PA/x.md"}
    ss.tool_exec_cache_put(sid, "obsidian_knowledge", args, {"success": True, "content": "OLD"})
    assert ss.tool_exec_cache_get(sid, "obsidian_knowledge", args) is not None
    import time as _t

    _t.sleep(0.01)
    f.write_text("NEW-AND-LONGER", encoding="utf-8")  # mtime/size 都变
    assert ss.tool_exec_cache_get(sid, "obsidian_knowledge", args) is None
    _cleanup(sid)


def test_cache_hit_carries_snapshot_time():
    """命中缓存必须带快照时点 —— agent 据此判断"这是不是旧快照"。"""
    sid = "t_bug6_c"
    _cleanup(sid)
    args = {"action": "read", "sop_key": "固定键"}
    ss.tool_exec_cache_put(sid, "obsidian_knowledge", args, {"success": True, "content": "X"})
    got = ss.tool_exec_cache_get(sid, "obsidian_knowledge", args)
    assert got and "_cached_at" not in got, "默认不得改变返回契约"
    got_meta = ss.tool_exec_cache_get(sid, "obsidian_knowledge", args, with_meta=True)
    assert got_meta and got_meta.get("_cached_at"), got_meta
    _cleanup(sid)


def test_sandbox_write_paths_unchanged():
    """不回归：read_file 的既有失效语义不变。"""
    sid = "t_bug6_d"
    _cleanup(sid)
    args = {"path": "data/x.txt"}
    ss.tool_exec_cache_put(sid, "read_file", args, {"success": True, "content": "A"})
    got = ss.tool_exec_cache_get(sid, "read_file", args)
    assert got is not None and got.get("content") == "A"
    _cleanup(sid)
