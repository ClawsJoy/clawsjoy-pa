#!/usr/bin/env python3
"""Workflow Vectorizer - Workflow Vectorizer 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


from pathlib import Path

import yaml

from core.lib.unified_config import unified_config
from core.tenant.tenant_vector_index import tenant_index_manager


class WorkflowVectorizer:
    """工作流语义推荐器"""

    def __init__(self):
        self._initialized = False

    def init_tenant_workflows(self, tenant_id: str = "default"):
        """初始化租户工作流向量索引"""
        if self._initialized:
            return

        index = tenant_index_manager.get_index(tenant_id)

        # 加载工作流配置
        workflow_file = Path("config/workflows.yaml")
        if not workflow_file.exists():
            print("   ⚠️ 未找到工作流配置")
            return

        with open(workflow_file, "r") as f:
            config = yaml.safe_load(f)

        workflows = config.get("workflows", [])
        indexed = 0
        for wf in workflows:
            wf_id = wf.get("id", "")
            name = wf.get("name", "")
            description = wf.get("description", "")
            steps = wf.get("steps", [])

            text = f"{name}: {description} 步骤: {','.join(steps)}"

            index.index_workflow(
                wf_id, name, text, {"workflow_id": wf_id, "name": name, "steps": steps}
            )
            indexed += 1

        print(f"   🔄 已索引 {indexed} 个工作流")
        self._initialized = True

    def recommend_workflow(self, tenant_id: str, intent: str, n: int = 3):
        """根据意图推荐工作流"""
        index = tenant_index_manager.get_index(tenant_id)
        return index.search_workflow(intent, n)


workflow_vectorizer = WorkflowVectorizer()
