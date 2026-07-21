import os
import sys
import re
import json
import logging
from typing import List, Dict, Any
from openai import OpenAI
from dotenv import load_dotenv

# 确保可以导入 backend 目录下的模块
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from agent_core import ReactAgent
from agent_core.tools import create_admin_tool, create_knowledge_tool
from agent_core.rag import HybridSearcher
from agent_core.config.settings import settings
from database.course_repo import query_course_admin, init_db

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 加载环境变量
env_path = os.path.join(backend_dir, 'agent_core', 'config', '.env')
load_dotenv(env_path)

class LLMAsAJudge:
    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("CHAT_API_KEY"),
            base_url=os.getenv("CHAT_BASE_URL")
        )
        self.model = os.getenv("CHAT_MODEL_NAME")

    def judge(self, question: str, expected_content: str, actual_answer: str, retrieved_context: str) -> Dict[str, Any]:
        prompt = f"""
你是一位离散数学课程的资深助教，现在需要你作为一个裁判（LLM-as-a-Judge），评估 RAG 系统生成的回答。

### 评估标准：
1. **准确性 (Accuracy)**：回答是否包含了“期待内容”中的核心要点？是否存在事实性错误？
2. **完整性 (Completeness)**：回答是否完整解决了问题？
3. **检索质量 (Retrieval Quality)**：系统检索到的参考内容是否与问题高度相关？是否为回答提供了有力支撑？
4. **忠实度 (Faithfulness)**：回答是否基于检索到的参考内容？是否存在幻觉（生成了参考内容中没有的信息）？

### 输入信息：
- **问题**: {question}
- **期待内容 (Ground Truth)**: {expected_content}
- **系统检索到的参考内容**: 
{retrieved_context if retrieved_context else "未检索到内容"}
- **系统最终回答**: {actual_answer}

### 输出格式 (请务必返回 JSON 格式):
{{
    "score": 0-10,
    "retrieval_score": 0-10,
    "reasoning": "简要说明评分理由，必须评价检索内容的相关性和回答的忠实度",
    "is_pass": true/false
}}
"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个严谨的学术评估助手。"},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"裁判评分失败: {e}")
            return {"score": 0, "reasoning": f"评分出错: {str(e)}", "is_pass": False}

def parse_eval_set(file_path: str) -> List[Dict[str, str]]:
    if not os.path.exists(file_path):
        logger.error(f"测评集文件不存在: {file_path}")
        return []

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 匹配 ### N. 题目名 \n - 问题: ... \n - 期待内容: ... \n - 精准定位: ...
    cases = []
    pattern = r"### .*?\n- \*\*问题\*\*: (.*?)\n- \*\*期待内容\*\*: (.*?)\n- \*\*精准定位\*\*: (.*?)(?:\n|$)"
    matches = re.findall(pattern, content, re.DOTALL)
    
    for m in matches:
        cases.append({
            "question": m[0].strip(),
            "expected": m[1].strip(),
            "location": m[2].strip()
        })
    
    return cases

async def run_evaluation():
    # 1. 初始化系统
    init_db()
    hybrid_searcher = HybridSearcher()
    tools = [
        create_admin_tool(query_course_admin),
        create_knowledge_tool(hybrid_searcher.query)
    ]
    agent = ReactAgent(config=settings, tools=tools)
    judge = LLMAsAJudge()

    # 2. 加载测评集
    eval_file = os.path.join(backend_dir, 'storage', 'raw', 'assets', 'evaluation_set', 'discrete_math_eval_set.md')
    test_cases = parse_eval_set(eval_file)
    
    if not test_cases:
        logger.error("未找到任何测试用例，请检查解析逻辑或文件路径。")
        return

    results = []
    total_score = 0
    pass_count = 0

    logger.info(f"开始测评，共 {len(test_cases)} 个用例...")

    for i, case in enumerate(test_cases):
        logger.info(f"正在测试 [{i+1}/{len(test_cases)}]: {case['question'][:30]}...")
        
        # 获取 Agent 回答
        actual_answer = ""
        try:
            for chunk in agent.stream_chat(case['question']):
                actual_answer += chunk
        except Exception as e:
            actual_answer = f"Agent 运行异常: {str(e)}"

        # 获取检索到的参考内容
        retrieved_context = "\n---\n".join(agent.last_observations)

        # 裁判评分
        evaluation = judge.judge(case['question'], case['expected'], actual_answer, retrieved_context)
        
        result = {
            "id": i + 1,
            "question": case['question'],
            "expected": case['expected'],
            "actual": actual_answer,
            "retrieved": retrieved_context,
            "score": evaluation.get("score", 0),
            "retrieval_score": evaluation.get("retrieval_score", 0),
            "reasoning": evaluation.get("reasoning", ""),
            "is_pass": evaluation.get("is_pass", False)
        }
        results.append(result)
        
        total_score += result["score"]
        if result["is_pass"]:
            pass_count += 1
        
        logger.info(f"得分: {result['score']} | 是否通过: {result['is_pass']}")

    # 3. 生成报告
    report_path = os.path.join(backend_dir, 'storage', 'raw', 'assets', 'evaluation_set', 'eval_report.json')
    summary = {
        "total_cases": len(test_cases),
        "pass_count": pass_count,
        "pass_rate": f"{pass_count / len(test_cases) * 100:.2f}%",
        "average_score": total_score / len(test_cases),
        "details": results
    }
    
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    logger.info(f"测评完成！报告已保存至: {report_path}")
    logger.info(f"平均分: {summary['average_score']:.2f} | 通过率: {summary['pass_rate']}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(run_evaluation())
