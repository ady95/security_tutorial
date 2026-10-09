#!/usr/bin/env bash
# 04-9 간단한 보안 파이프라인 — 세 가지 자동 점검을 차례로 실행하고, 하나라도 실패하면 실패로 끝난다
#   사용: bash pipeline.sh app-before
#
#   단계          도구              차단 기준
#   Secret 검사   gitleaks          키·토큰으로 보이는 문자열이 하나라도 있으면
#   코드 검사     Semgrep (SAST)    p/python 규칙에 걸리는 코드가 있으면
#   의존성 검사   Trivy (SCA)       HIGH 이상이면서 고친 버전이 나온 취약점이 있으면 (04-7 기준)
set -u
TARGET="${1:?검사할 폴더를 지정하세요 (예: app-before)}"
SRC="$(cd "$TARGET" && pwd)"
declare -A RESULT
fail=0

run_stage() {   # run_stage 이름 명령...
  local name="$1"; shift
  echo "==== [$name]"
  if "$@"; then RESULT[$name]="통과"; else RESULT[$name]="실패"; fail=1; fi
  echo
}

run_stage "Secret 검사" docker run --rm --network none -v "$SRC:/src:ro" \
  zricethezav/gitleaks:v8.30.1 dir /src --no-banner --no-color --redact

run_stage "코드 검사" docker run --rm -v "$SRC:/src:ro" \
  semgrep/semgrep:1.180.0 semgrep scan --config p/python --metrics=off --error --quiet /src

run_stage "의존성 검사" docker run --rm -v "$SRC:/src:ro" -v secbook-trivy-cache:/root/.cache/trivy \
  aquasec/trivy:0.75.0 fs --quiet --scanners vuln --severity HIGH,CRITICAL --ignore-unfixed --exit-code 1 /src

echo "==== 결과 요약 ($TARGET)"
for name in "Secret 검사" "코드 검사" "의존성 검사"; do
  printf '  %-10s %s\n' "$name" "${RESULT[$name]}"
done
if [ $fail -ne 0 ]; then echo "파이프라인 실패 — 배포를 막습니다"; else echo "파이프라인 통과"; fi
exit $fail
