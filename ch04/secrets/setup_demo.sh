#!/bin/sh
# 04-5 실습용 Git 저장소 만들기
# 가짜 키는 실행할 때 무작위로 만든다. 이 예제 저장소(공개)에는 키처럼 보이는 문자열을 넣지 않기 위해서다.
set -e
rm -rf /work/demo-app && mkdir -p /work/demo-app && cd /work/demo-app
git init -q -b main
git config user.name "lab-dev" && git config user.email "lab-dev@example.com"

rand() { head -c 4096 /dev/urandom | tr -dc "$1" | head -c "$2"; }
AWS_ID="AKIA$(rand 'A-Z2-7' 16)"            # 널리 알려진 클라우드 키 형식
PAY_KEY="lab-only-pay-$(rand 'a-f0-9' 32)"  # 회사 내부에서만 쓰는 결제 키 형식(가정)

# 커밋 1: 테스트하려고 키를 코드에 직접 적었다
cat > config.py <<PY
PAY_API_KEY = "$PAY_KEY"
AWS_ACCESS_KEY_ID = "$AWS_ID"
PY
printf 'from config import PAY_API_KEY\nprint("결제 모듈 준비 완료")\n' > app.py
git add . && git commit -q -m "결제 연동 추가"

# 커밋 2: 실수를 알아채고 키를 환경변수로 옮겼다
cat > config.py <<'PY'
import os

PAY_API_KEY = os.environ["PAY_API_KEY"]
AWS_ACCESS_KEY_ID = os.environ["AWS_ACCESS_KEY_ID"]
PY
printf 'PAY_API_KEY=\nAWS_ACCESS_KEY_ID=\n' > .env.example
printf '.env\n' > .gitignore
git add . && git commit -q -m "키를 환경변수로 이동"

git log --oneline
