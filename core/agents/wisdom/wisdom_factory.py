#!/usr/bin/env python3
"""Agent 工厂 v5.0 - 统一Agent实例化 + 缓存

改动:
- 删除 WisdomWrapper 包装（AgentCortex 替代）
- 删除懒加载器依赖（简化）
- 保留 Agent 注册 + 缓存 + 热重载
- 新增 get_agent() 直接返回 agent_v4 实例
"""

import sys, os
sys.path.insert(0, os.path.expanduser('~/clawsjoy_robotics'))

from typing import Dict, Optional

from core.lib.agent_registry import agent_registry


class WisdomFactory:
    """Agent 工厂 - 实例化 + 缓存"""

    _instance = None
    _agent_cache: Dict[str, object] = {}

    # 完整的 Agent 注册表（模块路径 → 类名）
    AGENT_REGISTRY = {
        "chat_agent": ("agents.chat_agent.agent_v4", "ChatAgentV4"),
        "code_agent": ("agents.code_agent.agent_v4", "CodeAgentV4"),
        "analysis_agent": ("agents.analysis_agent.agent_v4", "AnalysisAgentV4"),
        "butler_agent": ("agents.butler_agent.agent_v4", "ButlerAgentV4"),
        "translate_agent": ("agents.translate_agent.agent_v4", "TranslateAgentV4"),
        "robotics_agent": ("robotics_agent", "RoboticsAgentV4"),
        "calculator_agent": ("agents.calculator_agent.agent_v4", "CalculatorAgentV4"),
        "decision_agent": ("agents.decision_agent.agent_v4", "DecisionAgentV4"),
        "vision_agent": ("agents.vision_agent.agent_v4", "VisionAgentV4"),
        "memory_agent": ("agents.memory_agent.agent_v4", "MemoryAgentV4"),
        "file_agent": ("agents.file_agent.agent_v4", "FileAgentV4"),
        "video_agent": ("agents.video_agent.agent_v4", "VideoAgentV4"),
        "youtube_agent": ("agents.youtube_agent.agent_v4", "YoutubeAgentV4"),
        "audio_agent": ("agents.audio_agent.agent_v4", "AudioAgentV4"),
        "dialect_agent": ("agents.dialect_agent.agent_v4", "DialectAgentV4"),
        "collaboration_agent": ("agents.collaboration_agent.agent_v4", "CollaborationAgentV4"),
        "writer_agent": ("agents.writer_agent.agent_v4", "WriterAgentV4"),
        "three_d_agent": ("agents.three_d_agent.agent_v4", "ThreeDAgentV4"),
        "video_indexer_agent": ("agents.video_indexer_agent.agent_v4", "VideoIndexerAgentV4"),
        "proactive_agent": ("agents.proactive_agent.agent_v4", "ProactiveAgentV4"),
        "director_agent": ("agents.director_agent.agent_v4", "DirectorAgentV4"),
        "comic_writer_agent": ("agents.comic_writer_agent.agent_v4", "ComicWriterAgentV4"),
        "executor_agent": ("agents.executor_agent.agent_v4", "ExecutorAgentV4"),
    }

    CAPABILITIES = {
        "chat_agent": ["聊天", "对话", "问答"],
        "code_agent": ["代码生成", "调试", "审查", "优化"],
        "analysis_agent": ["数据分析", "统计", "趋势", "报告"],
        "butler_agent": ["待办", "提醒", "日程管理"],
        "translate_agent": ["翻译", "多语言"],
        "calculator_agent": ["计算", "数学"],
        "decision_agent": ["决策", "路由", "评估"],
        "vision_agent": ["图像生成", "图像分析"],
        "memory_agent": ["记忆存储", "记忆回忆", "记忆管理"],
        "file_agent": ["文件读写", "文件管理"],
        "video_agent": ["视频制作", "视频剪辑"],
        "youtube_agent": ["YouTube管理", "频道分析"],
        "audio_agent": ["音频处理", "语音合成"],
        "dialect_agent": ["方言学习", "方言翻译"],
        "collaboration_agent": ["多Agent协作", "任务分配"],
        "writer_agent": ["写作", "创作", "润色"],
        "three_d_agent": ["3D内容生成"],
        "video_indexer_agent": ["视频索引", "视频分析"],
        "proactive_agent": ["主动建议", "主动服务"],
        "director_agent": ["导演模式", "拍摄计划"],
        "comic_writer_agent": ["漫画创作", "漫画脚本"],
        "executor_agent": ["任务执行", "工作流执行"],
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    # 预热配置
    WARM_POOL = {
        "chat_agent": 2,
        "code_agent": 1,
        "memory_agent": 1,
        "calculator_agent": 1,
        "translate_agent": 1,
        "writer_agent": 1,
    }

    def _init(self):
        print("🧠 WisdomFactory v5.0 初始化")
        self._sync_to_registry()
        self._warmup()

    def _sync_to_registry(self):
        """同步 Agent 到注册中心"""
        for agent_name in self.AGENT_REGISTRY:
            if agent_name not in agent_registry.agents:
                agent_registry.register(agent_name, {
                    "name": agent_name,
                    "type": "v5",
                    "version": "5.0.0",
                    "description": f"Agent {agent_name}",
                    "capabilities": self.CAPABILITIES.get(agent_name, []),
                    "status": "active"
                })
        print(f"  📋 同步 {len(self.AGENT_REGISTRY)} 个Agent到注册中心")

    def _warmup(self):
        """后台预热高频Agent"""
        import threading
        def _do_warmup():
            print("🔥 Agent预热中...")
            for agent_name, count in self.WARM_POOL.items():
                for _ in range(count):
                    try:
                        self.get_agent(agent_name, "pool")
                    except:
                        pass
            print(f"✅ Agent预热完成")
        threading.Thread(target=_do_warmup, daemon=True).start()

    # ====================================================================
    #  获取Agent（唯一入口）
    # ====================================================================

    def get_agent(self, agent_name: str, user_id: str = "default"):
        """获取Agent实例（带缓存）

        AgentCortex 和所有需要直接调Agent的地方走这里。
        """
        cache_key = f"{agent_name}:{user_id}"
        if cache_key in self._agent_cache:
            return self._agent_cache[cache_key]
        print(f"[DEBUG] get_agent 创建新实例: {cache_key}")  # 加这行
        agent = self._instantiate(agent_name, user_id)
        if agent:
            self._agent_cache[cache_key] = agent
        return agent

    # 兼容旧接口名
    def get_wisdom_agent(self, agent_name: str, user_id: str = "default"):
        """[兼容] 等同 get_agent()"""
        return self.get_agent(agent_name, user_id)

    # ====================================================================
    #  实例化
    # ====================================================================

    def _instantiate(self, agent_name: str, user_id: str):
        """实例化Agent"""
        if agent_name not in self.AGENT_REGISTRY:
            # 尝试动态发现
            agent = self._dynamic_import(agent_name, user_id)
            if agent:
                return agent
            print(f"❌ Agent未注册: {agent_name}")
            return None

        module_path, class_name = self.AGENT_REGISTRY[agent_name]
        try:
            module = __import__(module_path, fromlist=[class_name])
            agent_class = getattr(module, class_name)
            return agent_class(user_id)
        except Exception as e:
            print(f"❌ 实例化 {agent_name} 失败: {e}")
            return None

    def _dynamic_import(self, agent_name: str, user_id: str):
        """动态导入（兜底）"""
        try:
            mod = __import__(f"agents.{agent_name}.agent_v4", fromlist=["*"])
            for attr in dir(mod):
                if attr.endswith("V4") and hasattr(getattr(mod, attr), 'process'):
                    return getattr(mod, attr)(user_id)
        except ImportError:
            pass
        return None

    # ====================================================================
    #  管理
    # ====================================================================

    def reload_agent(self, agent_name: str, user_id: str = "default"):
        """热重载"""
        cache_key = f"{agent_name}:{user_id}"
        self._agent_cache.pop(cache_key, None)
        self._agent_cache.pop(agent_name, None)
        print(f"🔄 热重载: {agent_name}")
        return True

    def clear_cache(self):
        """清除所有缓存"""
        self._agent_cache.clear()

    def list_agents(self) -> list:
        return list(self.AGENT_REGISTRY.keys())

    def get_agent_class(self, agent_name: str):
        """获取Agent类（不实例化）"""
        if agent_name not in self.AGENT_REGISTRY:
            return None
        module_path, class_name = self.AGENT_REGISTRY[agent_name]
        try:
            module = __import__(module_path, fromlist=[class_name])
            return getattr(module, class_name)
        except Exception:
            return None

    # ====================================================================
    #  统计
    # ====================================================================

    def get_stats(self) -> Dict:
        return {
            "total_registered": len(self.AGENT_REGISTRY),
            "cached_instances": len(self._agent_cache),
            "registry_stats": agent_registry.get_stats(),
        }

    def get_all_wisdom_stats(self) -> Dict:
        """[兼容]"""
        return self.get_stats()


# 全局单例
wisdom_factory = WisdomFactory()
