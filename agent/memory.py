# 对话历史管理
from typing import TypedDict


class Message(TypedDict):
    """单条消息的数据结构，与 Anthropic API 格式保持一致。"""
    role: str 
    content: str


class ConversationMemory:
    """
    管理多轮对话的历史记录。

    当前阶段：保留全部历史（适合短对话演示）。
    后续可在这里扩展：
      - 超过 N 轮后裁剪最早的消息（滑动窗口）
      - 按 token 数量控制历史长度，避免超出 API 限制
      - 持久化到本地文件，下次启动可恢复上下文
    """

    def __init__(self) -> None:
        self._messages: list[Message] = []

    def add(self, role: str, content: str) -> None:
        """追加一条消息到历史。"""
        self._messages.append({"role": role, "content": content})

    def get_all(self) -> list[Message]:
        """获取完整历史（传给 API 时使用）。"""
        return list(self._messages)

    def clear(self) -> None:
        """清空历史，开始新对话。"""
        self._messages.clear()

    def is_empty(self) -> bool:
        return len(self._messages) == 0

    def __len__(self) -> int:
        return len(self._messages)