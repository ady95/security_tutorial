"""Separate process keeps model state and tool paths isolated for one local case."""
import os
import sys
from pathlib import Path

from redteam_lab import CASES


def main():
    root = Path(os.environ["LAB_ROOT"])
    case = sys.argv[1]
    if case == "P2":
        import build_index
        chunks = [c for doc in sorted((root / "docs").glob("*.md")) for c in build_index.split_chunks(doc)]
        response = build_index.embed_client.with_options(timeout=120, max_retries=0).embeddings.create(
            model=build_index.EMBED_MODEL, input=[c["text"] for c in chunks])
        if len(response.data) != len(chunks):
            raise ValueError("incomplete embeddings")
        from redteam_lab import write_json
        for chunk, vector in zip(chunks, response.data):
            chunk["vector"] = vector.embedding
        write_json(root / "index.json", chunks)
        print("indexed", len(chunks), "chunks", flush=True)
    import agent
    agent.HERE = root
    agent.client = agent.client.with_options(timeout=120, max_retries=0)
    agent.MAX_STEPS = 4
    if "11434" in str(agent.client.base_url):
        agent.OPTS.update(max_tokens=800, temperature=0)
    # Keep normal project SYSTEM and tools unchanged; test budget only limits steps.
    agent.run(CASES[case]["goal"])


if __name__ == "__main__":
    main()
