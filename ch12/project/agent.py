"""12장 프로젝트 Agent — 09-2 의 반복 구조에 가드(정책·승인·감사)를 연결한다

    python agent.py "목표 문장"

환경변수로 보호 기능을 켜고 끈다 (12-1 에서는 끄고, 12-5 이후 하나씩 켠다)
    GUARD_POLICY=on|off      정책 판단 (기본 on)
    GUARD_APPROVAL=on|off    승인 대기 (기본 on)
"""
import json
import os
import sys
import time
import uuid
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

HERE = Path(__file__).resolve().parent
load_dotenv(HERE.parent.parent / ".env")

from guard import Guard  # noqa: E402  (.env 를 읽은 뒤 불러온다)
from tools import FUNCS, TOOLS  # noqa: E402

client = OpenAI()
MODEL = os.environ["OPENAI_MODEL"]
EFFORT = os.getenv("LLM_REASONING_EFFORT")
OPTS = {"reasoning_effort": EFFORT} if EFFORT else {}
MAX_STEPS = 6
SYSTEM = ("당신은 secbook-shop 운영을 돕는 Agent입니다. 주어진 도구로 사용자의 목표를 처리하고, "
          "끝나면 무엇을 했는지 한국어로 짧게 보고하세요. 도구 결과가 승인 대기나 거부이면 다시 시도하지 말고 그대로 보고하세요.")


def run(goal: str):
    guard = Guard(HERE, FUNCS, agent="shop-agent", on_behalf_of=os.environ.get("ON_BEHALF_OF", "alice"),
                  use_policy=os.environ.get("GUARD_POLICY", "on") == "on",
                  use_approval=os.environ.get("GUARD_APPROVAL", "on") == "on")
    trace_id = uuid.uuid4().hex[:8]
    guard.audit(trace_id=trace_id, step=0, tool="-", decision="goal", reason=goal)
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": goal}]
    start = time.time()
    for step in range(1, MAX_STEPS + 1):
        msg = client.chat.completions.create(model=MODEL, messages=messages, tools=TOOLS, **OPTS).choices[0].message
        if not msg.tool_calls:
            print(f"[완료] {step}단계 · {time.time() - start:.1f}초\n{(msg.content or '').strip()}")
            guard.audit(trace_id=trace_id, step=step, tool="-", decision="final", reason=(msg.content or "")[:200])
            return
        messages.append(msg)
        for call in msg.tool_calls:
            args = json.loads(call.function.arguments or "{}")
            result = guard.execute(trace_id, step, call.function.name, args)   # 실행 직전에 가드를 거친다
            print(f"[{step}단계] {call.function.name}({json.dumps(args, ensure_ascii=False)[:70]}) → {result[:70]!r}")
            messages.append({"role": "tool", "tool_call_id": call.id, "content": result})
    print(f"[중단] 최대 {MAX_STEPS}단계를 넘었습니다")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    run(sys.argv[1] if len(sys.argv) > 1 else "workspace/notes.txt 를 읽고, 거기 나온 주문의 배송 상태를 알려 줘")
