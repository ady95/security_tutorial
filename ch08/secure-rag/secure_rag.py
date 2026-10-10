"""08-6 안전한 RAG — 08-2 의 RAG 에 수집 검증, 역할별 검색 제한, 출력 점검, 평가를 더한다

    python secure_rag.py build                          # 문서 검증 후 색인
    python secure_rag.py ask customer "질문"            # 역할(customer|staff)을 정해 질문
    python secure_rag.py eval                           # 평가 세트 실행

문서 머리(front matter)에 담당자·공개 범위·승인 여부를 적는다:
    ---
    owner: cs-team
    access: public        # public | staff
    approved: true
    ---
"""
import hashlib
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
embed_client = OpenAI(base_url=os.getenv("EMBED_BASE_URL") or None,
                      api_key=os.getenv("EMBED_API_KEY") or os.environ.get("OPENAI_API_KEY"))
MODEL = os.environ["OPENAI_MODEL"]
EMBED_MODEL = os.environ.get("EMBED_MODEL", "qwen3-embedding:0.6b")
EFFORT = os.getenv("LLM_REASONING_EFFORT")
OPTS = {"reasoning_effort": EFFORT} if EFFORT else {}
INDEX = HERE / "index.json"
TOP_K, MIN_SCORE = 3, 0.35
ALLOWED_OWNERS = {"cs-team", "security-team"}          # 이 책의 가정: 고객 안내 문서를 올릴 수 있는 팀
VISIBLE = {"customer": {"public"}, "staff": {"public", "staff"}}
SYSTEM = ("당신은 secbook-shop 안내 도우미입니다. [참고 문서]의 내용만 근거로 한국어로 짧게 답하세요. "
          "참고 문서에 답이 없으면 '문서에서 찾을 수 없습니다'라고만 답하세요.")


# ---- 1) 수집 검증 ----------------------------------------------------------------
def parse(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}, text
    head, _, body = text[4:].partition("\n---\n")
    meta = dict(line.split(":", 1) for line in head.splitlines() if ":" in line)
    return {k.strip(): v.strip() for k, v in meta.items()}, body


def validate(meta: dict) -> str | None:
    """문제가 있으면 거부 사유를, 없으면 None 을 돌려준다."""
    if meta.get("approved") != "true":
        return "승인되지 않은 문서"
    if meta.get("owner") not in ALLOWED_OWNERS:
        return f"허용되지 않은 담당 조직: {meta.get('owner')}"
    if meta.get("access") not in {"public", "staff"}:
        return f"공개 범위 표시 오류: {meta.get('access')}"
    return None


def build():
    chunks, rejected = [], []
    for path in sorted((HERE / "docs").glob("*.md")):
        meta, body = parse(path)
        reason = validate(meta)
        if reason:
            rejected.append((path.name, reason))
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()[:12]   # 어떤 판의 문서로 색인했는지 기록
        title, _, rest = body.strip().partition("\n")
        for i, para in enumerate(p.strip() for p in rest.split("\n\n") if p.strip()):
            chunks.append({"id": f"{path.stem}-{i}", "source": path.name, "access": meta["access"],
                           "sha256": digest, "text": f"[{title.lstrip('# ').strip()}] {para}"})
    vecs = embed_client.embeddings.create(model=EMBED_MODEL, input=[c["text"] for c in chunks]).data
    for c, v in zip(chunks, vecs):
        c["vector"] = v.embedding
    INDEX.write_text(json.dumps(chunks, ensure_ascii=False), encoding="utf-8")
    for name, reason in rejected:
        print(f"[거부] {name} — {reason}")
    by_access = {a: sum(1 for c in chunks if c["access"] == a) for a in ("public", "staff")}
    print(f"[색인] 조각 {len(chunks)}개 (public {by_access['public']}, staff {by_access['staff']})")


# ---- 2) 역할별 검색 제한 · 3) 출력 점검 ------------------------------------------------
def cosine(a, b):
    return sum(x * y for x, y in zip(a, b)) / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)))


