"""#22 VectorKnowledgeCenter get_client 修复回归测试"""
import sys
sys.path.insert(0, ".")
import pytest


def test_get_client_exists_and_returns_client(monkeypatch, tmp_path):
    """get_client 存在且返回 ChromaDB client(#22 修复: 原死代码块移入 _init)"""
    import core.lib.vector_knowledge_center as vkc_mod
    # 隔离单例, 用 tmp_path 避免污染真实 vector_kb
    monkeypatch.setattr(vkc_mod.VectorKnowledgeCenter, "_instances", {})
    monkeypatch.setattr(vkc_mod, "get_data_root", lambda: str(tmp_path))
    vkc = vkc_mod.VectorKnowledgeCenter("test_sess_22")
    # get_client 存在且可用
    assert hasattr(vkc, "get_client"), "VectorKnowledgeCenter 应有 get_client"
    client = vkc.get_client()
    assert client is not None
    # collections 应已初始化(原死代码 bug: 位于 return 之后从不执行)
    assert hasattr(vkc, "collections"), "collections 应已初始化(修复死代码)"
    assert set(vkc.collections.keys()) >= {"skills", "agents", "routes", "memories", "documents"}


def test_code_indexer_reuses_get_client(monkeypatch, tmp_path):
    """code_indexer 经 get_client 复用 ChromaDB 客户端, 不再抛 AttributeError"""
    import core.lib.vector_knowledge_center as vkc_mod
    monkeypatch.setattr(vkc_mod.VectorKnowledgeCenter, "_instances", {})
    monkeypatch.setattr(vkc_mod, "get_data_root", lambda: str(tmp_path))
    from core.lib import code_indexer
    # code_indexer.__init__ 内部 import vector_knowledge_center, monkeypatch 模块级单例即可
    fake = vkc_mod.VectorKnowledgeCenter("test_sess_22b")
    monkeypatch.setattr(vkc_mod, "vector_knowledge_center", fake)
    # 复现原调用路径: CodeIndexer 构造不再抛 AttributeError(非致命已修)
    ci = code_indexer.CodeIndexer(project_root=str(tmp_path))
    assert ci.chroma_client is fake.get_client()
