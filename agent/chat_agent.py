# 当前阶段（简单对话交互agent）的具体实现
from openai import OpenAI
from config import OPENAI_API_KEY, OPENAI_BASE_URL, MODEL_NAME, MAX_TOKENS, SYSTEM_PROMPT
from .base_agent import BaseAgent


class ChatAgent(BaseAgent):
    """
    阶段1：纯对话 Agent。

    功能：
      - 多轮对话（携带完整历史）
      - 扮演离散数学助教角色（由 SYSTEM_PROMPT 控制）

    待扩展：
      - 意图分类
      - 课程数据库查询
      - 向量检索
    """

    def __init__(self) -> None:
        super().__init__()  # 初始化 memory
        self._client = OpenAI(
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_BASE_URL,   # 指向 AIHubMix 的接口地址
        )
        self._validate_config()

    def _validate_config(self) -> None:
        """启动时检查配置是否齐全，提前暴露问题。"""
        if not OPENAI_API_KEY:
            raise ValueError(
                "未找到 OPENAI_API_KEY。\n"
                "请在项目根目录创建 .env 文件，写入：\n"
                "OPENAI_API_KEY=你的AIHubMix密钥\n"
                "OPENAI_BASE_URL=https://aihubmix.com/v1"
            )


    def chat(self, user_input: str) -> str:
        """
        处理一轮对话的完整流程：
          1. 生成回复
          2. 将本轮记入历史
          3. 返回回复文本
        """
        user_input = user_input.strip()
        if not user_input:
            return "请输入你的问题～"

        # 生成回复（子类各自实现不同的生成逻辑）
        reply = self._build_response(user_input)

        # 生成成功后才写入历史，避免报错时存入半条记录
        self.memory.add("user", user_input)
        self.memory.add("assistant", reply)

        return reply

    # ── 内部实现 ──────────────────────────────────────────────
    def _build_response(self, user_input: str) -> str:
        """
        调用 llm API，带上完整对话历史，生成回复。

        阶段2扩展点：在这里调用之前，先做意图判断，
        如果是课程类问题则调用数据库，否则走这里的 API 调用。
        """
        # 构建本次发送给 API 的消息列表：历史 + 当前问题
        messages = (
            [{"role": "system", "content": SYSTEM_PROMPT}]
            + self.memory.get_all()
            + [{"role": "user", "content": user_input}]
        )

        response = self._client.chat.completions.create(
            model=MODEL_NAME,
            max_tokens=MAX_TOKENS,
            messages=messages,
        )

        return response.choices[0].message.content