"""10-5 정책 엔진 — Agent(LLM) 바깥에서 도구 호출을 허용·승인 필요·금지로 판단한다 (표준 라이브러리만 사용)

    python policy_engine.py            # demo_calls.json 의 도구 호출을 판단하고 decisions.log 에 기록
"""
import json
import posixpath
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent


def path_under(path: str, prefix: str) -> bool:
    """../ 를 정리한 뒤에도 prefix 아래인지 확인한다 (문자열 비교만으로 판단하지 않는다)."""
    norm = posixpath.normpath(path.replace("\\", "/"))
    return not norm.startswith(("../", "/")) and (norm + "/").startswith(prefix)


def matches(cond: dict, args: dict) -> bool:
    if "path_under" in cond and not path_under(str(args.get("path", "")), cond["path_under"]):
        return False
    if "host_in" in cond and urlparse(str(args.get("url", ""))).hostname not in cond["host_in"]:
        return False
    if "to_domain_in" in cond:
        to = str(args.get("to", ""))
        if "@" not in to or to.rsplit("@", 1)[1].lower() not in cond["to_domain_in"]:
            return False
    if "amount_max" in cond and not (0 < float(args.get("amount", 0)) <= cond["amount_max"]):
        return False
    return True


def decide(policy: dict, call: dict) -> tuple[str, str]:
    rules = policy["tools"].get(call.get("tool"))
    if rules is None:
        return "deny", "정책에 없는 도구 (기본 거부)"
    for rule in rules:
        if matches(rule.get("when", {}), call.get("args", {})):
            return rule["decision"], rule.get("reason", "규칙 일치")
    return "deny", "어떤 규칙에도 맞지 않음 (기본 거부)"


def main():
    policy = json.loads((HERE / "policy.json").read_text(encoding="utf-8"))
    calls = json.loads((HERE / "demo_calls.json").read_text(encoding="utf-8"))
    label = {"allow": "허용", "approve": "승인 필요", "approve2": "2인 승인", "deny": "금지"}
    with open(HERE / "decisions.log", "a", encoding="utf-8") as log:
        for call in calls:
            decision, reason = decide(policy, call)
            args = json.dumps(call.get("args", {}), ensure_ascii=False)
            print(f"[{label[decision]:^5}] {call['tool']}({args})  ← {reason}")
            log.write(json.dumps({"time": time.strftime("%Y-%m-%dT%H:%M:%S"), **call,
                                  "decision": decision, "reason": reason}, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
