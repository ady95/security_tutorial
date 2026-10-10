# 12장 프로젝트 Agent 이미지 — 코드와 문서는 이미지에 넣고, 실행 중에는 읽기 전용으로 쓴다
FROM python:3.12-slim
RUN pip install --no-cache-dir "openai>=1.50" "python-dotenv>=1.0" \
 && pip uninstall -y pip setuptools wheel
WORKDIR /app
COPY *.py policy.json ./
COPY docs ./docs
COPY workspace /workspace
ENV WORKSPACE=/workspace OUTPUT=/output INDEX_PATH=/data/index.json AUDIT_DIR=/audit
USER 10001:10001
CMD ["python", "agent.py"]
