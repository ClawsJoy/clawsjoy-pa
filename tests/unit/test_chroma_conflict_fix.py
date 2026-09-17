"""#30 回归测试: Chroma 实例冲突 — VectorMemory/experience_decider 复用 VKC client"""
import sys
sys.path.insert(0, ".")
import pytest


def test_memory_vector_reuses_vkc_client():
    """VectorMemory 默认库应复用 VectorKnowledgeCenter.get_client()"""
import core.lib.memory_vector as mv
src = open(mv.__file__, encoding="utf-8").read()
assert "vector_knowledge_center as _vkc" in src, "应复用 VKC"
assert "_vkc.get_client()" in src, "应调用 get_client()"
assert "allow_reset=True" in src, "自定义目录也应用 allow_reset=True(与 VKC 一致)"


def test_experience_decider_reuses_vkc_client():
    """experience_decider 应复用 VKC client(不再独立创建 default 路径客户端)"""
import core.lib.experience_decider as ed
src = open(ed.__file__, encoding="utf-8").read()
assert "vector_knowledge_center as _vkc" in src, "应复用 VKC"
assert "_vkc.get_client()" in src, "应调用 get_client()"


def test_no_chroma_conflict_sequence():
    """顺序实例化 VKC -> VectorMemory -> experience_decider 无冲突"""
from core.lib.vector_knowledge_center import vector_knowledge_center as vkc
from core.lib.memory_vector import VectorMemory
vm = VectorMemory()
assert vm.client is not None
assert vm.collection is not None, "collection 应可访问"
from core.lib.experience_decider import get_experience_decider
d = get_experience_decider()
assert d is not None
assert not hasattr(d, "_client_error") or d.client is not None


def test_memory_vector_custom_dir_still_works():
    """VectorMemory 自定义目录仍可独立创建(带 allow_reset=True)"""
import tempfile
from pathlib import Path
from core.lib.memory_vector import VectorMemory
with tempfile.TemporaryDirectory() as td:
    vm = VectorMemory(persist_dir=td)
    assert vm.client is not None
    did = vm.add("test memory", category="test")
    assert did, "add 应返回 doc_id"
