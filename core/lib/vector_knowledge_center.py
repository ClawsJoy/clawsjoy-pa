#!/usr/bin/env python3
"""Vector Knowledge Center - Vector Knowledge Center 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from typing import Dict, List, Optional

from core.lib.config_helper import (
    get_data_root,
    get_embedding_model,
    get_gateway_port,
    get_llm_endpoint,
    get_llm_model,
    get_timeout,
)
from core.lib.unified_config import unified_config

"""向量知识中心 - 智能知识管理"""

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings

#: 向量仓之件名（**一处定形** —— ⛔ 散写之字面）。
VECTOR_DB_NAME = u"chroma.sqlite3"


import logging

_log = logging.getLogger(__name__)


class _UnavailableCollections(dict):
    u"""连不成时之**照实之占位**（⛔ 静默）：凡真取集合 ⇒ 明报其因。

    由（pm_1694 §二 令⒜）：`import core` ⛔ 得因「外部之态」（仓之锁 ／ 异形 ／ 版漂）而死 ——
    本机之实（2026-10-07）：`<cwd>/data/vector_kb/chroma.sqlite3` 为异形 ⇒ `chromadb/api/rust.py`
    之 `start()` 抛 ⇒ 其 `stop()` 复以 `AttributeError: 'RustBindingsAPI' object has no
    attribute 'bindings'` 派之 ⇒ **凡「引 core」之齿（全族）皆败**（⛔ 其件之过）。
    """

    def __init__(self, why):
        super().__init__()
        self.why = u"%s" % (why,)

    def __getitem__(self, key):
        raise RuntimeError(u"向量知识中心不可用：%s" % self.why)

    def get(self, key, default=None):
        raise RuntimeError(u"向量知识中心不可用：%s" % self.why)



class VectorKnowledgeCenter:
    """向量知识中心 - 统一管理所有向量化知识"""

    _instances = {}  # 按 session_id 隔离

    def __new__(cls, session_id=None):
        _key = session_id or "default"
        if _key not in cls._instances:
            cls._instances[_key] = super().__new__(cls)
            cls._instances[_key]._init(session_id)
        return cls._instances[_key]

    def _init(self, session_id=None):
        # 初始化 ChromaDB 客户端（按 session 隔离）
        _dir = f"{get_data_root()}/vector_kb"
        if session_id and session_id != "default":
            _dir = f"data/projects/{session_id}/vector_kb"
        self.persist_dir = Path(_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        # ⭐ pm_1694 §二 令⒜：连 ⇒ **照实之降**（⛔ 令 import 死 · ⛔ 静默）
        self.available = False
        self.connect_error = u""
        try:
            self.client = chromadb.PersistentClient(
                path=str(self.persist_dir), settings=Settings(anonymized_telemetry=False, allow_reset=True)
            )

            # 知识集合映射（#22 修复: 原块误置于 get_client 的 return 之后成为死代码,
            # collections 从不初始化, add_skill/search 等路径 AttributeError）
            self.collections = {
                "skills": self.client.get_or_create_collection(name="knowledge_skills", metadata={"description": "技能知识库"}),
                "agents": self.client.get_or_create_collection(
                    name="knowledge_agents", metadata={"description": "Agent知识库"}
                ),
                "routes": self.client.get_or_create_collection(name="knowledge_routes", metadata={"description": "路由知识库"}),
                "memories": self.client.get_or_create_collection(
                    name="knowledge_memories", metadata={"description": "记忆知识库"}
                ),
                "documents": self.client.get_or_create_collection(
                    name="knowledge_documents", metadata={"description": "文档知识库"}
                ),
            }

            self.available = True
        except Exception as _exc:                          # noqa: BLE001 —— 照实之降（⛔ 静默）
            self.client = None
            self.connect_error = u"%s: %s" % (type(_exc).__name__, _exc)
            self.collections = _UnavailableCollections(self.connect_error)
            self._forget_half_started()
            _log.warning(u"向量知识中心不可用（%s）⇒ %s", self.persist_dir, self.connect_error)

        # #25 启动日志: 默认实例遍历所有 session 库统计总数(真实数据在 data/projects/{sid}/vector_kb)
        if not self.available:
            print(u"⚠️ 向量知识中心不可用（%s）：%s" % (self.persist_dir, self.connect_error))
            print(u"   - 去处：核 `%s`（锁 ／ 异形 ／ 版漂）" % (self.persist_dir / VECTOR_DB_NAME))
        elif session_id in (None, "default"):
            _totals = self.count_all_sessions()
            print(f"✅ 向量知识中心初始化完成（全 session 汇总）")
            for _label, _cnt in _totals.items():
                print(f"   - {_label}: {_cnt} 条")
        else:
            print(f"✅ 向量知识中心初始化完成")
            for name, col in self.collections.items():
                print(f"   - {name}: {col.count()} 条")

    def _forget_half_started(self):
        u"""抹「半启之 system」（承上）—— `chromadb` 于 `start()` **之前**即登其 system ⇒
        start 败后其 stop 复以 `del self.bindings` 抛（**即 PM 报之错**）⇒ 故**先抹其登**。"""
        try:
            from chromadb.api.shared_system_client import SharedSystemClient as _S
            _S._identifier_to_system.pop(str(self.persist_dir), None)
            _S._identifier_to_refcount.pop(str(self.persist_dir), None)
        except Exception:                                  # noqa: BLE001 —— 照实
            pass

    def get_client(self):
        """获取底层 ChromaDB 客户端（#22: 供 code_indexer 等复用, 与旧版 live 兼容）

        ⚠ 连不成 ⇒ `None`（**照实**：`available` ／ `connect_error` 载其因 —— 承 pm_1694 §二）。
        """
        if not self.available:
            _log.warning(u"get_client：向量知识中心不可用（%s）", self.connect_error)
        return self.client

    def count_all_sessions(self) -> Dict[str, int]:
        """#25: 遍历默认 + 所有 session 的 vector_kb, 统计五集合总数(只读 sqlite, 不改存储)"""
        import sqlite3 as _sq

        _totals = {k: 0 for k in self.collections}
        _roots = [Path(get_data_root()) / "vector_kb"]  # 默认库
        _projects = Path(get_data_root()) / "projects"
        if _projects.exists():
            for _d in sorted(_projects.iterdir()):
                if _d.is_dir():
                    _roots.append(_d / "vector_kb")
        for _root in _roots:
            _db = _root / "chroma.sqlite3"
            if not _db.exists():
                continue
            try:
                _con = _sq.connect(f"file:{_db.resolve()}?mode=ro", uri=True)
                try:
                    _rows = _con.execute(
                        "SELECT c.name, COUNT(e.id) FROM collections c "
                        "LEFT JOIN segments s ON s.collection = c.id "
                        "LEFT JOIN embeddings e ON e.segment_id = s.id "
                        "GROUP BY c.name"
                    ).fetchall()
                    _counts = dict(_rows)
                    for _label, _col in self.collections.items():
                        _totals[_label] += _counts.get(_col.name, 0)
                finally:
                    _con.close()
            except Exception:
                continue  # 单库读取失败不阻断统计
        return _totals

    def _get_collection(self, name: str):
        """获取集合"""
        if not self.available:
            raise RuntimeError(u"向量知识中心不可用：%s" % self.connect_error)
        try:
            return self.client.get_collection(name)
        except Exception:
            return None

    def _get_or_create_collection(self, name: str):
        """获取或创建集合"""
        if not self.available:
            raise RuntimeError(u"向量知识中心不可用：%s" % self.connect_error)
        try:
            return self.client.get_collection(name)
        except Exception:
            return self.client.create_collection(name)

    # ========== 知识入库 ==========
    def add_skill(self, skill_name: str, metadata: Dict) -> str:
        """添加技能知识"""
        doc_id = hashlib.md5(f"skill_{skill_name}".encode()).hexdigest()[:16]

        doc = f"""
技能名称: {skill_name}
分类: {metadata.get('category', 'general')}
描述: {metadata.get('description', '')}
关键词: {metadata.get('keywords', skill_name)}
用法: {metadata.get('usage', '')}
        """

        self.collections["skills"].upsert(
            ids=[doc_id],
            documents=[doc],
            metadatas=[
                {
                    "type": "skill",
                    "name": skill_name,
                    "category": metadata.get("category", "general"),
                    "description": metadata.get("description", "")[:200],
                    "tags": metadata.get("keywords", skill_name),
                    "created_at": datetime.now().isoformat(),
                }
            ],
        )
        return doc_id

    def add_agent(self, agent_name: str, metadata: Dict) -> str:
        """添加 Agent 知识"""
        doc_id = hashlib.md5(f"agent_{agent_name}".encode()).hexdigest()[:16]

        doc = f"""
Agent名称: {agent_name}
类型: {metadata.get('type', 'core')}
能力: {metadata.get('capabilities', '')}
描述: {metadata.get('description', '')}
性格: {metadata.get('personality', 'professional')}
        """

        self.collections["agents"].upsert(
            ids=[doc_id],
            documents=[doc],
            metadatas=[
                {
                    "type": "agent",
                    "name": agent_name,
                    "capabilities": metadata.get("capabilities", ""),
                    "personality": metadata.get("personality", "professional"),
                    "created_at": datetime.now().isoformat(),
                }
            ],
        )
        return doc_id

    def add_memory(self, content: str, user_id: str, category: str = "general") -> str:
        """添加记忆知识"""
        doc_id = hashlib.md5(f"memory_{user_id}_{datetime.now().isoformat()}".encode()).hexdigest()[:16]

        self.collections["memories"].upsert(
            ids=[doc_id],
            documents=[content],
            metadatas=[
                {
                    "type": "memory",
                    "user_id": user_id,
                    "category": category,
                    "created_at": datetime.now().isoformat(),
                }
            ],
        )
        return doc_id

    # ========== 知识检索 ==========
    def search(self, query: str, knowledge_type: str = None, n: int = 10) -> List[Dict]:
        """智能检索"""
        results = []

        # 确定搜索范围
        if knowledge_type and knowledge_type in self.collections:
            collections = {knowledge_type: self.collections[knowledge_type]}
        else:
            collections = self.collections

        for col_name, collection in collections.items():
            try:
                search_results = collection.query(query_texts=[query], n_results=n)

                if search_results["documents"] and search_results["documents"][0]:
                    for i, doc in enumerate(search_results["documents"][0]):
                        results.append(
                            {
                                "source": col_name,
                                "content": doc[:300],
                                "score": (1 - search_results["distances"][0][i] if search_results["distances"] else 0),
                                "metadata": (search_results["metadatas"][0][i] if search_results["metadatas"] else {}),
                            }
                        )
            except Exception as e:
                print(f"搜索 {col_name} 失败: {e}")

                # 按相似度排序
        results.sort(key=lambda x: -x["score"])
        return results[:n]

    def search_skills(self, query: str, n: int = 10) -> List[Dict]:
        """搜索技能"""
        return self.search(query, "skills", n)

    def search_agents(self, query: str, n: int = 10) -> List[Dict]:
        """搜索 Agent"""
        return self.search(query, "agents", n)

    # ========== 知识统计 ==========
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {name: collection.count() for name, collection in self.collections.items()}

    def get_categories(self) -> Dict:
        """获取分类统计"""
        categories = {}
        for col_name, collection in self.collections.items():
            categories[col_name] = {
                "count": collection.count(),
                "description": collection.metadata.get("description", ""),
            }
        return categories

    # ========== 知识清理 ==========
    def clear_collection(self, collection_name: str):
        """清空指定集合"""
        if collection_name in self.collections:
            # 获取所有 IDs
            all_data = self.collections[collection_name].get()
            if all_data["ids"]:
                self.collections[collection_name].delete(ids=all_data["ids"])
            print(f"✅ 已清空 {collection_name} 集合")

    def rebuild_index(self):
        """重建索引"""
        for name in self.collections:
            self.clear_collection(name)
        print("✅ 所有索引已重建")

    # ==================== 会员向量管理 ====================

    def add_member(self, user_id: str, metadata: Dict) -> str:
        """添加会员向量 - 用于相似会员推荐和个性化服务"""
        collection = self._get_or_create_collection("butler_members")
        doc_id = f"member_{user_id}"

        # 构造会员特征文本（用于向量化）
        content = self._member_to_text(metadata)

        # 准备元数据
        meta = {
            "user_id": user_id,
            "butler_name": metadata.get("butler_name", "小管"),
            "level": metadata.get("level", "bronze"),
            "interactions": metadata.get("interactions", 0),
            "achievements": metadata.get("achievements", 0),
            "tags": metadata.get("tags", []),
            "timestamp": datetime.now().isoformat(),
        }

        try:
            collection.upsert(ids=[doc_id], documents=[content], metadatas=[meta])
            print(f"✅ 会员向量已添加: {user_id}")
            return doc_id
        except Exception as e:
            print(f"❌ 添加会员向量失败: {e}")
            return ""

    def _member_to_text(self, metadata: Dict) -> str:
        """将会员元数据转换为文本特征"""
        parts = [
            f"会员等级: {metadata.get('level', 'bronze')}",
            f"管家名称: {metadata.get('butler_name', '小管')}",
            f"交互次数: {metadata.get('interactions', 0)}",
            f"成就数量: {metadata.get('achievements', 0)}",
        ]

        # 添加标签
        tags = metadata.get("tags", [])
        if tags:
            parts.append(f"兴趣标签: {', '.join(tags)}")

        return "。".join(parts)

    def update_member(self, user_id: str, metadata: Dict) -> bool:
        """更新会员向量"""
        doc_id = f"member_{user_id}"
        collection = self._get_collection("butler_members")
        if not collection:
            return False

        content = self._member_to_text(metadata)
        meta = {
            "user_id": user_id,
            "butler_name": metadata.get("butler_name", "小管"),
            "level": metadata.get("level", "bronze"),
            "interactions": metadata.get("interactions", 0),
            "achievements": metadata.get("achievements", 0),
            "updated_at": datetime.now().isoformat(),
        }

        try:
            collection.update(ids=[doc_id], documents=[content], metadatas=[meta])
            return True
        except Exception:
            # 如果更新失败，尝试添加
            return bool(self.add_member(user_id, metadata))

    def search_members(self, query: str, n: int = 10) -> List[Dict]:
        """根据查询文本检索相似会员"""
        collection = self._get_collection("butler_members")
        if not collection:
            return []

        try:
            results = collection.query(query_texts=[query], n_results=n)
            return self._format_member_results(results)
        except Exception as e:
            print(f"❌ 检索会员失败: {e}")
            return []

    def search_similar_members(self, user_id: str, n: int = 5) -> List[Dict]:
        """基于现有会员找相似会员（排除自己）"""
        collection = self._get_collection("butler_members")
        if not collection:
            return []

        doc_id = f"member_{user_id}"

        try:
            # 获取该会员的文档
            result = collection.get(ids=[doc_id])
            if not result["documents"]:
                return []

            # 用该会员的内容检索相似会员
            results = collection.query(
                query_texts=[result["documents"][0]],
                n_results=n + 1,  # 多取一个，排除自己
            )

            formatted = self._format_member_results(results)
            # 排除自己
            return [r for r in formatted if r.get("user_id") != user_id][:n]
        except Exception as e:
            print(f"❌ 查找相似会员失败: {e}")
            return []

    def _format_member_results(self, results: Dict) -> List[Dict]:
        """格式化会员检索结果"""
        formatted = []
        if not results.get("ids"):
            return formatted

        for i, doc_id in enumerate(results["ids"][0]):
            metadata = results["metadatas"][0][i] if results.get("metadatas") else {}
            formatted.append(
                {
                    "user_id": metadata.get("user_id", doc_id.replace("member_", "")),
                    "butler_name": metadata.get("butler_name", "小管"),
                    "level": metadata.get("level", "bronze"),
                    "interactions": metadata.get("interactions", 0),
                    "achievements": metadata.get("achievements", 0),
                    "similarity_score": (results["distances"][0][i] if results.get("distances") else 1.0),
                    "content": (results["documents"][0][i] if results.get("documents") else ""),
                }
            )
        return formatted

    def get_member_vector_stats(self) -> Dict:
        """获取会员向量统计"""
        collection = self._get_collection("butler_members")
        if not collection:
            return {"count": 0, "exists": False}

        try:
            count = collection.count()
            return {"exists": True, "count": count, "collection_name": "butler_members"}
        except Exception as e:
            return {"count": 0, "error": str(e)}

    # ==================== 会员向量管理 ====================

    def _get_member_collection(self):
        """获取或创建会员集合"""
        try:
            return self.client.get_collection("butler_members")
        except Exception:
            return self.client.create_collection("butler_members")

    def add_member(self, user_id: str, metadata: dict) -> str:
        """添加会员向量"""
        collection = self._get_member_collection()
        doc_id = f"member_{user_id}"

        # 构造特征文本
        content = f"等级:{metadata.get('level','bronze')} 管家:{metadata.get('butler_name','小管')} 交互:{metadata.get('interactions',0)} 成就:{metadata.get('achievements',0)}"

        collection.upsert(
            ids=[doc_id],
            documents=[content],
            metadatas=[
                {
                    "user_id": user_id,
                    "butler_name": metadata.get("butler_name", "小管"),
                    "level": metadata.get("level", "bronze"),
                    "interactions": metadata.get("interactions", 0),
                    "achievements": metadata.get("achievements", 0),
                    "timestamp": datetime.now().isoformat(),
                }
            ],
        )
        return doc_id

    def update_member(self, user_id: str, metadata: dict) -> bool:
        """更新会员向量"""
        try:
            collection = self._get_member_collection()
            doc_id = f"member_{user_id}"
            content = f"等级:{metadata.get('level','bronze')} 管家:{metadata.get('butler_name','小管')} 交互:{metadata.get('interactions',0)} 成就:{metadata.get('achievements',0)}"
            collection.update(
                ids=[doc_id],
                documents=[content],
                metadatas=[
                    {
                        "user_id": user_id,
                        "butler_name": metadata.get("butler_name", "小管"),
                        "level": metadata.get("level", "bronze"),
                        "interactions": metadata.get("interactions", 0),
                        "achievements": metadata.get("achievements", 0),
                        "updated_at": datetime.now().isoformat(),
                    }
                ],
            )
            return True
        except Exception:
            return False

    def search_members(self, query: str, n: int = 10) -> list:
        """搜索相似会员"""
        try:
            collection = self._get_member_collection()
            results = collection.query(query_texts=[query], n_results=n)
            formatted = []
            for i, doc_id in enumerate(results["ids"][0]):
                meta = results["metadatas"][0][i] if results.get("metadatas") else {}
                formatted.append(
                    {
                        "user_id": meta.get("user_id", ""),
                        "butler_name": meta.get("butler_name", ""),
                        "level": meta.get("level", ""),
                        "score": (results["distances"][0][i] if results.get("distances") else 1.0),
                    }
                )
            return formatted
        except Exception:
            return []

    def get_member_stats(self) -> dict:
        """获取会员向量统计"""
        try:
            collection = self._get_member_collection()
            return {"count": collection.count(), "exists": True}
        except Exception:
            return {"count": 0, "exists": False}

    # ==================== 路由知识管理 ====================

    def add_route(self, route_name: str, metadata: dict) -> str:
        """添加路由知识"""
        doc_id = hashlib.md5(f"route_{route_name}".encode()).hexdigest()[:16]

        doc = f"""
路由名称: {route_name}
描述: {metadata.get('description', '')}
文件: {metadata.get('file', '')}
        """

        self.collections["routes"].upsert(
            ids=[doc_id],
            documents=[doc],
            metadatas=[
                {
                    "type": "route",
                    "name": route_name,
                    "description": metadata.get("description", "")[:200],
                    "file": metadata.get("file", ""),
                    "created_at": datetime.now().isoformat(),
                }
            ],
        )
        return doc_id

    # ==================== 文档知识管理 ====================

    def add_document(self, doc_id: str, content: str, metadata: dict = None) -> str:
        """添加文档知识"""
        import hashlib

        doc_hash = hashlib.md5(f"doc_{doc_id}".encode()).hexdigest()[:16]

        self.collections["documents"].upsert(
            ids=[doc_hash],
            documents=[content[:2000]],
            metadatas=[
                {
                    "doc_id": doc_id,
                    "type": (metadata.get("type", "document") if metadata else "document"),
                    "file": metadata.get("file", "") if metadata else "",
                    "title": metadata.get("title", doc_id) if metadata else doc_id,
                    "created_at": datetime.now().isoformat(),
                }
            ],
        )
        return doc_hash

    def search_documents(self, query: str, n: int = 10) -> list:
        """检索文档"""
        try:
            results = self.collections["documents"].query(query_texts=[query], n_results=n)
            formatted = []
            if results.get("ids"):
                for i, doc_id in enumerate(results["ids"][0]):
                    metadata = results["metadatas"][0][i] if results.get("metadatas") else {}
                    formatted.append(
                        {
                            "doc_id": metadata.get("doc_id", doc_id),
                            "title": metadata.get("title", ""),
                            "type": metadata.get("type", ""),
                            "score": (results["distances"][0][i] if results.get("distances") else 1.0),
                        }
                    )
            return formatted
        except Exception as e:
            return []

            # ==================== 检索缓存 ====================

            #             _cache = {}
            _cache_size = 100
            _cache_ttl = 300  # 5分钟

    def search_with_cache(self, query: str, knowledge_type: str = None, n: int = 10) -> list:
        """带缓存的检索"""
        cache_key = f"{query}:{knowledge_type}:{n}"

        # 检查缓存
        if cache_key in self._cache:
            cached_time, cached_result = self._cache[cache_key]
            if (datetime.now().timestamp() - cached_time) < self._cache_ttl:
                return cached_result

        # 执行检索
        result = self.search(query, knowledge_type, n)

        # 更新缓存
        if len(self._cache) > self._cache_size:
            # 删除最旧的
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][0])
            del self._cache[oldest_key]

        self._cache[cache_key] = (datetime.now().timestamp(), result)
        return result

    # ==================== Agent 能力向量管理 ====================

    def add_agent_capability(self, agent_name: str, capability_desc: str, user_id: str = "system") -> str:
        """添加 Agent 能力向量（用于智能路由）"""
        collection = self._get_or_create_collection("agent_capabilities")
        doc_id = f"agent_{user_id}_{agent_name}"

        content = f"Agent: {agent_name}\n能力描述: {capability_desc}"

        collection.upsert(
            ids=[doc_id],
            documents=[content],
            metadatas=[
                {
                    "agent_name": agent_name,
                    "user_id": user_id,
                    "capability_desc": capability_desc[:500],
                    "created_at": datetime.now().isoformat(),
                }
            ],
        )
        return doc_id

    def find_best_agent(self, query: str, user_id: str = None, top_k: int = 3) -> list:
        """根据用户请求找到最匹配的 Agent"""
        collection = self._get_collection("agent_capabilities")
        if not collection:
            return []

        try:
            # 过滤条件
            where_filter = {"user_id": user_id} if user_id else None
            results = collection.query(query_texts=[query], n_results=top_k, where=where_filter)
            return self._format_agent_results(results)
        except Exception as e:
            print(f"检索 Agent 失败: {e}")
            return []

    def _format_agent_results(self, results: dict) -> list:
        """格式化 Agent 检索结果"""
        formatted = []
        if not results.get("ids"):
            return formatted

        for i, doc_id in enumerate(results["ids"][0]):
            metadata = results["metadatas"][0][i] if results.get("metadatas") else {}
            formatted.append(
                {
                    "agent_name": metadata.get("agent_name", ""),
                    "user_id": metadata.get("user_id", ""),
                    "score": (results["distances"][0][i] if results.get("distances") else 1.0),
                }
            )
        return formatted

    def list_agent_capabilities(self, user_id: str = None) -> list:
        """列出 Agent 能力"""
        collection = self._get_collection("agent_capabilities")
        if not collection:
            return []

        try:
            where_filter = {"user_id": user_id} if user_id else None
            results = collection.get(where=where_filter)
            agents = []
            for i, metadata in enumerate(results["metadatas"]):
                agents.append(
                    {
                        "agent_name": metadata.get("agent_name"),
                        "user_id": metadata.get("user_id"),
                        "capability": metadata.get("capability_desc", "")[:100],
                    }
                )
            return agents
        except Exception:
            return []

    def find_best_agent_exclude_self(self, query: str, exclude_agent: str, user_id: str = None, top_k: int = 5) -> list:
        """找到最匹配的 Agent（排除指定 Agent）"""
        collection = self._get_collection("agent_capabilities")
        if not collection:
            return []

        try:
            where_filter = {"user_id": user_id} if user_id else None
            results = collection.query(query_texts=[query], n_results=top_k, where=where_filter)
            formatted = self._format_agent_results(results)
            # 排除指定 Agent
            return [r for r in formatted if r.get("agent_name") != exclude_agent]
        except Exception as e:
            print(f"检索 Agent 失败: {e}")
            return []

        #         """智能搜索 - 自动分类"""
        knowledge_type = self.classify_query(query)
        return self.search(query, knowledge_type=knowledge_type, n=n)

    def classify_query(self, query: str) -> str:
        """分类查询类型"""
        query_lower = query.lower()

        # 技能相关关键词
        skill_keywords = [
            "技能",
            "skill",
            "执行",
            "execute",
            "调用",
            "call",
            "运行",
            "run",
        ]
        for kw in skill_keywords:
            if kw in query_lower:
                return "skills"

        # 智能体相关关键词
        agent_keywords = ["智能体", "agent", "助手", "assistant", "管家", "butler"]
        for kw in agent_keywords:
            if kw in query_lower:
                return "agents"

        # 记忆相关关键词
        memory_keywords = [
            "记忆",
            "memory",
            "记住",
            "remember",
            "回忆",
            "recall",
            "知道",
            "了解",
        ]
        for kw in memory_keywords:
            if kw in query_lower:
                return "memories"

        # 路由相关关键词
        route_keywords = ["路由", "route", "接口", "api", "路径"]
        for kw in route_keywords:
            if kw in query_lower:
                return "routes"

        # 默认返回 None（全部搜索）
        return None

    def smart_search(self, query: str, n: int = 10) -> List[Dict]:
        """智能搜索 - 自动分类"""
        knowledge_type = self.classify_query(query)
        return self.search(query, knowledge_type=knowledge_type, n=n)


# 全局实例
vector_knowledge_center = VectorKnowledgeCenter()
