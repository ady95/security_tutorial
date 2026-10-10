"""12장 프로젝트 가드 — Agent(LLM) 바깥에서 도구 실행 직전에 끼어든다

  1) 정책 판단   policy.json 의 허용 목록으로 허용 · 승인 필요 · 금지 판단 (10-5)
  2) 승인 대기   승인이 필요한 호출은 실행하지 않고 approvals/ 에 요청을 남긴다 (10-4)
  3) 감사 기록   모든 판단을 audit.jsonl 에 추적 식별자와 함께 남긴다 (13-2)

"신뢰할 수 없는 내용을 읽었는가(tainted)"를 따로 추적한다. 파일이나 문서를 한 번이라도 읽은 뒤에는
그 안의 문장이 다음 판단에 섞여 있을 수 있으므로, 정책이 이 상태를 조건으로 쓸 수 있다
(MITRE ATLAS 완화책 AML.M0030 과 같은 생각).
"""
import json
import os
import posixpath
import time
import uuid
from pathlib import Path

UNTRUSTED_SOURCES = {"read_file", "search_document"}


def path_under(path: str, prefix: str) -> bool:
    norm = posixpath.normpath(str(path).replace("\\", "/"))
    return not norm.startswith(("../", "/")) and (norm + "/").startswith(prefix)


def matches(cond: dict, args: dict, tainted: bool) -> bool:
    if "tainted" in cond and cond["tainted"] != tainted:
        return False
    if "path_under" in cond and not path_under(args.get("path", ""), cond["path_under"]):
        return False
    if "to_domain_in" in cond:
        to = str(args.get("to", ""))
        if "@" not in to or to.rsplit("@", 1)[1].lower() not in cond["to_domain_in"]:
            return False
    return True


class Guard:
    def __init__(self, base: Path, funcs: dict, agent: str, on_behalf_of: str,
                 use_policy: bool = True, use_approval: bool = True):
        self.base, self.funcs = base, funcs
        self.agent, self.on_behalf_of = agent, on_behalf_of
        self.use_policy, self.use_approval = use_policy, use_approval
        self.policy = json.loads((base / "policy.json").read_text(encoding="utf-8"))
        audit_dir = Path(os.environ.get("AUDIT_DIR", base))   # 감사 기록·승인 요청 저장 위치
        self.audit_path = audit_dir / "audit.jsonl"
        self.approvals = audit_dir / "approvals"
        self.tainted = False

    def decide(self, name: str, args: dict) -> tuple[str, str]:
        if not self.use_policy:
            return "allow", "정책 꺼짐"
        rules = self.policy["tools"].get(name)
        if rules is None:
            return "deny", "정책에 없는 도구 (기본 거부)"
        for rule in rules:
            if matches(rule.get("when", {}), args, self.tainted):
                return rule["decision"], rule.get("reason", "규칙 일치")
        return "deny", "어떤 규칙에도 맞지 않음 (기본 거부)"

    def audit(self, **kw):
        with open(self.audit_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"time": time.strftime("%Y-%m-%dT%H:%M:%S"), "agent": self.agent,
                                "on_behalf_of": self.on_behalf_of, **kw}, ensure_ascii=False) + "\n")

    def execute(self, trace_id: str, step: int, name: str, args: dict) -> str:
        decision, reason = self.decide(name, args)
        short = {k: (v[:80] + "…" if isinstance(v, str) and len(v) > 80 else v) for k, v in args.items()}
        entry = dict(trace_id=trace_id, step=step, tool=name, args=short,
                     tainted=self.tainted, decision=decision, reason=reason)
        if decision == "deny":
            self.audit(**entry, result="거부")
            return f"거부됨: {reason}"
        if decision == "approve" and self.use_approval:
            ticket = uuid.uuid4().hex[:6]
            self.approvals.mkdir(exist_ok=True)
            (self.approvals / f"{ticket}.json").write_text(json.dumps(
                {"ticket": ticket, "trace_id": trace_id, "tool": name, "args": args,
                 "reason": reason, "status": "pending"}, ensure_ascii=False, indent=1), encoding="utf-8")
            self.audit(**entry, result=f"승인 대기 {ticket}")
            return f"승인 대기 중입니다 (요청 번호 {ticket}). 사람이 승인하면 실행됩니다. 지금은 실행하지 마세요."
        try:
            result = self.funcs[name](**args)
        except Exception as e:
            result = f"오류: {e}"
        if name in UNTRUSTED_SOURCES:
            self.tainted = True
        self.audit(**entry, result=result[:120])
        return result
