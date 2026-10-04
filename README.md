# security_tutorial

위키독스 책 《AI 시대의 IT 보안 따라하기 — 해킹의 기초부터 LLM·AI 에이전트 보안까지》의 예제 코드 저장소입니다.

- 책: [https://wikidocs.net/book/21504](https://wikidocs.net/book/21504)

## 주의

이 저장소에는 **학습용으로 일부러 취약하게 만든 코드와 설정**이 들어 있습니다.

- 모든 실습은 자신의 PC 안에 있는 격리된 Docker 랩에서만 실행하세요
- 취약한 예제를 인터넷에 노출된 서버에 배포하지 마세요
- 허가받지 않은 시스템을 대상으로 한 공격은 불법입니다

## 빠른 시작

```bash
git clone https://github.com/ady95/security_tutorial.git
cd security_tutorial
cp .env.example .env          # LLM 경로(Ollama 또는 OpenAI API) 선택
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python ch00/check_env.py      # 실습 환경 점검
```

## 폴더 구성

| 폴더 | 책의 장 | 내용 |
|---|---|---|
| ch00 | 00. 들어가며 | 실습 환경 점검, 최소 랩 |
| ch02 | 02. 네트워크와 시스템 해킹 따라하기 | packet: HTTP·HTTPS 패킷 관찰 / logs: 공격 전후 로그 비교, 속도 제한 |

장을 집필하는 대로 폴더가 추가됩니다.

## 필요 환경

- Windows(WSL2) / macOS / Linux, RAM 16GB 권장, GPU 불필요
- Docker + Docker Compose, Git, Python 3.10 이상
- Ollama(기본) 또는 OpenAI API 키(선택)
