# -*- coding: utf-8 -*-
"""SAG 链式注入器。

SagChainInjector 复用 code_entity_extractor 的四个方法，把代码实体搜索、
关键词上下文、边关系查询与图遍历组装为统一的链式注入上下文：

- search_with_hyperedges      实体 + 动态超边扩展搜索
- query_context_by_keywords   步骤摘要 / 代码实体关键词上下文
- get_edges                   按实体名与边类型查询边关系
- traverse_edges              沿 code_edges 图遍历关联实体

用法:
    injector = SagChainInjector()
    ctx = injector.inject_context(query="用户登录", project_id="default")
"""

from typing import Any, Dict, List, Optional

from core.lib.code_entity_extractor import CodeEntityExtractor, CodeEntitySearcher


class SagChainInjector:
    """SAG 链式注入器：包装 CodeEntitySearcher / CodeEntityExtractor 形成链式查询入口。"""

    def __init__(self, db_url: Optional[str] = None):
        """初始化底层 SAG 组件。

        Args:
            db_url: 数据库连接串，缺省时回退到 DATABASE_URL 环境变量或本地默认值。
        """
        self.db_url = db_url
        self._searcher = CodeEntitySearcher(db_url)
        self._extractor = CodeEntityExtractor(db_url)

    # ---- 复用 code_entity_extractor 的四个方法（委托） ----

    def search_with_hyperedges(
        self, query: str, project_id: str = "default", limit: int = 10
    ) -> Dict[str, Any]:
        """查询实体 + 动态超边扩展（支持中文关键词匹配）。

        委托给 CodeEntitySearcher.search_with_hyperedges。
        """
        return self._searcher.search_with_hyperedges(query, project_id, limit)

    def query_context_by_keywords(
        self, keywords: str, task_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """在 steps_summary 和 code_entities 中按关键词模糊匹配，返回上下文摘要列表。

        委托给 CodeEntitySearcher.query_context_by_keywords。
        """
        return self._searcher.query_context_by_keywords(keywords, task_name)

    def get_edges(
        self,
        entity_name: str,
        edge_type: Optional[str] = None,
        project_id: str = "default",
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """查询边关系，可按实体名和边类型过滤。

        委托给 CodeEntityExtractor.get_edges。
        """
        return self._extractor.get_edges(entity_name, edge_type, project_id, limit)

    def traverse_edges(
        self, entity_name: str, depth: int = 2, project_id: str = "default"
    ) -> List[Dict[str, Any]]:
        """沿 code_edges 图遍历，从 entity_name 出发遍历 depth 层。

        委托给 CodeEntitySearcher.traverse_edges。
        """
        return self._searcher.traverse_edges(entity_name, depth, project_id)

    # ---- 链式注入组装 ----

    def inject_context(
        self,
        query: str,
        project_id: str = "default",
        limit: int = 10,
        task_name: Optional[str] = None,
        traverse_depth: int = 2,
    ) -> Dict[str, Any]:
        """链式注入：按 搜索 -> 关键词上下文 -> 图遍历 组装统一上下文。

        Args:
            query: 查询关键词 / 实体名。
            project_id: 项目 ID。
            limit: 搜索返回条数上限。
            task_name: 可选任务名，用于关键词上下文过滤。
            traverse_depth: 图遍历深度。

        Returns:
            {
                "query": query,
                "primary": 主实体命中,
                "related": 超边扩展相关实体,
                "context": 关键词上下文摘要列表,
                "edges": 边关系列表,
                "traversed": 图遍历关联实体,
            }
        """
        hyper = self.search_with_hyperedges(query, project_id, limit)
        context = self.query_context_by_keywords(query, task_name)
        edges: List[Dict[str, Any]] = []
        traversed: List[Dict[str, Any]] = []
        primary = (hyper or {}).get("primary") or {}
        entity_name = primary.get("name") or query
        try:
            edges = self.get_edges(entity_name, project_id=project_id, limit=limit)
        except Exception:
            edges = []
        try:
            traversed = self.traverse_edges(entity_name, traverse_depth, project_id)
        except Exception:
            traversed = []
        return {
            "query": query,
            "primary": hyper.get("primary") if hyper else None,
            "related": hyper.get("related") if hyper else [],
            "referers": hyper.get("referers") if hyper else [],
            "context": context,
            "edges": edges,
            "traversed": traversed,
        }

    def inject_text(
        self,
        task_query: str,
        chain: Optional[List[str]] = None,
        max_items: int = 10,
        max_chars: int = 1500,
        project_id: str = "default",
    ) -> str:
        """链式注入并渲染为可直接拼入系统提示词的文本块。

        Args:
            task_query: 任务查询关键词 / 实体名。
            chain: 依赖链实体类型列表（如 ["task", "plan", "hypothesis", "capability"]），
                按类型逐级查询构成链式上下文。
            max_items: 每类实体最多返回的条目数。
            max_chars: 渲染文本的最大字符数，超出按字符截断。
            project_id: 项目 ID，缺省 "default"。

        Returns:
            渲染后的 markdown 风格上下文文本。
        """
        chain = chain or ["task", "plan", "hypothesis", "capability"]
        lines: List[str] = [f"## SAG 依赖链上下文: {task_query}", ""]
        try:
            hyper = self.search_with_hyperedges(task_query, project_id, max_items)
        except Exception:
            hyper = {}
        hyper = hyper or {}
        primary = hyper.get("primary") or {}
        entity_name = primary.get("entity_name") or primary.get("name") or task_query
        if primary:
            lines.append("### 主实体")
            lines.append(
                f"- {primary.get('entity_name') or entity_name}: "
                f"{primary.get('signature') or primary.get('summary') or ''}"
            )
        related = hyper.get("related") or []
        if related:
            lines.append("### 相关实体（超边扩展）")
            for item in related[:max_items]:
                lines.append(
                    f"- {item.get('entity_name') or item.get('name')}: "
                    f"{item.get('signature') or item.get('summary') or ''}"
                )
        # 依赖链：按 chain 中的实体类型逐级查询边关系
        for entity_type in chain:
            try:
                edges = self.get_edges(
                    entity_name,
                    edge_type=entity_type,
                    project_id=project_id,
                    limit=max_items,
                )
            except Exception:
                edges = []
            if edges:
                lines.append(f"### 依赖链: {entity_type}")
                for edge in edges[:max_items]:
                    lines.append(
                        f"- {edge.get('source_name') or entity_name} -> "
                        f"{edge.get('target_name') or ''}"
                    )
        text = "\n".join(lines)
        if max_chars and max_chars > 0:
            text = text[:max_chars]
        return text

    # ---- 组合渲染：build_chain -> render_semantic -> render_graph ----

    def build_chain(
        self,
        query: str,
        project_id: str = "default",
        limit: int = 10,
        chain: Optional[List[str]] = None,
        traverse_depth: int = 2,
    ) -> Dict[str, Any]:
        """构建依赖链数据：搜索 -> 关键词上下文 -> 边关系 -> 图遍历。

        在 inject_context 基础上，按 chain 中的实体类型逐级查询边关系，
        汇总为 chain_edges 存入返回的链式数据结构。
        """
        base = self.inject_context(
            query=query,
            project_id=project_id,
            limit=limit,
            traverse_depth=traverse_depth,
        )
        primary = base.get("primary") or {}
        entity_name = (
            primary.get("entity_name") or primary.get("name") or query
        )
        chain = chain or ["task", "plan", "hypothesis", "capability"]
        chain_edges: List[Dict[str, Any]] = []
        for entity_type in chain:
            try:
                edges = self.get_edges(
                    entity_name,
                    edge_type=entity_type,
                    project_id=project_id,
                    limit=limit,
                )
            except Exception:
                edges = []
            chain_edges.extend(edges)
        base["chain"] = chain
        base["chain_edges"] = chain_edges
        return base

    def render_semantic(self, chain_data: Dict[str, Any]) -> str:
        """将链式数据渲染为语义摘要文本（主实体 / 相关实体 / 关键词上下文）。"""
        lines: List[str] = []
        query = chain_data.get("query", "")
        primary = chain_data.get("primary") or {}
        if primary:
            name = primary.get("entity_name") or primary.get("name") or query
            sig = primary.get("signature") or primary.get("summary") or ""
            lines.append(f"- 主实体: {name}: {sig}")
        for item in chain_data.get("related") or []:
            name = item.get("entity_name") or item.get("name") or ""
            sig = item.get("signature") or item.get("summary") or ""
            lines.append(f"- 相关: {name}: {sig}")
        for item in chain_data.get("context") or []:
            if isinstance(item, dict):
                lines.append(f"- 上下文: {item}")
            else:
                lines.append(f"- 上下文: {item}")
        return "\n".join(lines) if lines else "(无语义内容)"

    def render_graph(self, chain_data: Dict[str, Any]) -> str:
        """将边关系与图遍历结果渲染为边列表（graph 文本表示）。"""
        lines: List[str] = []
        for edge in chain_data.get("edges") or []:
            lines.append(
                f"- {edge.get('source_name') or '?'} -> "
                f"{edge.get('target_name') or ''} "
                f"[{edge.get('edge_type') or 'edge'}]"
            )
        for edge in chain_data.get("chain_edges") or []:
            lines.append(
                f"- {edge.get('source_name') or '?'} -> "
                f"{edge.get('target_name') or ''} "
                f"[{edge.get('edge_type') or 'edge'}]"
            )
        for item in chain_data.get("traversed") or []:
            lines.append(
                f"- {item.get('source_name') or item.get('entity_name') or '?'} -> "
                f"{item.get('target_name') or ''}"
            )
        return "\n".join(lines) if lines else "(无图关系)"

    def render_injection(
        self,
        query: str,
        project_id: str = "default",
        limit: int = 10,
        chain: Optional[List[str]] = None,
        traverse_depth: int = 2,
        max_chars: int = 1500,
        include_graph: bool = True,
    ) -> str:
        """组合渲染注入：build_chain -> render_semantic -> render_graph。

        输出可直接拼入系统提示词的 markdown 风格文本，超出 max_chars 截断。
        """
        chain_data = self.build_chain(
            query=query,
            project_id=project_id,
            limit=limit,
            chain=chain,
            traverse_depth=traverse_depth,
        )
        semantic = self.render_semantic(chain_data)
        graph = self.render_graph(chain_data)
        text = f"## SAG 注入: {query}\n\n{semantic}\n\n{graph}"
        if max_chars and max_chars > 0:
            text = text[:max_chars]
        return text
