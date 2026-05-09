# 抽象基类，定义扩展接口
from abc import ABC, abstractmethod
from .memory import ConversationMemory


class BaseAgent(ABC):
    """
    Agent 抽象基类，定义所有版本 Agent 必须实现的接口。

    扩展方式：
      阶段1（当前）： ChatAgent(BaseAgent)          简单对话交互
      阶段2：        CourseAwareAgent(BaseAgent)   + 数据库查询
      阶段3：        RAGAgent(BaseAgent)            + 向量检索
      阶段4：        FullAgent(BaseAgent)           完整版

    方便后续对模型进行扩展和迭代
    """

    def __init__(self) -> None:
        # 所有子类共享同一套记忆管理
        self.memory = ConversationMemory()

    @abstractmethod
    def chat(self, user_input: str) -> str:
        """
        处理用户输入，返回回复字符串。
        这是每个子类必须实现的核心方法。
        """
        ...

    @abstractmethod
    def _build_response(self, user_input: str) -> str:
        """
        内部方法：实际生成回复的逻辑。
        chat() 负责流程控制，_build_response() 负责生成内容，两者分离。

        阶段1：直接调用 llm API
        阶段2：先判断意图，再选择数据库查询或 llm API
        阶段3：在阶段2基础上加入向量检索
        """
        ...

    def reset(self) -> None:
        """清空对话历史。所有子类通用，无需重写。"""
        self.memory.clear()
        print("[提示] 对话历史已清空，开始新对话。")

    def get_history_length(self) -> int:
        """返回当前对话轮数，调试时用。"""
        return len(self.memory) // 2  # 每轮 = 1条user + 1条assistant