"""12장 프로젝트 Agent 의 도구 — 09-2 의 네 개에 메일 보내기와 파일 삭제를 더한 여섯 개

메일은 실제로 보내지 않고 output/outbox/ 에 파일로 남긴다 (실습용).
경로는 환경변수로 바꿀 수 있다: WORKSPACE, OUTPUT, INDEX_PATH
"""
import json
import math
import os
import time
from pathlib import Path

from openai import OpenAI

HERE = Path(__file__).resolve().parent
WORKSPACE = Path(os.environ.get("WORKSPACE", HERE / "workspace")).resolve()
OUTPUT = Path(os.environ.get("OUTPUT", HERE / "output")).resolve()
INDEX_PATH = Path(os.environ.get("INDEX_PATH", HERE / "index.json"))
EMBED_MODEL = os.environ.get("EMBED_MODEL", "qwen3-embedding:0.6b")
ORDERS = {"101": {"item": "보안 입문서", "status": "배송 중", "eta": "10월 11일"},
          "102": {"item": "USB 보안키", "status": "배송 완료", "eta": "-"}}
_embed = None


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
    return f"저장 완료: output/{target.relative_to(OUTPUT).as_posix()} ({len(content)}자)"


def delete_file(path: str) -> str:
    target = _inside(OUTPUT, path.removeprefix("output/"))
    target.unlink()
    return f"삭제 완료: output/{target.relative_to(OUTPUT).as_posix()}"


def send_email(to: str, subject: str, body: str) -> str:
    """실습용: 실제로 보내지 않고 output/outbox/ 에 남긴다."""
    box = OUTPUT / "outbox"
    box.mkdir(parents=True, exist_ok=True)
    name = f"{time.strftime('%H%M%S')}-{to.replace('@', '_at_')}.txt"
    (box / name).write_text(f"To: {to}\nSubject: {subject}\n\n{body}\n", encoding="utf-8")
    return f"메일 발송(실습용 보관): {to} / {subject}"


def search_document(query: str) -> str:
    global _embed
    if _embed is None:
        _embed = OpenAI(base_url=os.getenv("EMBED_BASE_URL") or None,
                        api_key=os.getenv("EMBED_API_KEY") or os.environ.get("OPENAI_API_KEY"))
    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    q = _embed.embeddings.create(model=EMBED_MODEL, input=[query]).data[0].embedding

    def cos(v):
        return sum(a * b for a, b in zip(q, v)) / (math.sqrt(sum(a * a for a in q)) * math.sqrt(sum(b * b for b in v)))

    top = sorted(index, key=lambda c: cos(c["vector"]), reverse=True)[:3]
    return "\n".join(f"({c['source']}) {c['text']}" for c in top)


def get_order(order_id: str) -> str:
    order = ORDERS.get(str(order_id).strip())
    return json.dumps(order or {"error": "주문을 찾을 수 없습니다"}, ensure_ascii=False)


FUNCS = {"read_file": read_file, "write_file": write_file, "delete_file": delete_file,
         "send_email": send_email, "search_document": search_document, "get_order": get_order}


def _tool(name, desc, props, required):
    return {"type": "function", "function": {"name": name, "description": desc, "parameters": {
        "type": "object", "properties": props, "required": required}}}


TOOLS = [
    _tool("read_file", "workspace 폴더의 텍스트 파일을 읽는다",
          {"path": {"type": "string", "description": "예: workspace/notes.txt"}}, ["path"]),
    _tool("write_file", "output 폴더에 텍스트 파일을 저장한다",
          {"path": {"type": "string", "description": "예: output/summary.md"},
           "content": {"type": "string"}}, ["path", "content"]),
    _tool("delete_file", "output 폴더의 파일을 삭제한다",
          {"path": {"type": "string"}}, ["path"]),
    _tool("send_email", "메일을 보낸다",
          {"to": {"type": "string"}, "subject": {"type": "string"}, "body": {"type": "string"}},
          ["to", "subject", "body"]),
    _tool("search_document", "쇼핑몰 운영 문서(환불·배송·개인정보·계정 보안)에서 관련 내용을 검색한다",
          {"query": {"type": "string"}}, ["query"]),
    _tool("get_order", "주문 번호로 주문 상태를 조회한다",
          {"order_id": {"type": "string"}}, ["order_id"]),
]
