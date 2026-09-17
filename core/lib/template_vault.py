#!/usr/bin/env python3
"""Template Vault - Template Vault 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.config_helper import (
    get_data_root,
    get_embedding_model,
    get_gateway_port,
    get_llm_endpoint,
    get_llm_model,
    get_timeout,
)
from core.lib.unified_config import unified_config

"""模板库 - 人工审核入库，只作参考"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import yaml


class TemplateVault:
    """模板库 - 参考库，人工审核"""

    def __init__(self):
        self.vault_dir = Path(f"{get_data_root()}/template_vault")
        self.vault_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.vault_dir / "index.json"
        self._load_index()

    def _load_index(self):
        if self.index_file.exists():
            with open(self.index_file, "r") as f:
                self.index = json.load(f)
        else:
            self.index = {"templates": [], "review_queue": []}

    def _save_index(self):
        with open(self.index_file, "w") as f:
            json.dump(self.index, f, indent=2)

    def submit_for_review(
        self, name: str, code: str, category: str, submitter: str
    ) -> Dict:
        """提交模板供审核"""
        template_id = f"tmpl_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # 保存模板文件
        template_file = self.vault_dir / f"{template_id}.yaml"
        with open(template_file, "w") as f:
            yaml.dump(
                {
                    "id": template_id,
                    "name": name,
                    "code": code,
                    "category": category,
                    "submitter": submitter,
                    "submitted_at": datetime.now().isoformat(),
                },
                f,
            )

        # 加入审核队列
        self.index["review_queue"].append(
            {
                "id": template_id,
                "name": name,
                "category": category,
                "submitter": submitter,
                "submitted_at": datetime.now().isoformat(),
            }
        )
        self._save_index()

        return {
            "success": True,
            "template_id": template_id,
            "message": f"模板 [{name}] 已提交审核",
        }

    def review_approve(self, template_id: str, reviewer: str) -> Dict:
        """审核通过"""
        # 从审核队列移除
        for item in self.index["review_queue"]:
            if item["id"] == template_id:
                self.index["review_queue"].remove(item)

                # 加入正式模板库
                self.index["templates"].append(
                    {
                        **item,
                        "reviewer": reviewer,
                        "approved_at": datetime.now().isoformat(),
                    }
                )
                break

        self._save_index()

        return {"success": True, "message": f"模板已通过审核"}

    def review_reject(self, template_id: str, reason: str) -> Dict:
        """审核拒绝"""
        for item in self.index["review_queue"]:
            if item["id"] == template_id:
                self.index["review_queue"].remove(item)
                # 删除文件
                template_file = self.vault_dir / f"{template_id}.yaml"
                if template_file.exists():
                    template_file.unlink()
                break

        self._save_index()

        return {"success": True, "message": f"模板已拒绝，原因: {reason}"}

    def get_templates(self, category: str = None) -> List[Dict]:
        """获取参考模板列表"""
        templates = self.index["templates"]
        if category:
            templates = [t for t in templates if t.get("category") == category]
        return templates

    def get_review_queue(self) -> List[Dict]:
        """获取审核队列"""
        return self.index["review_queue"]


template_vault = TemplateVault()
