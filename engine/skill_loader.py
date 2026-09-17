#!/usr/bin/env python3
"""原子引擎技能加载器 - 基于 skill_loader_v3"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 直接复用原有的 skill_loader_v3
from core.lib.skill_loader_v3 import SkillLoaderV3, skill_loader

# 导出
__all__ = ["SkillLoaderV3", "skill_loader"]
