"""08-2 RAG 질문하기 — 질문과 가까운 조각을 찾아 그 내용을 근거로 답한다

    python ask.py "포장을 뜯지 않은 상품은 며칠 안에 환불할 수 있나요?"
"""
import json
import math
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

HERE = Path(__file__).resolve().parent
load_dotenv(HERE.parent.parent / ".env")
client = OpenAI()
# 임베딩은 답변 생성과 다른 곳에서 만들 수 있다 (예: 임베딩은 로컬 Ollama, 답변은 API)
embed_client = OpenAI(base_url=os.getenv("EMBED_BASE_URL") or None,
                      api_key=os.getenv("EMBED_API_KEY") or os.environ.get("OPENAI_API_KEY"))
MODEL = os.environ["OPENAI_MODEL"]
EMBED_MODEL = os.environ.get("EMBED_MODEL", "qwen3-embedding:0.6b")
EFFORT = os.getenv("LLM_REASONING_EFFORT")
OPTS = {"reasoning_effort": EFFORT} if EFFORT else {}
TOP_K = 2

SYSTEM = (
    "당신은 secbook-shop 고객 안내 도우미입니다. "
    "아래 [참고 문서]에 있는 내용만 근거로 한국어로 짧게 답하세요. "
    "참고 문서에 답이 없으면 추측하지 말고 '문서에서 찾을 수 없습니다'라고만 답하세요."
)


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    return dot / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)))


def main(question: str):
    index = json.loads((HERE / "index.json").read_text(encoding="utf-8"))

    # 1) 검색: 질문을 임베딩해 가장 가까운 조각 TOP_K 개를 고른다
    t0 = time.time()
    qvec = embed_client.embeddings.create(model=EMBED_MODEL, input=[question]).data[0].embedding
    ranked = sorted(index, key=lambda c: cosine(qvec, c["vector"]), reverse=True)[:TOP_K]
    t1 = time.time()
    for c in ranked:
        print(f"[검색] {cosine(qvec, c['vector']):.3f}  {c['source']}  {c['text'][:40]}...")

    # 2) 생성: 고른 조각만 참고 문서로 넣어 답을 만든다
    context = "\n".join(f"- ({c['source']}) {c['text']}" for c in ranked)
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"[참고 문서]\n{context}\n\n[질문]\n{question}"},
        ],
        **OPTS,
    )
    t2 = time.time()
    print(f"[답변] {resp.choices[0].message.content.strip()}")
    print(f"[시간] 검색 {t1 - t0:.1f}초 · 생성 {t2 - t1:.1f}초")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main(sys.argv[1] if len(sys.argv) > 1 else "포장을 뜯지 않은 상품은 며칠 안에 환불할 수 있나요?")
