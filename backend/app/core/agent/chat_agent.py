from openai import OpenAI
from app.config.settings import settings
from .base_agent import BaseAgent
from .classifier import (
    classify,
    INTENT_ADMIN, INTENT_CONTENT, INTENT_KNOWLEDGE, INTENT_IRRELEVANT,
)
from app.infrastructure.database.course_repo import query_course_admin, init_db
from app.infrastructure.database.vector_repo import query as vector_query

class ChatAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__()
        self._client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
        )
        init_db()

    def chat(self, user_input: str) -> str:
        user_input = user_input.strip()
        if not user_input:
            return "请输入你的问题～"

        reply = self._build_response(user_input)
        if reply:
            self.memory.add("user", user_input)
            self.memory.add("assistant", reply)
        return reply

    def _build_response(self, user_input: str) -> str:
        intent = classify(user_input)
        
        if intent == INTENT_ADMIN:
            return self._handle_admin(user_input)
        elif intent == INTENT_CONTENT:
            return self._handle_content(user_input)
        elif intent == INTENT_KNOWLEDGE:
            return self._handle_knowledge(user_input)
        else:
            return self._handle_irrelevant(user_input)

    def _handle_admin(self, user_input: str) -> str:
        result = query_course_admin(user_input)
        if result:
            return f"【课程信息】\n{result}"
        return "抱歉，我暂时没有找到关于这个问题的确切信息。建议直接联系老师：kejiwei@tongji.edu.cn"

    def _handle_content(self, user_input: str) -> str:
        results = vector_query(user_input)
        results = [r for r in results if r["similarity"] >= settings.SIMILARITY_THRESHOLD]

        if not results:
            return "在课件和讲义中未找到直接相关内容。你可以换个关键词，或者直接问我通用知识。"

        context = "\n\n".join([f"【来源：{r['source_file']} 第{r['page']}页】\n{r['text']}" for r in results])
        prompt = f"请根据以下课程材料回答问题：{user_input}\n\n材料：\n{context}"
        return self._call_llm(prompt)

    def _handle_knowledge(self, user_input: str) -> str:
        messages = (
            [{"role": "system", "content": settings.SYSTEM_PROMPT}]
            + self.memory.get_all()
            + [{"role": "user", "content": user_input}]
        )
        return self._call_llm_with_messages(messages)

    def _handle_irrelevant(self, user_input: str) -> str:
        return "这个问题好像超出了离散数学课程的范围。我擅长回答课程安排、课件内容和离散数学知识点。"

    def _call_llm(self, user_prompt: str) -> str:
        messages = [
            {"role": "system", "content": settings.SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
        return self._call_llm_with_messages(messages)

    def _call_llm_with_messages(self, messages: list[dict]) -> str:
        response = self._client.chat.completions.create(
            model=settings.MODEL_NAME,
            max_tokens=settings.MAX_TOKENS,
            messages=messages,
        )
        return response.choices[0].message.content
