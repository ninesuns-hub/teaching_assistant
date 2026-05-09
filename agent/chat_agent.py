from openai import OpenAI
from config import OPENAI_API_KEY, OPENAI_BASE_URL, MODEL_NAME, MAX_TOKENS, SYSTEM_PROMPT
from .base_agent import BaseAgent
from agent.classifier import (
    classify,
    INTENT_ADMIN, INTENT_CONTENT, INTENT_KNOWLEDGE, INTENT_IRRELEVANT,
)
from database.course_db import query_course_admin, init_db
from database.vector_store import query as vector_query


class ChatAgent(BaseAgent):
    """
    功能：
      - 多轮对话（携带完整历史）
      - 扮演离散数学助教角色（由 SYSTEM_PROMPT 控制）
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
        # 启动时初始化 SQLite（第一次运行自动建表+示例数据）
        init_db()

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

        # 只有正常回复才记入历史，拒绝回复不记，避免污染上下文
        if reply:
            self.memory.add("user", user_input)
            self.memory.add("assistant", reply)

        return reply

    def _build_response(self, user_input: str) -> str:
        """
        支持多意图，分别处理后合并回复。

        四条路径：
          admin      → _handle_admin()      查 SQLite
          content    → _handle_content()    查 ChromaDB + 大模型组织回答
          knowledge  → _handle_knowledge()  直接调大模型
          irrelevant → _handle_irrelevant() 礼貌拒绝
        """
        
        intent_raw = classify(user_input)

        # 支持多意图，如 "admin,knowledge"
        intents = [i.strip() for i in intent_raw.split(",")]

        replies = []

        for intent in intents:
            if intent == INTENT_ADMIN:
                replies.append(self._handle_admin(user_input))
            elif intent == INTENT_CONTENT:
                replies.append(self._handle_content(user_input))
            elif intent == INTENT_KNOWLEDGE:
                replies.append(self._handle_knowledge(user_input))
            elif intent == INTENT_IRRELEVANT:
                # 只有在单独 irrelevant 时才拒绝
                if len(intents) == 1:
                    replies.append(self._handle_irrelevant(user_input))

        if not replies:
            return self._handle_irrelevant(user_input)

        #多条回复用分隔线合并
        return "\n\n".join(replies)
        
    def _handle_admin(self, user_input: str) -> str:
        """
        课程事务类：查 SQLite，找到直接返回精确答案。
        查不到时礼貌说明，不乱猜。
        """
        result = query_course_admin(user_input)
        if result:
            return f"【课程信息】\n{result}"
        else:
            return (
                "抱歉，我暂时没有找到关于这个问题的确切信息。\n"
                "建议直接联系老师或查看教务系统获取最新通知。\n\n"
                "老师邮箱：kejiwei@tongji.edu.cn"
            )

    def _handle_content(self, user_input: str) -> str:
        """
        教学内容类：先检索 ChromaDB 找相关课件片段，
        再把检索结果交给大模型组织成自然语言回答。
        """
        # 从向量库检索相关片段
        results = vector_query(user_input)
        SIMILARITY_THRESHOLD = 0.3
        
        # 过滤掉相似度过低的结果
        results = [r for r in results if r["similarity"] >= SIMILARITY_THRESHOLD]

        if not results:
            # 检索不到相关内容，明确告知而不是让大模型自由发挥
            return (
                "在课件和讲义中未找到与该问题直接相关的内容。\n\n"
                "• 尝试换个关键词描述你的问题\n\n"
                "如果你想了解这个知识点的一般解释，可以直接问我，"
                "我会根据离散数学的通用知识来回答。"
            )

        # 构建参考资料，标注来源和页码
        context_parts = []
        for r in results:
            source_label = (
                f"【来源：{r['source_file']} "
                f"第{r['page']}页 | "
                f"相关度：{r['similarity']}】"
            )
            context_parts.append(f"{source_label}\n{r['text']}")
        context = "\n\n".join(context_parts)

        prompt = f"""以下是从课件和讲义中检索到的相关内容：

    {context}

    ---

    请根据以上课程材料，回答学生的问题：{user_input}

    严格要求：
    1. 只使用上方检索到的内容作答，不要补充材料中没有的内容
    2. 如果材料中有例题编号（如"例1.1"、"Example 1"），请直接引用
    3. 在回答末尾注明参考来源：文件名 + 第几页
    4. 如果检索到的内容不足以完整回答问题，明确说明"课件中仅提供了部分内容"
    """
        return self._call_llm(prompt)

    def _handle_knowledge(self, user_input: str) -> str:
        """
        通用知识点类：直接调用大模型，携带对话历史保持上下文。
        """
        messages = (
            [{"role": "system", "content": SYSTEM_PROMPT}]
            + self.memory.get_all()
            + [{"role": "user", "content": user_input}]
        )
        return self._call_llm_with_messages(messages)

    def _handle_irrelevant(self, user_input: str) -> str:
        """
        无关话题：礼貌拒绝，引导回课程话题。
        """
        return (
            "这个问题好像超出了离散数学课程的范围，我可能帮不上忙～\n\n"
            "我擅长回答以下类型的问题：\n"
            "  • 课程安排（考试时间、作业截止日期、评分规则等）\n"
            "  • 课件和讲义内容（例题、定义、定理等）\n"
            "  • 离散数学知识点（集合论、图论、命题逻辑等）\n\n"
            "有这方面的问题欢迎随时问我！"
        )

    # ── 底层 LLM 调用 ─────────────────────────────────────────

    def _call_llm(self, user_prompt: str) -> str:
        """
        单轮调用大模型（不带历史），用于 RAG 场景。
        RAG 已经把上下文塞进 prompt 里了，不需要历史。
        """
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_prompt},
        ]
        return self._call_llm_with_messages(messages)

    def _call_llm_with_messages(self, messages: list[dict]) -> str:
        """底层 API 调用，所有需要调大模型的路径最终都走这里。"""
        response = self._client.chat.completions.create(
            model=MODEL_NAME,
            max_tokens=MAX_TOKENS,
            messages=messages,
        )
        return response.choices[0].message.content