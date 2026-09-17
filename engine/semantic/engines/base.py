"""引擎基类"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Tuple


class BaseEngine(ABC):
    """语义理解引擎基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def priority(self) -> int:
        pass

    @abstractmethod
    def understand(self, text: str) -> Tuple[str, float, Dict]:
        pass

    def reload(self) -> None:
        pass

    def is_available(self) -> bool:
        return True

    def get_capabilities(self) -> Dict:
        return {"name": self.name, "priority": self.priority}
