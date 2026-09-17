#!/usr/bin/env python3
"""Constants - Constants 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

"""项目常量 - 配置驱动"""

from pathlib import Path

# 项目根目录（直接定义，不导入其他模块）
PROJECT_ROOT = Path(__file__).parent.parent

# 常用路径
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"
SKILLS_DIR = PROJECT_ROOT / "skills"
CONFIG_DIR = PROJECT_ROOT / "config"
TEMPLATES_DIR = PROJECT_ROOT / "templates"
WEB_DIR = PROJECT_ROOT / "web"

# 确保目录存在
for d in [DATA_DIR, LOGS_DIR, SKILLS_DIR, CONFIG_DIR]:
    d.mkdir(parents=True, exist_ok=True)
