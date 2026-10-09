"""04-9 파이프라인 실습용 작은 앱 — 고치기 전 (흔한 실수 두 가지가 들어 있다)"""
from flask import Flask

app = Flask(__name__)


@app.get("/")
def home():
    return "pipeline demo"


if __name__ == "__main__":
    # 실수 1: 디버그 모드를 켠 채 모든 주소에서 접속을 받는다
    app.run(host="0.0.0.0", port=5000, debug=True)
