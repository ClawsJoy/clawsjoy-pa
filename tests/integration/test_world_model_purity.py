"""world_model 纯净性：非 .py 文件不入 modules"""
import sys, json
sys.path.insert(0, ".")
import pytest

from pathlib import Path


def test_update_world_model_skips_non_py():
    """_update_world_model 对非 .py 文件不入 modules（过滤网基准纯净）"""
    from core.gateway.execute_agent_task import _update_world_model
    uid, sid = "wm_u1", "wm_s1"
    state_path = Path(f"data/projects/{uid}/{sid}/clawsjoy_dev/.agent_state.json")
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps({"world_model": {"modules": {}, "last_updated": ""}}), encoding="utf-8")
    try:
        # 写入 .html / .env → 不入 modules（guard 生效，提前 return）
        _update_world_model("clawsjoy_dev/web/dashboard/test.html", "<html></html>", uid, sid)
        _update_world_model("clawsjoy_dev/.env", "SECRET=x", uid, sid)
        state = json.loads(state_path.read_text(encoding="utf-8"))
        mods = state.get("world_model", {}).get("modules", {})
        assert len(mods) == 0, f"非 .py 混入: {list(mods.keys())}"
    finally:
        import shutil
        shutil.rmtree(state_path.parent, ignore_errors=True)


def test_backfill_scans_only_py():
    """backfill 脚本只扫 .py（源码断言）"""
    src = open("tools/backfill_world_model.py", encoding="utf-8").read()
    assert "*.py" in src
    assert "WORKSPACE_ROOT" in src, "应 cwd 无关"
    assert "EXCLUDE" in src
