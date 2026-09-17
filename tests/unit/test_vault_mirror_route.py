# -*- coding: utf-8 -*-
"""Q1 测试: data/vault 镜像不存在 → 引导 obsidian_knowledge(不触发审批)"""
import sys

sys.path.insert(0, ".")


def test_vault_mirror_redirect_in_guard():
    src = open("core/gateway/guards/registry.py", encoding="utf-8").read()
    assert 'startswith(("data/vault", "vault/"))' in src, "读工具应识别 vault 镜像路径"
    assert "Obsidian 第二大脑没有沙箱镜像" in src, "应给 obsidian_knowledge 引导文案"
    # 引导发生在审批/越权之前(同分支内先于 _is_read_path_escape)
    assert src.index("_vault_mirror =") < src.index("_is_read_path_escape(sandbox_base, _rpath)"), "应先于越权判定"


def test_vault_guidance_in_agent_system():
    src = open("config/prompts/agent_system.md", encoding="utf-8").read()
    assert "data/vault 镜像" in src or "无 data/vault 镜像" in src or "data/vault/" in src
    assert "obsidian_knowledge" in src
