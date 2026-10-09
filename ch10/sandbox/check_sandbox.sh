#!/bin/sh
# 10-3 Sandbox 제한 확인 — "열림"이어야 하는 두 항목 외에는 모두 "막힘"이어야 정상
t() { if eval "$2" >/dev/null 2>&1; then echo "열림  $1"; else echo "막힘  $1"; fi; }
echo "실행 계정: $(id -u):$(id -g)"
echo "남은 특수 권한(CapEff): $(awk '/^CapEff/{print $2}' /proc/self/status)"
echo "권한 상승 금지(NoNewPrivs): $(awk '/^NoNewPrivs/{print $2}' /proc/self/status)"
t "작업 폴더 읽기 (열려 있어야 정상)"   "cat /workspace/notes.txt"
t "결과 폴더 쓰기 (열려 있어야 정상)"   "touch /output/result.txt"
t "작업 폴더 쓰기"                       "touch /workspace/new.txt"
t "루트 파일시스템 쓰기"                 "touch /usr/local/bin/x"
t "외부 네트워크 접속"                   "python -c 'import urllib.request; urllib.request.urlopen(\"http://example.com\", timeout=5)'"
t "프로세스 65개 만들기"                  "python -c 'import subprocess; ps=[subprocess.Popen([\"sleep\",\"5\"]) for _ in range(65)]'"
