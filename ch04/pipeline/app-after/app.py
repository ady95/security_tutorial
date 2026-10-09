"""04-9 파이프라인 실습용 작은 앱 — 고친 후"""
import os

from flask import Flask

app = Flask(__name__)


@app.get("/")
def home():
    return "pipeline demo"


if __name__ == "__main__":
    # 고침 1: 디버그 모드는 환경변수로만 켤 수 있고 기본은 꺼짐
    # 고침 2: 기본은 내 PC 안(127.0.0.1)에서만 접속. 컨테이너처럼 꼭 필요할 때만 APP_HOST=0.0.0.0 으로 연다
    app.run(
        host=os.environ.get("APP_HOST", "127.0.0.1"),
        port=5000,
        debug=os.environ.get("FLASK_DEBUG") == "1",
    )
