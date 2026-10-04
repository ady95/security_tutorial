#!/bin/sh
# 02-8 실습용 트래픽 생성기 — 랩 안의 target 에만 요청을 보낸다
#   normal    : 사람이 사이트를 둘러보는 정도의 요청
#   suspicious: 없는 경로 탐색 + 관리자 로그인 실패 반복 후 성공
T=http://target

normal() {
  for p in / /about / /about; do
    curl -s -o /dev/null -w "%{http_code} GET $p\n" "$T$p"
    sleep 1
  done
}

suspicious() {
  for p in /.env /backup.zip /admin.php /wp-login.php /config.bak; do
    curl -s -o /dev/null -w "%{http_code} GET $p\n" "$T$p"
  done
  for pw in admin 1234 password lab-only-wrong lab-only-admin-2026; do
    curl -s -o /dev/null -u "admin:$pw" -w "%{http_code} GET /admin (admin:$pw)\n" "$T/admin"
  done
}

case "$1" in
  normal) normal ;;
  suspicious) suspicious ;;
  *) echo "usage: traffic.sh normal|suspicious"; exit 1 ;;
esac
