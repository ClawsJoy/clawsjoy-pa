"""永久记忆方案A: 合并加载 fallback(历史 user_id 变更后恢复记忆)"""
import sys, os, json, hashlib
sys.path.insert(0, ".")
from pathlib import Path
import pytest

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@127.0.0.1:5432/test")


@pytest.fixture(autouse=True)
def _isolate_memory(tmp_path, monkeypatch):
    """把记忆目录隔离到 tmp_path, 不碰真实 data/permanent_memory。

    注意: base_agent 是模块级 from ... import get_data_root, 必须 patch
    base_agent 模块自己的引用(而非 config_helper)。
    """
    import core.agents.base.base_agent as ba
    mem_dir = tmp_path / "permanent_memory"
    mem_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(ba, "get_data_root", lambda: str(tmp_path))
    yield mem_dir


def _make_mem_file(mem_dir, user_id, name, key, value, ts):
    """写一个记忆文件(旧 user_id 命名)"""
    k = hashlib.md5(f"{user_id}_{name}".encode()).hexdigest()[:16]
    data = {key: {"value": value, "importance": 5, "timestamp": ts, "agent": name}}
    (mem_dir / f"{k}.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def test_exact_key_loads(_isolate_memory):
    """精确 key 命中: 正常加载, 不走 fallback"""
    mem_dir = _isolate_memory
    _make_mem_file(mem_dir, "current_user", "memory_agent_v4", "名字", "小明", "2026-08-01T00:00:00")
    from agents.memory_agent.agent_v4 import MemoryAgentV4
    agent = MemoryAgentV4("current_user")
    mem = agent.get_all_memories()["permanent"]
    assert mem.get("名字", {}).get("value") == "小明"


def test_fallback_merges_old_user_files(_isolate_memory):
    """精确 key 不存在: fallback 合并所有同 name 历史文件(旧 user_id 记忆恢复)"""
    mem_dir = _isolate_memory
    # 两个不同旧 user_id 的记忆文件, 内容 agent 都是 memory_agent_v4
    _make_mem_file(mem_dir, "old_user_a", "memory_agent_v4", "名字", "李四", "2026-06-27T06:56:00")
    _make_mem_file(mem_dir, "old_user_b", "memory_agent_v4", "密码", "abc", "2026-06-27T07:00:00")
    from agents.memory_agent.agent_v4 import MemoryAgentV4
    agent = MemoryAgentV4("new_user")  # 精确 key 不存在
    mem = agent.get_all_memories()["permanent"]
    assert len(mem) == 2, f"应合并 2 条: {mem}"
    assert mem.get("名字", {}).get("value") == "李四"
    assert mem.get("密码", {}).get("value") == "abc"


def test_fallback_ignores_other_agents(_isolate_memory):
    """fallback 只合并本 agent 的记忆, 忽略其他 agent 文件"""
    mem_dir = _isolate_memory
    _make_mem_file(mem_dir, "old_a", "memory_agent_v4", "名字", "李四", "2026-06-27T00:00:00")
    # 另一个 agent 的文件(agent 字段不同)
    other_key = hashlib.md5("old_a_other_agent".encode()).hexdigest()[:16]
    (mem_dir / f"{other_key}.json").write_text(json.dumps(
        {"x": {"value": 1, "importance": 5, "timestamp": "2026-06-27T00:00:00", "agent": "other_agent"}}
    ), encoding="utf-8")
    from agents.memory_agent.agent_v4 import MemoryAgentV4
    agent = MemoryAgentV4("new_user")
    mem = agent.get_all_memories()["permanent"]
    assert len(mem) == 1, f"只应加载本 agent: {mem}"
    assert "x" not in mem


def test_save_writes_exact_key(_isolate_memory):
    """保存仍写精确 key(新记忆归位), 不污染 fallback 源文件"""
    mem_dir = _isolate_memory
    _make_mem_file(mem_dir, "old_a", "memory_agent_v4", "名字", "李四", "2026-06-27T00:00:00")
    from agents.memory_agent.agent_v4 import MemoryAgentV4
    agent = MemoryAgentV4("new_user")
    agent.remember_forever("新记忆", "hello")
    # 精确 key 文件应存在且含新记忆
    k = hashlib.md5("new_user_memory_agent_v4".encode()).hexdigest()[:16]
    exact = mem_dir / f"{k}.json"
    assert exact.exists(), f"应写精确 key 文件: {exact}"
    data = json.loads(exact.read_text(encoding="utf-8"))
    assert data.get("新记忆", {}).get("value") == "hello"
