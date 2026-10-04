"""00-4. LLM 연결 확인 — 일반 대화와 도구 호출(Tool Calling)

Ollama(기본)와 OpenAI API(선택) 모두 같은 코드로 동작합니다.
어느 쪽을 쓸지는 .env 의 OPENAI_BASE_URL / OPENAI_API_KEY / OPENAI_MODEL 로 정합니다.
    python ch00/hello_llm.py
"""
import os
import time

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI()  # OPENAI_BASE_URL, OPENAI_API_KEY 환경변수를 자동으로 읽는다
MODEL = os.environ["OPENAI_MODEL"]
# 생각(thinking) 모드를 지원하는 모델은 답하기 전에 긴 추론을 먼저 생성한다.
# GPU 없는 PC에서는 이 단계가 몇 분씩 걸리므로 .env 에서 none 으로 끌 수 있게 한다.
EFFORT = os.getenv("LLM_REASONING_EFFORT")
OPTS = {"reasoning_effort": EFFORT} if EFFORT else {}

# 1) 일반 대화
start = time.time()
resp = client.chat.completions.create(
    model=MODEL,
    messages=[{"role": "user", "content": "SQL Injection을 한 문장으로 설명해 주세요."}],
    **OPTS,
)
print(f"[대화] {time.time() - start:.1f}초")
print(resp.choices[0].message.content.strip())
print()

# 2) 도구 호출 — 9장 AI Agent 실습에서 쓰는 기능이다.
#    모델이 "파일을 읽어야겠다"고 판단해 read_file 도구를 호출하는지 본다.
tools = [{
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "지정한 경로의 텍스트 파일을 읽어 내용을 돌려준다",
        "parameters": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "읽을 파일 경로"}},
            "required": ["path"],
        },
    },
}]
start = time.time()
resp = client.chat.completions.create(
    model=MODEL,
    messages=[{"role": "user", "content": "notes.txt 파일을 읽고 요약해 주세요."}],
    tools=tools,
    **OPTS,
)
msg = resp.choices[0].message
print(f"[도구 호출] {time.time() - start:.1f}초")
if msg.tool_calls:
    for call in msg.tool_calls:
        print(f"OK  모델이 도구를 호출했습니다: {call.function.name}({call.function.arguments})")
else:
    print("불가  모델이 도구를 호출하지 않았습니다. 9장 실습에는 도구 호출을 지원하는 모델이 필요합니다.")
    print(f"     모델 응답: {(msg.content or '').strip()[:100]}")
