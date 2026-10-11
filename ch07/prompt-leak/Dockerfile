FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd -r -u 10001 lab
COPY *.py .
ENV PYTHONDONTWRITEBYTECODE=1
USER 10001:10001
CMD ["python", "app.py"]