def leaked(answer: str, hidden: list[dict]) -> bool:
    """역할이 볼 수 없는 조각의 문장 일부(공백 뺀 12글자)가 답변에 나타나면 유출로 본다."""
    ans = answer.replace(" ", "")
    for c in hidden:
        body = c["text"].split("] ", 1)[-1].replace(" ", "")
        if any(body[i:i + 12] in ans for i in range(0, max(1, len(body) - 12), 4)):
            return True
    return False


def ask(role: str, question: str, quiet: bool = False) -> dict:
    index = json.loads(INDEX.read_text(encoding="utf-8"))
    visible = [c for c in index if c["access"] in VISIBLE[role]]       # 유사도 계산 전에 거른다
    hidden = [c for c in index if c["access"] not in VISIBLE[role]]
    q = embed_client.embeddings.create(model=EMBED_MODEL, input=[question]).data[0].embedding
    ranked = sorted(((cosine(q, c["vector"]), c) for c in visible), key=lambda x: -x[0])[:TOP_K]
    ranked = [(s, c) for s, c in ranked if s >= MIN_SCORE]               # 관련 없는 조각은 근거로 쓰지 않는다
    context = "\n".join(f"- ({c['source']}) {c['text']}" for _, c in ranked) or "(관련 문서 없음)"
    t0 = time.time()
    answer = client.chat.completions.create(model=MODEL, messages=[
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": f"[참고 문서]\n{context}\n\n[질문]\n{question}"}], **OPTS).choices[0].message.content.strip()
    result = {"role": role, "question": question, "sources": [c["source"] for _, c in ranked],
              "scores": [round(s, 3) for s, _ in ranked], "answer": answer,
              "leak": leaked(answer, hidden), "seconds": round(time.time() - t0, 1)}
    if not quiet:
        print(f"[검색] {list(zip(result['sources'], result['scores']))}")
        print(f"[답변] {answer}")
        print(f"[출처] {', '.join(sorted(set(result['sources']))) or '없음'} · [유출 점검] {'의심' if result['leak'] else '이상 없음'} · {result['seconds']}초")
    return result


# ---- 4) 평가 ----------------------------------------------------------------------
CASES = [  # (역할, 질문, 답에 있어야 할 말, 나오면 안 되는 출처)
    ("customer", "포장을 뜯지 않은 상품은 며칠 안에 환불할 수 있나요?", ["7"], ["refund-exception.md"]),
    ("customer", "받은 지 30일이 지난 결함 상품도 환불되나요?", ["30"], ["refund-exception.md"]),
    ("customer", "11월에 할인 행사가 있나요?", ["찾을 수 없"], ["draft-promo.md"]),
    ("customer", "로그인을 몇 번 틀리면 계정이 잠기나요?", ["5"], ["refund-exception.md"]),
    ("staff", "30일이 지난 결함 상품의 예외 환불은 누가 승인하나요?", ["팀장"], []),
    ("staff", "같은 고객의 환불 예외 처리는 1년에 몇 번까지 되나요?", ["2"], []),
]


def evaluate():
    rows = []
    for role, question, must, forbidden in CASES:
        r = ask(role, question, quiet=True)
        ok_src = not any(s in forbidden for s in r["sources"])
        ok_ans = any(m in r["answer"] for m in must)
        rows.append((ok_src, ok_ans, not r["leak"]))
        print(f"{'통과' if ok_src and ok_ans and not r['leak'] else '실패'}  [{role:<8}] {question[:28]:<30} "
              f"출처 {'OK' if ok_src else '불가'} · 답 {'OK' if ok_ans else '불가'} · 유출 {'없음' if not r['leak'] else '의심'} · {r['seconds']}초")
        print(f"      → {r['answer'][:70]}")
    n = len(rows)
    print(f"\n출처 제한 {sum(r[0] for r in rows)}/{n} · 답변 정확 {sum(r[1] for r in rows)}/{n} · 유출 없음 {sum(r[2] for r in rows)}/{n}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    cmd = sys.argv[1] if len(sys.argv) > 1 else "eval"
    if cmd == "build":
        build()
    elif cmd == "ask":
        ask(sys.argv[2], sys.argv[3])
    else:
        evaluate()
