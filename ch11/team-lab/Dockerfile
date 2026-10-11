FROM python:3.12-slim
WORKDIR /lab
COPY *.py *.json *.jsonl ./
USER 10001:10001
CMD ["python", "team_lab.py", "model"]
