#!/bin/bash
# 02-6 서버 설정 점검 스크립트 — 02-5 의 점검 항목을 확인한다 (root 로 실행)
risk=0
ok()   { echo "[OK]   $1"; }
warn() { echo "[위험] $1"; risk=$((risk+1)); }

echo "== 1. 누구나 쓸 수 있는 파일 (/opt, /etc, /usr/local)"
files=$(find /opt /etc /usr/local -xdev -type f -perm -o+w 2>/dev/null)
if [ -n "$files" ]; then for f in $files; do warn "누구나 쓸 수 있음: $f ($(stat -c %a "$f"))"; done
else ok "없음"; fi

echo "== 2. 다른 계정이 읽을 수 있는 비밀 파일"
files=$(find /opt /home /root -xdev -type f \( -name '.env*' -o -name '*.key' -o -name '*.pem' \) -perm -o+r 2>/dev/null)
if [ -n "$files" ]; then for f in $files; do warn "누구나 읽을 수 있음: $f ($(stat -c %a "$f"))"; done
else ok "없음"; fi

echo "== 3. sudo 허용 범위"
lines=$(grep -hsE '^[^#].*NOPASSWD:[[:space:]]*ALL' /etc/sudoers /etc/sudoers.d/*)
if [ -n "$lines" ]; then echo "$lines" | while read -r l; do echo "[위험] 비밀번호 없이 모든 명령 허용: $l"; done; risk=$((risk+$(echo "$lines" | wc -l)))
else ok "비밀번호 없는 전체 허용 없음"; fi

echo "== 4. SSH 설정"
# sshd -T 는 설정 파일들을 합친 '실제 적용값'을 출력한다. 실행에 실패하면 OK 로 넘기지 않는다
if ! eff=$(sshd -T 2>&1); then
  warn "확인 불가 — sshd -T 실패: $(echo "$eff" | head -1)"
else
  [ "$(echo "$eff" | awk '/^permitrootlogin /{print $2}')" = "yes" ] && warn "PermitRootLogin yes" || ok "root 로그인 차단"
  [ "$(echo "$eff" | awk '/^passwordauthentication /{print $2}')" = "yes" ] && warn "PasswordAuthentication yes" || ok "비밀번호 로그인 차단"
fi

echo "== 5. 셸 기록에 남은 비밀값"
hits=$(grep -lsiE 'pass(word)?[=: ]|-p[^ ]+|secret|token' /root/.bash_history /home/*/.bash_history)
if [ -n "$hits" ]; then for f in $hits; do warn "비밀값 의심 기록: $f"; done
else ok "없음"; fi

echo
if [ "$risk" -eq 0 ]; then echo "점검 결과: 위험 항목 없음"; else echo "점검 결과: 위험 항목 ${risk}건"; fi
