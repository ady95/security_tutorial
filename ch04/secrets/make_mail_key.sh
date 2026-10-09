#!/bin/sh
# 04-5 커밋 전 검사 확인용 — 키를 직접 적은 mail.py 를 만든다 (가짜 키는 실행할 때 무작위 생성)
KEY=$(head -c 4096 /dev/urandom | tr -dc 'A-Za-z0-9' | head -c 40)
printf 'MAIL_API_KEY = "%s"\n' "$KEY" > /work/demo-app/mail.py
echo "mail.py 작성 (키를 코드에 직접 적음)"
