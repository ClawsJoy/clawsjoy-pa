#!/usr/bin/env python3
"""项目依赖图可视化"""

from core.lib.project_graph import ProjectGraph
import json
from pathlib import Path


def generate_dependency_html(project_id: str, user_id: str = "codex_user") -> str:
    """生成依赖图 HTML"""
    try:
        from core.lib.code_repo import get_code_repo
        repo = get_code_repo(user_id)
        project = repo.get_project(project_id)
        if not project:
            return "<p>项目不存在</p>"
        
        graph = ProjectGraph(project["path"])
        
        # 构建节点和边
        nodes = []
        edges = []
        for file, deps in graph.graph.items():
            nodes.append({"id": file, "label": file.split('/')[-1]})
            for dep in deps:
                if dep in graph.graph:
                    edges.append({"from": file, "to": dep})
        
        # 生成 HTML
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>项目依赖图 - {project['name']}</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.2/vis-network.min.js"></script>
    <style>
        body {{ margin: 0; background: #1e1e2e; }}
        #network {{ width: 100%; height: 100vh; }}
        .stats {{ position: fixed; top: 20px; right: 20px; background: rgba(0,0,0,0.8); padding: 16px; border-radius: 8px; color: #cdd6f4; z-index: 100; }}
    </style>
</head>
<body>
    <div class="stats">
        <div>📁 文件: {len(nodes)}</div>
        <div>🔗 依赖: {len(edges)}</div>
        <div>📊 复杂度: {len(edges) / max(1, len(nodes)):.2f}</div>
    </div>
    <div id="network"></div>
    <script>
        var nodes = new vis.DataSet({nodes});
        var edges = new vis.DataSet({edges});
        var container = document.getElementById('network');
        var data = {{ nodes: nodes, edges: edges }};
        var options = {{
            physics: {{ enabled: true }},
            layout: {{ hierarchical: {{ enabled: false }}}},
            nodes: {{ shape: 'dot', size: 10, font: {{ color: '#cdd6f4', size: 12 }}}},
            edges: {{ arrows: 'to', color: {{ color: '#6c7086' }}}}
        }};
        var network = new vis.Network(container, data, options);
    </script>
</body>
</html>
"""
        return html
    except Exception as e:
        return f"<p>生成失败: {e}</p>"
