"""09-9 Agent 감사 기록을 OWASP Agentic Top 10 과 MITRE ATLAS 로 읽기 (표준 라이브러리만 사용)

    python map_frameworks.py                         # sample_audit.jsonl 분석
    python map_frameworks.py 경로/audit.jsonl         # 12장 프로젝트에서 만든 기록 분석

기록(audit.jsonl)을 실행 단위(trace_id)로 묶어 시간순으로 보여 주고, mapping.json 의 규칙에 맞는 단계에
위험 '후보'를 붙인다. 규칙은 판단을 돕는 표시일 뿐이며, 실제로 공격이었는지는 사람이 기록을 보고 정한다.
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAP = json.loads((HERE / "mapping.json").read_text(encoding="utf-8"))


def load(path: Path) -> dict[str, list[dict]]:
    traces = defaultdict(list)
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            e = json.loads(line)
            traces[e["trace_id"]].append(e)
    return traces


def executed(e: dict) -> bool:
    """가드를 통과해 실제로 실행되었는가 (거부·승인 대기는 실행되지 않은 것)."""
    return not str(e.get("result", "")).startswith(("거부", "승인 대기"))


def external(e: dict) -> bool:
    to = str(e.get("args", {}).get("to", ""))
    return "@" in to and to.rsplit("@", 1)[1].lower() not in MAP["internal_domains"]


def in_goal(tool: str, goal: str) -> bool:
    return any(w in goal for w in MAP["goal_words"].get(tool, []))


def match(rule: dict, e: dict, goal: str) -> bool:
    w = rule["when"]
    if "tool_in" in w and e["tool"] not in w["tool_in"]:
        return False
    if "executed" in w and executed(e) != w["executed"]:
        return False
    if "tainted" in w and e.get("tainted") != w["tainted"]:
        return False
    if "external" in w and external(e) != w["external"]:
        return False
    if w.get("not_in_goal") and in_goal(e["tool"], goal):
        return False
    return True


def analyze(steps: list[dict]) -> tuple[str, list[tuple[dict, list[dict]]], list[dict]]:
    goal = next((e["reason"] for e in steps if e["decision"] == "goal"), "")
    calls = [e for e in steps if e["tool"] != "-"]
    tagged = [(e, [r for r in MAP["rules"] if "tool_in" in r["when"] and match(r, e, goal)]) for e in calls]
    final = next((e["reason"] for e in steps if e["decision"] == "final"), "")
    sent = any(e["tool"] == "send_email" and executed(e) for e in calls)
    extra = [r for r in MAP["rules"] if r["when"].get("final_claims_sent_without_send")
             and not sent and any(w in final for w in MAP["claim_words"])]
    return goal, tagged, extra


def main(path: Path):
    traces = load(path)
    hits = Counter()
    print(f"[기록] {path.name} · 실행 {len(traces)}건 · 줄 {sum(len(v) for v in traces.values())}개\n")
    for tid, steps in traces.items():
        goal, tagged, extra = analyze(steps)
        guard = "OFF" if any(e.get("reason") == "정책 꺼짐" for e in steps) else "ON"
        print(f"=== {tid} · 가드 {guard} · 목표: {goal}")
        for e, rules in tagged:
            outcome = "실행" if executed(e) else str(e["result"]).split(":")[0][:12]
            args = json.dumps(e["args"], ensure_ascii=False)[:48]
            print(f"  [{e['step']}] {e['tool']}({args}) tainted={str(e['tainted']).lower()} → {e['decision']} · {outcome}")
            for r in rules:
                hits[(r["id"], r["name"], guard, outcome == "실행")] += 1
                print(f"      {r['id']} {r['name']}: {', '.join(r['asi'] + r['atlas'])}")
        final = next((e["reason"] for e in steps if e["decision"] == "final"), None)
        print(f"  [보고] {final[:70] if final else '(보고 없이 끝남)'}")
        for r in extra:
            hits[(r["id"], r["name"], guard, True)] += 1
            print(f"      {r['id']} {r['name']}: {', '.join(r['asi'])}")
        print()
    print("[요약] 규칙별 후보 수 (가드 OFF / ON, 괄호 안은 그중 실제로 실행된 수)")
    for rid, name in sorted({(k[0], k[1]) for k in hits}):
        cols = []
        for g in ("OFF", "ON"):
            total = hits[(rid, name, g, True)] + hits[(rid, name, g, False)]
            cols.append(f"{total}({hits[(rid, name, g, True)]})")
        print(f"  {rid} {name:<20} {cols[0]:>6} / {cols[1]:<6}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "sample_audit.jsonl")
