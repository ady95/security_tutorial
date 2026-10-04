"""02-8. nginx 접근 로그에서 의심스러운 패턴 찾기 (표준 라이브러리만 사용)

    docker compose logs target --no-log-prefix | python analyze_log.py

다음 네 가지를 IP별로 집계한다.
  1) 요청 수와 상태 코드 분포
  2) 없는 경로(404) 요청 목록 — 무작위 경로 탐색의 흔적
  3) 인증 실패(401) 뒤에 같은 계정으로 성공(200)한 경우 — 비밀번호 추측 성공 의심
  4) 속도 제한(429)에 걸린 요청 수 — 방어가 작동한 흔적
"""
import re
import sys
from collections import Counter, defaultdict

# nginx 기본(combined) 형식: IP - 사용자 [시각] "메서드 경로 프로토콜" 상태 크기 "referer" "user-agent"
LINE = re.compile(
    r'^(?P<ip>\S+) - (?P<user>\S+) \[(?P<time>[^\]]+)\] '
    r'"(?P<method>\S+) (?P<path>\S+) [^"]*" (?P<status>\d{3}) '
)


def parse(lines):
    for line in lines:
        m = LINE.match(line.strip())
        if m:
            yield m.groupdict()


def main():
    records = list(parse(sys.stdin))
    if not records:
        print("분석할 접근 로그가 없습니다.")
        return

    by_ip = defaultdict(list)
    for r in records:
        by_ip[r["ip"]].append(r)

    for ip, rows in by_ip.items():
        status = Counter(r["status"] for r in rows)
        print(f"[{ip}] 요청 {len(rows)}건 · 상태 코드 {dict(sorted(status.items()))}")

        missing = [r["path"] for r in rows if r["status"] == "404"]
        if missing:
            print(f"  - 없는 경로 요청 {len(missing)}건: {', '.join(missing)}")

        fails = Counter()
        for r in rows:
            user = r["user"]
            if r["status"] == "401" and user != "-":
                fails[user] += 1
            elif r["status"] == "200" and fails[user]:
                print(f"  - 경고: 계정 '{user}' 인증 {fails[user]}회 실패 후 성공 ({r['time']})")
                fails[user] = 0
        for user, n in fails.items():
            if n:
                print(f"  - 계정 '{user}' 인증 실패 {n}회 (성공 없음)")

        limited = status.get("429", 0)
        if limited:
            print(f"  - 속도 제한(429)으로 차단된 요청 {limited}건")


if __name__ == "__main__":
    main()
