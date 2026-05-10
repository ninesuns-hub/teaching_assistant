from abc import ABC, abstractmethod
from .memory import ConversationMemory

class BaseAgent(ABC):
    def __init__(self) -> None:
        self.memory = ConversationMemory()

    @abstractmethod
    def chat(self, user_input: str) -> str:
        pass

    @abstractmethod
    def _build_response(self, user_input: str) -> str:
        pass

    def reset(self) -> None:
        self.memory.clear()

    def get_history_length(self) -> int:
        return len(self.memory) // 2
