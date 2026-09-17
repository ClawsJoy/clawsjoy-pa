# -*- coding: utf-8 -*-
"""S3 单测: 统一执行缓存(shared_state.tool_exec_cache) + 工具输出策略"""
import os
import sys

sys.path.insert(0, ".")
import agent_gateway_enhanced as main
from core.gateway.shared_state import (
    _invalidate_read_content_cache,
    _tool_exec_cache,
    tool_exec_cache_get,
    tool_exec_cache_put,
)


def _reset():
    _tool_exec_cache.clear()


def test_policy_json_array_count():
    arr = ",".join('"%03d项内容凑长度填充填充%d"' % (i, i) for i in range(120))
    out = main._truncate_tool_result_content("[" + arr + "]")
    assert "共 120 项" in out and "000项" in out, out[:80]


def test_policy_multiline_count():
    txt = "\n".join("条目 %d " % i + "x" * 60 for i in range(60))
    out = main._truncate_tool_result_content(txt)
    assert "60 行条目" in out and "条目 0" in out and "条目 59" in out, out[:80]


def test_policy_generic_long_marker():
    big = "HEAD" + "m" * 4992 + "TAIL"
    out = main._truncate_tool_result_content(big)
    assert out.startswith("HEAD") and out.endswith("TAIL"), out[:60]
    assert "[TRUNCATED]" in out and "原文 5000 字符" in out


def test_policy_short_passthrough():
    assert main._truncate_tool_result_content("短内容") == "短内容"


def test_tool_exec_cache_roundtrip_and_rules():
    _reset()
    d = os.path.abspath("data/tmp")
    # data/ 在 .gitignore 里(运行时目录), 新克隆/新副本下不存在;
    # 产品侧由 write_file 用时自动建父目录(docs/reports/v9_tmp_usage_audit_20260829.md),
    # 所以这里用例自建, 不把"未 provisioning 的运行时目录"当产品契约。
    os.makedirs(d, exist_ok=True)
    assert os.path.isdir(d)
    r = {"success": True, "content": "目录内容"}
    tool_exec_cache_put("s3_1", "list_dir", {"path": d}, r)
    assert tool_exec_cache_get("s3_1", "list_dir", {"path": d}) == r
    # 非读类不缓存
    tool_exec_cache_put("s3_1", "write_file", {"path": "x"}, {"success": True})
    assert tool_exec_cache_get("s3_1", "write_file", {"path": "x"}) is None
    # 失败不缓存
    tool_exec_cache_put("s3_1", "read_file", {"path": "missing"}, {"success": False})
    assert tool_exec_cache_get("s3_1", "read_file", {"path": "missing"}) is None


def test_tool_exec_cache_mtime_staleness_and_write_invalidation(tmp_path):
    _reset()
    f = tmp_path / "a.txt"
    f.write_text("v1", encoding="utf-8")
    tool_exec_cache_put("s3_2", "read_file", {"path": str(f)}, {"success": True, "content": "v1"})
    assert tool_exec_cache_get("s3_2", "read_file", {"path": str(f)}) is not None
    # 文件变更(mtime) → 缓存失效
    import time as _t

    f.write_text("v2", encoding="utf-8")
    os.utime(str(f), (_t.time() + 3, _t.time() + 3))
    assert tool_exec_cache_get("s3_2", "read_file", {"path": str(f)}) is None
    # 写失效(整个 session 执行缓存清空)
    tool_exec_cache_put("s3_2", "list_dir", {"path": str(tmp_path)}, {"success": True, "content": "x"})
    _invalidate_read_content_cache("s3_2")
    assert tool_exec_cache_get("s3_2", "list_dir", {"path": str(tmp_path)}) is None


def test_gateway_uses_shared_service():
    src = open(main.__file__, encoding="utf-8").read()
    _TR = open("core/gateway/v9_bridge/tool_runner.py", encoding="utf-8").read()
    assert "_L4_TOOL_CACHE" not in src, "agent_gateway 不应再有本地执行缓存"
    assert "def _l4_cache_get" not in src
    assert "from core.gateway.shared_state import tool_exec_cache_get" in _TR, "桥接应调用共享缓存"
    assert "from core.gateway.shared_state import empty_arg_error" in _TR, "空参应调共享逻辑"
