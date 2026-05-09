import json
from openai import OpenAI
from config import OPENAI_API_KEY, OPENAI_BASE_URL, MODEL_NAME

INTENT_ADMIN      = "admin"       # 课程事务类 → 查 SQLite
INTENT_CONTENT    = "content"     # 教学内容类 → 查 ChromaDB
INTENT_KNOWLEDGE  = "knowledge"   # 通用知识点类 → 调用大模型
INTENT_IRRELEVANT = "irrelevant"  # 无关话题 → 礼貌拒绝

# 分类提示词
_CLASSIFY_PROMPT = """你是一个意图分类器，负责判断学生问题属于哪一类。

四种类别定义：
1. admin：课程事务类
   - 考试安排（时间、地点、规定）
   - 作业相关（截止日期、提交方式）
   - 成绩评分（占比、构成）
   - 上课信息（时间、地点、教室）
   - 答疑信息（时间、地点、办公室）
   - 老师信息（联系方式、邮箱）
   - 课程规定（课堂政策、学习建议）
   - 参考书目、课程网站

2. content：教学内容类
   - 询问课件、讲义、PPT 中的具体内容
   - 询问课堂例题、习题
   - 询问某章节讲了什么

3. knowledge：通用知识点类
   - 离散数学概念解释（集合、图论、逻辑等）
   - 定理证明、公式推导
   - 解题方法、计算过程
   - 不依赖课件就能回答的数学问题

4. irrelevant：与课程完全无关的话题

要求：
- 只返回 JSON，不要任何其他文字
- 问题只涉及一种意图时：{"intent": "admin"}
- 问题同时涉及多种意图时，按优先级列出：{"intent": "admin,knowledge"}
- 意图优先级：admin > content > knowledge > irrelevant
"""


def classify(question: str) -> str:
    """
    用大模型对问题做意图分类，返回四种意图常量之一。
    如果大模型调用失败，自动降级为关键词兜底匹配。
    """
    try:
        return _classify_by_llm(question)
    except Exception as e:
        print(f"[分类器] 大模型分类失败，降级为关键词匹配：{e}")
        return _classify_by_keywords(question)


def _classify_by_llm(question: str) -> str:
    """调用大模型做分类，解析返回的 JSON 得到意图。"""
    client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)

    response = client.chat.completions.create(
        model=MODEL_NAME,
        max_tokens=80,  
        temperature=0,          # 温度设为 0，让分类结果更稳定、不随机
        messages=[
            {"role": "system", "content": _CLASSIFY_PROMPT},
            {"role": "user",   "content": f"请对以下问题分类：{question}"},
        ],
    )

    raw = response.choices[0].message.content.strip()

    # 解析 JSON，提取 intent 字段
    result = json.loads(raw)
    intent = result.get("intent", "").strip()

    # 校验返回值是否合法
    valid = {INTENT_ADMIN, INTENT_CONTENT, INTENT_KNOWLEDGE, INTENT_IRRELEVANT}
    if intent not in valid:
        print(f"[分类器] 大模型返回了未知意图 '{intent}'，降级为关键词匹配")
        return _classify_by_keywords(question)

    print(f"[分类器] '{question[:20]}...' → {intent}")
    return intent


def _classify_by_keywords(question: str) -> str:
    """
    关键词兜底匹配，仅在大模型分类失败时使用。
    保留这个函数是为了保证网络异常时系统仍然可用。
    """
    from config import COURSE_ADMIN_KEYWORDS, COURSE_CONTENT_KEYWORDS

    for kw in COURSE_ADMIN_KEYWORDS:
        if kw in question:
            return INTENT_ADMIN

    for kw in COURSE_CONTENT_KEYWORDS:
        if kw in question:
            return INTENT_CONTENT

    MATH_KEYWORDS = ["什么是", "怎么", "如何", "为什么", "证明", "计算", "求", "解释", "举例"]
    for kw in MATH_KEYWORDS:
        if kw in question:
            return INTENT_KNOWLEDGE

    return INTENT_IRRELEVANT