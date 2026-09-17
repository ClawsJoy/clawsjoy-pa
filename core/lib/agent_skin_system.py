#!/usr/bin/env python3
"""Agent Skin System - Agent Skin System 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""

from core.lib.unified_config import unified_config

"""Agent 皮肤和动画系统 - 商品化"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import yaml


class AgentSkinSystem:
    """Agent 皮肤系统 - 支持动画、特效、人物形象"""

    def __init__(self):
        self.skins_config = self._load_skins_config()
        self.animations_config = self._load_animations_config()

    def _load_skins_config(self) -> Dict:
        """加载皮肤配置"""
        config_file = Path("config/agent_skins.yaml")
        if config_file.exists():
            with open(config_file, "r") as f:
                return unified_config.get("agent_skins")
        return self._get_default_skins()

    def _load_animations_config(self) -> Dict:
        """加载动画配置"""
        config_file = Path("config/agent_animations.yaml")
        if config_file.exists():
            with open(config_file, "r") as f:
                return unified_config.get("agent_skins")
        return self._get_default_animations()

    def _get_default_skins(self) -> Dict:
        """默认皮肤配置"""
        return {
            "personal_butler": {
                "skins": {
                    "default": {
                        "name": "经典管家",
                        "avatar": "🤵",
                        "avatar_animated": "🤵‍♂️✨",
                        "color": "#00f3f",
                        "glow": "blue",
                        "background": "linear-gradient(135deg, #0a0a1a, #001a33)",
                        "price": "free",
                        "rarity": "common",
                    },
                    "maid": {
                        "name": "女仆管家",
                        "avatar": "👩‍🍳",
                        "avatar_animated": "💕👩‍🍳💕",
                        "color": "#ff69b4",
                        "glow": "pink",
                        "background": "linear-gradient(135deg, #1a0a1a, #331a33)",
                        "price": 4.99,
                        "rarity": "rare",
                        "effects": ["sparkle", "heart"],
                    },
                    "butler_premium": {
                        "name": "执事管家",
                        "avatar": "🕴️",
                        "avatar_animated": "✨🕴️✨",
                        "color": "#ffd700",
                        "glow": "golden",
                        "background": "linear-gradient(135deg, #1a1a0a, #33331a)",
                        "price": 9.99,
                        "rarity": "epic",
                        "effects": ["glow", "crown"],
                    },
                    "sci_fi": {
                        "name": "科幻管家",
                        "avatar": "🤖",
                        "avatar_animated": "⚡🤖⚡",
                        "color": "#b000f",
                        "glow": "purple",
                        "background": "linear-gradient(135deg, #0a0a2a, #1a0a3a)",
                        "price": 4.99,
                        "rarity": "rare",
                        "effects": ["scan_line", "hologram"],
                    },
                    "anime": {
                        "name": "动漫管家",
                        "avatar": "🎀",
                        "avatar_animated": "🌸🎀🌸",
                        "color": "#ff66cc",
                        "glow": "pink",
                        "background": "linear-gradient(135deg, #2a1a2a, #3a2a3a)",
                        "price": 6.99,
                        "rarity": "rare",
                        "effects": ["petal", "sparkle"],
                    },
                    "cyberpunk": {
                        "name": "赛博管家",
                        "avatar": "🦾",
                        "avatar_animated": "💀🦾💀",
                        "color": "#ff00f",
                        "glow": "neon",
                        "background": "linear-gradient(135deg, #0a0a0a, #1a0a2a)",
                        "price": 12.99,
                        "rarity": "legendary",
                        "effects": ["glitch", "scan_line", "grid"],
                    },
                    "fantasy": {
                        "name": "奇幻管家",
                        "avatar": "🧙",
                        "avatar_animated": "✨🧙✨",
                        "color": "#ffaa44",
                        "glow": "gold",
                        "background": "linear-gradient(135deg, #1a2a0a, #2a3a1a)",
                        "price": 7.99,
                        "rarity": "epic",
                        "effects": ["magic", "sparkle"],
                    },
                }
            },
            "code_agent": {
                "skins": {
                    "default": {
                        "name": "经典代码",
                        "avatar": "💻",
                        "avatar_animated": "⌨️💻⌨️",
                        "color": "#00ff88",
                        "price": "free",
                        "rarity": "common",
                    },
                    "hacker": {
                        "name": "黑客风格",
                        "avatar": "👾",
                        "avatar_animated": "🖥️👾🖥️",
                        "color": "#00ff00",
                        "glow": "green",
                        "price": 4.99,
                        "rarity": "rare",
                        "effects": ["matrix", "code_rain"],
                    },
                }
            },
            "translate_agent": {
                "skins": {
                    "default": {
                        "name": "经典翻译",
                        "avatar": "🔤",
                        "avatar_animated": "🌐🔤🌐",
                        "color": "#00f3f",
                        "price": "free",
                        "rarity": "common",
                    },
                    "scholar": {
                        "name": "学者风格",
                        "avatar": "📚",
                        "avatar_animated": "📖📚📖",
                        "color": "#8B4513",
                        "glow": "brown",
                        "price": 4.99,
                        "rarity": "rare",
                        "effects": ["book", "glow"],
                    },
                }
            },
        }

    def _get_default_animations(self) -> Dict:
        """默认动画配置"""
        return {
            "idle": {
                "name": "待机动画",
                "css": "pulse 2s ease-in-out infinite",
                "price": "free",
            },
            "glow": {
                "name": "发光特效",
                "css": "glow 1.5s ease-in-out infinite alternate",
                "price": 2.99,
            },
            "bounce": {
                "name": "弹跳动画",
                "css": "bounce 0.5s ease-in-out infinite",
                "price": 3.99,
            },
            "rotate": {
                "name": "旋转特效",
                "css": "rotate 3s linear infinite",
                "price": 2.99,
            },
            "float": {
                "name": "漂浮动画",
                "css": "float 2s ease-in-out infinite",
                "price": 4.99,
            },
            "sparkle": {
                "name": "星光闪烁",
                "css": "sparkle 1s ease-in-out infinite",
                "price": 5.99,
            },
        }

    def get_available_skins(self, agent_id: str) -> List[Dict]:
        """获取 Agent 可用皮肤"""
        agent_skins = self.skins_config.get(agent_id, {}).get("skins", {})
        return [
            {
                "id": skin_id,
                "name": info.get("name"),
                "avatar": info.get("avatar"),
                "avatar_animated": info.get("avatar_animated"),
                "color": info.get("color"),
                "glow": info.get("glow", "none"),
                "background": info.get("background"),
                "price": info.get("price"),
                "rarity": info.get("rarity", "common"),
                "effects": info.get("effects", []),
            }
            for skin_id, info in agent_skins.items()
        ]

    def get_skin_css(self, skin_id: str, agent_id: str = "personal_butler") -> str:
        """生成皮肤 CSS"""
        agent_skins = self.skins_config.get(agent_id, {}).get("skins", {})
        skin = agent_skins.get(skin_id, agent_skins.get("default", {}))

        css = f"""
        .agent-avatar {{
            font-size: 48px;
            color: {skin.get('color', '#00f3f')};
            text-shadow: 0 0 10px {skin.get('color', '#00f3f')};
            transition: all 0.3s ease;
        }}
        .agent-card {{
            background: {skin.get('background', 'linear-gradient(135deg, #0a0a1a, #001a33)')};
            border: 1px solid {skin.get('color', '#00f3f')};
            box-shadow: 0 0 20px {skin.get('color', '#00f3f')}40;
        }}
        """

        # 添加特效 CSS
        for effect in skin.get("effects", []):
            if effect == "sparkle":
                css += """
                @keyframes sparkle {
                    0%, 100% { text-shadow: 0 0 5px gold; }
                    50% { text-shadow: 0 0 20px gold, 0 0 30px orange; }
                }
                .sparkle { animation: sparkle 1s ease-in-out infinite; }
                """
            elif effect == "scan_line":
                css += """
                .scan-line {
                    position: absolute;
                    animation: scan 2s linear infinite;
                }
                @keyframes scan {
                    0% { transform: translateY(-100%); }
                    100% { transform: translateY(100%); }
                }
                """
            elif effect == "glitch":
                css += """
                @keyframes glitch {
                    0%, 100% { transform: skew(0deg, 0deg); }
                    20% { transform: skew(2deg, 1deg); text-shadow: -2px 0 red; }
                    40% { transform: skew(-2deg, -1deg); text-shadow: 2px 0 blue; }
                }
                .glitch { animation: glitch 0.3s ease-in-out infinite; }
                """

        return css

    def get_animation_css(self, animation_id: str) -> str:
        """获取动画 CSS"""
        anim = self.animations_config.get(
            animation_id, self.animations_config.get("idle", {})
        )

        css_map = {
            "pulse": """
            @keyframes pulse {
                0%, 100% { transform: scale(1); opacity: 1; }
                50% { transform: scale(1.05); opacity: 0.8; }
            }
            """,
            "glow": """
            @keyframes glow {
                0% { text-shadow: 0 0 5px cyan; }
                100% { text-shadow: 0 0 20px cyan, 0 0 30px blue; }
            }
            """,
            "bounce": """
            @keyframes bounce {
                0%, 100% { transform: translateY(0); }
                50% { transform: translateY(-10px); }
            }
            """,
            "float": """
            @keyframes float {
                0%, 100% { transform: translateY(0px); }
                50% { transform: translateY(-8px); }
            }
            """,
            "rotate": """
            @keyframes rotate {
                from { transform: rotate(0deg); }
                to { transform: rotate(360deg); }
            }
            """,
        }

        return css_map.get(anim.get("css", "").split()[0], "")


agent_skin_system = AgentSkinSystem()
