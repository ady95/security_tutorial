"""12장 프로젝트용 RAG 색인 만들기 (08-2 와 같음, 색인 위치만 INDEX_PATH 로 지정 가능)

08-2 RAG 색인 만들기 — 문서를 조각내고 임베딩해 index.json 에 저장한다

    python build_index.py

원리가 잘 보이도록 벡터 데이터베이스 없이 JSON 파일 하나에 저장한다.
임베딩은 OpenAI 호환 API(/v1/embeddings)로 만들며, .env 의 EMBED_MODEL 로 모델을 고른다.
"""
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

HERE = Path(__file__).resolve().parent
load_dotenv(HERE.parent.parent / ".env")
INDEX_PATH = Path(os.environ.get("INDEX_PATH", HERE / "index.json"))
client = OpenAI()
# 임베딩은 답변 생성과 다른 곳에서 만들 수 있다 (예: 임베딩은 로컬 Ollama, 답변은 API)
embed_client = OpenAI(base_url=os.getenv("EMBED_BASE_URL") or None,
                      api_key=os.getenv("EMBED_API_KEY") or os.environ.get("OPENAI_API_KEY"))
EMBED_MODEL = os.environ.get("EMBED_MODEL", "qwen3-embedding:0.6b")


def split_chunks(path: Path) -> list[dict]:
    """문서를 빈 줄 기준 문단으로 나누고, 각 조각 앞에 문서 제목을 붙인다."""
    text = path.read_text(encoding="utf-8").strip()
    title, _, body = text.partition("\n")
    title = title.lstrip("# ").strip()
    chunks = []
    for i, para in enumerate(p.strip() for p in body.split("\n\n") if p.strip()):
        chunks.append({"id": f"{path.stem}-{i}", "source": path.name, "text": f"[{title}] {para}"})
    return chunks


def main():
    chunks = [c for doc in sorted((HERE / "docs").glob("*.md")) for c in split_chunks(doc)]
    start = time.time()
    resp = embed_client.embeddings.create(model=EMBED_MODEL, input=[c["text"] for c in chunks])
    for chunk, item in zip(chunks, resp.data):
        chunk["vector"] = item.embedding
    INDEX_PATH.write_text(json.dumps(chunks, ensure_ascii=False), encoding="utf-8")
    print(f"문서 {len({c['source'] for c in chunks})}개 → 조각 {len(chunks)}개 · "
          f"임베딩 {len(chunks[0]['vector'])}차원 · {time.time() - start:.1f}초 · 모델 {EMBED_MODEL}")


if __name__ == "__main__":
    main()
