from typing import TypedDict

class Message(TypedDict):
    role: str 
    content: str

class ConversationMemory:
    def __init__(self) -> None:
        self._messages: list[Message] = []

    def add(self, role: str, content: str) -> None:
        self._messages.append({"role": role, "content": content})

    def get_all(self) -> list[Message]:
        return list(self._messages)

    def clear(self) -> None:
        self._messages.clear()

    def is_empty(self) -> bool:
        return len(self._messages) == 0

    def __len__(self) -> int:
        return len(self._messages)
