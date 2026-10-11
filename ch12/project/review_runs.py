"""Read only summaries and selected fake-case evidence; no approval or execution."""
import argparse
import json
import os
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--engine", choices=["live", "replay"], required=True)
    p.add_argument("--case", choices=["P1", "P2", "T1", "C1", "N1"])
    p.add_argument("--mode", choices=["weak", "guard"])
    p.add_argument("--show", choices=["transcript", "audit", "summary"])
    p.add_argument("--root", type=Path, default=Path(os.getenv("INDEX_PATH", Path(__file__).with_name("index.json"))).parent / "redteam-runs")
    args = p.parse_args()
    results = []
    for path in args.root.glob("*/result.json"):
        result = json.loads(path.read_text(encoding="utf-8"))
        if result["engine"] == args.engine and (not args.case or result["case"] == args.case) and (not args.mode or result["mode"] == args.mode):
            results.append((path, result))
    results.sort(key=lambda item: item[0].stat().st_mtime)
    if args.show:
        if not args.case or not args.mode or not results:
            p.error("--show requires matching --case and --mode")
        path = results[-1][0].parent / {"transcript": "transcript.txt", "audit": "audit/audit.jsonl", "summary": "output/refund-summary.md"}[args.show]
        print(path.read_text(encoding="utf-8") if path.exists() else "artifact absent")
    else:
        for _, result in results:
            print(json.dumps({key: result[key] for key in ("case", "mode", "engine", "status", "attack_success", "outbox_count", "pending_count", "normal_order_observed", "marker_in_audit", "marker_in_pending")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
