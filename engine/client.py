"""原子引擎统一客户端"""

from engine.active import active_engine
from engine.knowledge import knowledge_engine
from engine.memory import memory_engine
from engine.profile import profile_engine
from engine.reasoning import reasoning_engine
from engine.semantic import semantic_engine


class EngineClient:
    """统一引擎客户端"""

    @property
    def semantic(self):
        return semantic_engine

    @property
    def profile(self):
        return profile_engine

    @property
    def memory(self):
        return memory_engine

    @property
    def active(self):
        return active_engine

    @property
    def knowledge(self):
        return knowledge_engine

    @property
    def reasoning(self):
        return reasoning_engine


engine = EngineClient()
