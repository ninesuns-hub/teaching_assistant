import os
import sys
import re
import json
import logging
from typing import List, Dict, Any
from openai import OpenAI
from dotenv import load_dotenv

# 纭繚鍙互瀵煎叆 backend 鐩綍涓嬬殑妯″潡
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from agent_core import ReactAgent
from agent_core.tools import create_admin_tool, create_knowledge_tool
from agent_core.rag import HybridSearcher
from agent_core.config.settings import settings
from database.course_repo import query_course_admin, init_db

# 閰嶇疆鏃ュ織
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 鍔犺浇鐜鍙橀噺
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
浣犳槸涓€浣嶇鏁ｆ暟瀛﹁绋嬬殑璧勬繁鍔╂暀锛岀幇鍦ㄩ渶瑕佷綘浣滀负涓€涓鍒わ紙LLM-as-a-Judge锛夛紝璇勪及 RAG 绯荤粺鐢熸垚鐨勫洖绛斻€?

### 璇勪及鏍囧噯锛?
1. **鍑嗙‘鎬?(Accuracy)**锛氬洖绛旀槸鍚﹀寘鍚簡鈥滄湡寰呭唴瀹光€濅腑鐨勬牳蹇冭鐐癸紵鏄惁瀛樺湪浜嬪疄鎬ч敊璇紵
2. **瀹屾暣鎬?(Completeness)**锛氬洖绛旀槸鍚﹀畬鏁磋В鍐充簡闂锛?
3. **妫€绱㈣川閲?(Retrieval Quality)**锛氱郴缁熸绱㈠埌鐨勫弬鑰冨唴瀹规槸鍚︿笌闂楂樺害鐩稿叧锛熸槸鍚︿负鍥炵瓟鎻愪緵浜嗘湁鍔涙敮鎾戯紵
4. **蹇犲疄搴?(Faithfulness)**锛氬洖绛旀槸鍚﹀熀浜庢绱㈠埌鐨勫弬鑰冨唴瀹癸紵鏄惁瀛樺湪骞昏锛堢敓鎴愪簡鍙傝€冨唴瀹逛腑娌℃湁鐨勪俊鎭級锛?

### 杈撳叆淇℃伅锛?
- **闂**: {question}
- **鏈熷緟鍐呭 (Ground Truth)**: {expected_content}
- **绯荤粺妫€绱㈠埌鐨勫弬鑰冨唴瀹?*:
{retrieved_context if retrieved_context else "鏈绱㈠埌鍐呭"}
- **绯荤粺鏈€缁堝洖绛?*: {actual_answer}

### 杈撳嚭鏍煎紡 (璇峰姟蹇呰繑鍥?JSON 鏍煎紡):
{{
    "score": 0-10,
    "retrieval_score": 0-10,
    "reasoning": "绠€瑕佽鏄庤瘎鍒嗙悊鐢憋紝蹇呴』璇勪环妫€绱㈠唴瀹圭殑鐩稿叧鎬у拰鍥炵瓟鐨勫繝瀹炲害",
    "is_pass": true/false
}}
"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "浣犳槸涓€涓弗璋ㄧ殑瀛︽湳璇勪及鍔╂墜銆?},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"瑁佸垽璇勫垎澶辫触: {e}")
            return {"score": 0, "reasoning": f"璇勫垎鍑洪敊: {str(e)}", "is_pass": False}

def parse_eval_set(file_path: str) -> List[Dict[str, str]]:
    if not os.path.exists(file_path):
        logger.error(f"娴嬭瘎闆嗘枃浠朵笉瀛樺湪: {file_path}")
        return []

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 鍖归厤 ### N. 棰樼洰鍚?\n - 闂: ... \n - 鏈熷緟鍐呭: ... \n - 绮惧噯瀹氫綅: ...
    cases = []
    pattern = r"### .*?\n- \*\*闂\*\*: (.*?)\n- \*\*鏈熷緟鍐呭\*\*: (.*?)\n- \*\*绮惧噯瀹氫綅\*\*: (.*?)(?:\n|$)"
    matches = re.findall(pattern, content, re.DOTALL)

    for m in matches:
        cases.append({
            "question": m[0].strip(),
            "expected": m[1].strip(),
            "location": m[2].strip()
        })

    return cases

async def run_evaluation():
    # 1. 鍒濆鍖栫郴缁?
    init_db()
    hybrid_searcher = HybridSearcher()
    tools = [
        create_admin_tool(query_course_admin),
        create_knowledge_tool(hybrid_searcher.query)
    ]
    agent = ReactAgent(config=settings, tools=tools)
    judge = LLMAsAJudge()

    # 2. 鍔犺浇娴嬭瘎闆?
    eval_file = os.path.join(backend_dir, 'storage', 'raw', 'assets', 'evaluation_set', 'discrete_math_eval_set.md')
    test_cases = parse_eval_set(eval_file)

    if not test_cases:
        logger.error("鏈壘鍒颁换浣曟祴璇曠敤渚嬶紝璇锋鏌ヨВ鏋愰€昏緫鎴栨枃浠惰矾寰勩€?)
        return

    results = []
    total_score = 0
    pass_count = 0

    logger.info(f"寮€濮嬫祴璇勶紝鍏?{len(test_cases)} 涓敤渚?..")

    for i, case in enumerate(test_cases):
        logger.info(f"姝ｅ湪娴嬭瘯 [{i+1}/{len(test_cases)}]: {case['question'][:30]}...")

        # 鑾峰彇 Agent 鍥炵瓟
        actual_answer = ""
        try:
            for chunk in agent.stream_chat(case['question']):
                actual_answer += chunk
        except Exception as e:
            actual_answer = f"Agent 杩愯寮傚父: {str(e)}"

        # 鑾峰彇妫€绱㈠埌鐨勫弬鑰冨唴瀹?
        retrieved_context = "\n---\n".join(agent.last_observations)

        # 瑁佸垽璇勫垎
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

        logger.info(f"寰楀垎: {result['score']} | 鏄惁閫氳繃: {result['is_pass']}")

    # 3. 鐢熸垚鎶ュ憡
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

    logger.info(f"娴嬭瘎瀹屾垚锛佹姤鍛婂凡淇濆瓨鑷? {report_path}")
    logger.info(f"骞冲潎鍒? {summary['average_score']:.2f} | 閫氳繃鐜? {summary['pass_rate']}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(run_evaluation())
