#!/usr/bin/env python3
"""Config Helper - Config Helper 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


import os
from pathlib import Path

from core.lib.unified_config import unified_config

# 仓根之「一处定形」（承规七 · pm_1698 三.1a）：get_data_root() 之**相对值** ⇒ 按**仓根**拼。
# 由：昔返 config 之字面 data（相对径）⇒ 消费者 Path(get_data_root()) / "vector_kb"
#   按 **CWD** 解 ⇒「异 cwd ⇒ 异仓」（态漂）—— 2026-10-07 一手之显形：CW 之面齿在沙箱
#   CWD 下竟写 D:/clawsjoy_v9/data/**（＝规七之第四次）。
REPO_ROOT = Path(__file__).resolve().parents[2]

#: env 之覆（供齿 ／ 沙箱 ／ 试）—— 名与 core/lib/platform_client.py:15 **同源**（一举一义）。
DATA_ROOT_ENV = "CLAWSJOY_DATA_DIR"

#: ⭐ 9.0.13 P0：向量库根之 env（与 scripts/win_pa/pa_paths.py:ENV_VEC **同源** · 一处定形）。
#:   装 Program Files 只读 ⇒ chroma 库 ⛔ 落装根；PA_VEC_DIR ＝ 库目录本身
#:   （缺省 %LOCALAPPDATA%\ClawsJoyPA\vec —— 由 scripts/win_pa/pa_paths.py 注入）。
VECTOR_ROOT_ENV = "PA_VEC_DIR"


def get_data_root() -> str:
    """获取数据根目录（**绝对径** · 与「根」绑定 · 不按 CWD —— 承规七 · pm_1698 三.1a）。

    之序：① env CLAWSJOY_DATA_DIR（覆）⇒ ② 配置 paths.data_root（默认 data）。
    **相对值** ⇒ 按**仓根**（core/lib/config_helper.py 之 parents[2]）拼 ⇒ 恒**绝对径**
    （不按 CWD —— 否则「异 cwd ⇒ 异仓」）。
    """
    raw = (os.environ.get(DATA_ROOT_ENV) or "").strip() or \
        str(unified_config.get("paths.data_root", "data") or "").strip()
    if not raw:
        raw = "data"
    p = Path(str(raw))
    return str(p if p.is_absolute() else (REPO_ROOT / p))


def get_vector_root() -> str:
    """向量库根目录（**绝对径** · ⭐ 9.0.13 P0：装根只读 ⇒ 库 ⛔ 落装根）。

    之序：① env PA_VEC_DIR（＝ 库目录本身；缺省 %LOCALAPPDATA%\\ClawsJoyPA\\vec）
    ⇒ ② 旧形 <get_data_root()>/vector_kb（向后兼容；缺 env 之开发树沿用）。
    **相对值** ⇒ 按**仓根**拼（与 get_data_root 同律 —— ⛔ 按 CWD）。
    """
    raw = (os.environ.get(VECTOR_ROOT_ENV) or "").strip()
    if raw:
        p = Path(str(raw))
        return str(p if p.is_absolute() else (REPO_ROOT / p))
    return str(Path(get_data_root()) / "vector_kb")


def get_llm_endpoint() -> str:
    """获取 LLM 端点"""
    return unified_config.get("llm.endpoint", "http://localhost:11434")


def get_llm_model(fast: bool = False) -> str:
    """获取 LLM 模型"""
    if fast:
        return unified_config.get("llm.fast_model", "qwen2.5:3b")
    return unified_config.get("llm.default_model", "qwen2.5:7b")


def get_embedding_model() -> str:
    """获取 Embedding 模型"""
    return unified_config.get("vector.embedding_model", "nomic-embed-text")


def get_gateway_port() -> int:
    """获取网关端口"""
    return unified_config.get("services.gateway.port", 5002)


def get_timeout(name: str = "default") -> int:
    """获取超时配置"""
    return unified_config.get(f"timeouts.{name}", 30)


def get_tenant_base_path() -> str:
    """获取租户基础路径"""
    return unified_config.get("tenant.base_path", "data/tenants")


def get_vector_config() -> dict:
    """获取向量配置"""
    return unified_config.get("vector", {})
