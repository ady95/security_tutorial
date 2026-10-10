"""09-2 Tool Calling 로컬 Agent — 도구 네 개를 가진 작은 Agent

    python agent.py "환불 정책을 찾아서 세 줄로 요약하고 output/refund-summary.md 로 저장해 줘"

도구
  read_file(path)              workspace/ 안의 파일 읽기 (10-2 의 경로 제한)
  write_file(path, content)    output/ 안에만 쓰기
  search_document(query)       08-2 RAG 색인에서 쇼핑몰 문서 검색
  get_order(order_id)          주문 조회 API (실습용 가짜 데이터, 네트워크 없음)

모든 단계는 trace.jsonl 에 추적 식별자와 함께 기록된다 (13-2).
"""
import json
import math
import os
import sys
import time
import uuid
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

HERE = Path(__file__).resolve().parent
load_dotenv(HERE.parent.parent / ".env")
client = OpenAI()
embed_client = OpenAI(base_url=os.getenv("EMBED_BASE_URL") or None,
                      api_key=os.getenv("EMBED_API_KEY") or os.environ.get("OPENAI_API_KEY"))
MODEL = os.environ["OPENAI_MODEL"]
EMBED_MODEL = os.environ.get("EMBED_MODEL", "qwen3-embedding:0.6b")
EFFORT = os.getenv("LLM_REASONING_EFFORT")
OPTS = {"reasoning_effort": EFFORT} if EFFORT else {}
MAX_STEPS = 6
WORKSPACE = (HERE / "workspace").resolve()
OUTPUT = (HERE / "output").resolve()
INDEX = HERE.parent.parent / "ch08" / "rag" / "index.json"
ORDERS = {"101": {"item": "보안 입문서", "status": "배송 중", "eta": "10월 11일"},
          "102": {"item": "USB 보안키", "status": "배송 완료", "eta": "-"}}


# ---- 도구 구현 -------------------------------------------------------------
def _inside(base: Path, path: str) -> Path:
    target = (base / path).resolve()
    if not target.is_relative_to(base):
        raise PermissionError(f"허용된 폴더 밖의 경로입니다: {path}")
    return target


def read_file(path: str) -> str:
    return _inside(WORKSPACE, path.removeprefix("workspace/")).read_text(encoding="utf-8")[:4000]


def write_file(path: str, content: str) -> str:
    target = _inside(OUTPUT, path.removeprefix("output/"))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"저장 완료: output/{target.relative_to(OUTPUT)} ({len(content)}자)"


def search_document(query: str) -> str:
    index = json.loads(INDEX.read_text(encoding="utf-8"))
    q = embed_client.embeddings.create(model=EMBED_MODEL, input=[query]).data[0].embedding

    def cos(v):
        return sum(a * b for a, b in zip(q, v)) / (math.sqrt(sum(a * a for a in q)) * math.sqrt(sum(b * b for b in v)))

    top = sorted(index, key=lambda c: cos(c["vector"]), reverse=True)[:2]
    return "\n".join(f"({c['source']}) {c['text']}" for c in top)


def get_order(order_id: str) -> str:
    order = ORDERS.get(str(order_id).strip())
    return json.dumps(order or {"error": "주문을 찾을 수 없습니다"}, ensure_ascii=False)


FUNCS = {"read_file": read_file, "write_file": write_file,
         "search_document": search_document, "get_order": get_order}


def tool(name, desc, props, required):
    return {"type": "function", "function": {"name": name, "description": desc, "parameters": {
        "type": "object", "properties": props, "required": required}}}


TOOLS = [
    tool("read_file", "workspace 폴더의 텍스트 파일을 읽는다",
         {"path": {"type": "string", "description": "예: workspace/notes.txt"}}, ["path"]),
    tool("write_file", "output 폴더에 텍스트 파일을 저장한다",
         {"path": {"type": "string", "description": "예: output/summary.md"},
          "content": {"type": "string"}}, ["path", "content"]),
    tool("search_document", "쇼핑몰 운영 문서(환불·배송·개인정보·계정 보안)에서 관련 내용을 검색한다",
         {"query": {"type": "string"}}, ["query"]),
    tool("get_order", "주문 번호로 주문 상태를 조회한다",
         {"order_id": {"type": "string"}}, ["order_id"]),
]
SYSTEM = ("당신은 secbook-shop 운영을 돕는 Agent입니다. 주어진 도구로 사용자의 목표를 처리하고, "
          "끝나면 무엇을 했는지 한국어로 짧게 보고하세요.")


# ---- Agent 반복 ------------------------------------------------------------
def run(goal: str):
    trace_id = uuid.uuid4().hex[:8]
    log = open(HERE / "trace.jsonl", "a", encoding="utf-8")

    def record(**kw):
        log.write(json.dumps({"trace_id": trace_id, "time": time.strftime("%H:%M:%S"), **kw},
                             ensure_ascii=False) + "\n")

    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": goal}]
    record(step=0, kind="goal", content=goal)
    start = time.time()
    for step in range(1, MAX_STEPS + 1):
        msg = client.chat.completions.create(model=MODEL, messages=messages, tools=TOOLS, **OPTS).choices[0].message
        if not msg.tool_calls:
            print(f"[완료] {step}단계 · {time.time() - start:.1f}초\n{(msg.content or '').strip()}")
            record(step=step, kind="final", content=msg.content)
            return
        messages.append(msg)
        for call in msg.tool_calls:
            name, args = call.function.name, json.loads(call.function.arguments or "{}")
            try:
                result = FUNCS[name](**args)
            except Exception as e:  # 거부·오류도 결과로 돌려줘 Agent 가 다음 판단에 쓰게 한다
                result = f"오류: {e}"
            print(f"[{step}단계] {name}({json.dumps(args, ensure_ascii=False)[:80]}) → {result[:60]!r}")
            record(step=step, kind="tool", tool=name, args=args, result=result[:200])
            messages.append({"role": "tool", "tool_call_id": call.id, "content": result})
    print(f"[중단] 최대 {MAX_STEPS}단계를 넘었습니다")
    record(step=MAX_STEPS, kind="stopped")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    run(sys.argv[1] if len(sys.argv) > 1 else "workspace/notes.txt 를 읽고, 거기 나온 주문의 배송 상태를 알려 줘")
