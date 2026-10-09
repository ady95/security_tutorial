#!/bin/sh
# 04-5 커밋 전 검사(pre-commit hook) 설치 — 커밋할 때마다 gitleaks 가 스테이징된 변경을 검사한다
cat > /work/demo-app/.git/hooks/pre-commit <<'HOOK'
#!/bin/sh
gitleaks git --pre-commit --staged --redact --no-banner --no-color --verbose
HOOK
chmod +x /work/demo-app/.git/hooks/pre-commit
echo "pre-commit hook 설치 완료"
