# 지시·검색·출력·도구 경계 실습

07-2, 07-7, 08-3, 09-3이 공유하는 독립 실습입니다. 실제 서비스, 비밀값, 메일 발송은 없습니다.
저장 도구는 실행별 runs 폴더의 note.txt 하나만 씁니다. output 사례는 고정된 무해한
HTML 이벤트와 printf 두 번을 사용합니다. 임의 문자열을 셸 실행에 연결하지 마세요.

## 로컬 모델 경로

다른 장의 랩을 먼저 종료합니다(동일한 10.30.0.0/24 서브넷 사용).
Docker Compose와 Python 3.12 이미지, Ollama 0.35.0을 사용합니다.
프로젝트 이름은 secbook-ch07-boundary입니다. 07-4의 secbook-ch07-prompt-leak과 이름을 구분하지만
같은 서브넷이므로 둘을 동시에 띄우지 않습니다. 호스트 포트를 공개하지 않습니다.
모델 다운로드용 네트워크는 Ollama만 사용합니다.

lab은 기본 UID:GID 1000:1000으로 실행하여 바인드 폴더에 runs를 씁니다. Linux·WSL2에서는
아래 환경변수로 호스트 계정과 맞추세요. macOS·Windows Docker Desktop은 우선 기본값을 사용하고,
쓰기 오류가 나면 폴더 공유 설정과 소유권을 확인합니다. cap_drop은 그대로 유지합니다.

```bash
export LAB_UID=$(id -u)
export LAB_GID=$(id -g)
```

```bash
cd security_tutorial/ch07/boundary-lab
docker compose up -d ollama
docker compose exec ollama ollama pull qwen3.5:4b
docker compose exec ollama ollama pull qwen3-embedding:0.6b
docker compose run --rm lab python -m unittest -v
docker compose run --rm lab python lab.py normal --mode weak
docker compose run --rm lab python lab.py direct --mode weak
docker compose run --rm lab python lab.py indirect --mode fixed
docker compose run --rm lab python lab.py output
docker compose run --rm lab python lab.py rag-fact --mode weak
docker compose run --rm lab python lab.py rag-instruction --mode fixed
docker compose run --rm lab python lab.py chatbot
docker compose run --rm lab python lab.py agent --mode weak
docker compose run --rm lab python lab.py agent --mode fixed
docker compose run --rm lab python lab.py agent --engine replay --mode fixed
docker compose down
```

rag-normal은 오염 없는 검색 기준선, agent-normal은 저장 지시 없는 주문 조회 대조군입니다.
각 사례에 weak/fixed를 적용해 비교합니다. normal/direct/indirect는 입력 구분과 좁은 출력
표식 검사를 비교하고, rag는 보호된 원본 목록·해시 검사를, agent는 실행 직전의 조회 전용
권한을 비교합니다. 모든 방어를 한꺼번에 켜는 프로그램이 아닙니다.

runs/실행번호/result.json에 원응답, 검색 순위 또는 도구 이벤트가 남습니다.
status=inconclusive 또는 종료 코드 2는 오류·시간/단계 제한이며 차단 성공이 아닙니다.
실제 쓰기 여부 effect는 별도로 읽습니다. 요청별 시간 제한 180초, Agent 최대 3단계입니다.
모델·임베딩 이름, 환경변수와 실행 횟수를 결과와 함께 보관하세요.

output은 모델 응답을 대신하는 고정 표본입니다. weak.html/fixed.html을 로컬 브라우저로
열어 개발자 도구에서 document.body.dataset.lab을 비교할 수 있습니다.
명령 표본은 Linux 컨테이너에서만 실행합니다. 브라우저 검증은 Python 시험과 별개입니다.

## API 설정

Python 표준 라이브러리로 OpenAI 호환 chat/completions와 embeddings를 호출합니다.
OPENAI_BASE_URL, OPENAI_API_KEY, OPENAI_MODEL로 전환하며 기본은 로컬 모델입니다.
LLM_REASONING_EFFORT=none을 사용합니다. 외부 제공자가 지원하지 않으면 빈 값으로 지정합니다.
LLM_TOKEN_FIELD는 기본 max_tokens이며 필요한 제공자는 max_completion_tokens로 설정합니다.
EMBED_MODEL은 같은 엔드포인트의 임베딩 모델입니다. 기본 임베딩 이름을 외부 API에 보내면
동작하지 않으므로 해당 제공자의 이름도 지정해야 합니다. 서로 다른 임베딩의 벡터는 섞지 않습니다.

이 Compose는 격리된 로컬 모델 전용입니다. 외부 API를 사용하려면 07-4처럼 별도의 제한된
중계 경로를 설계해야 하며, lab 네트워크의 격리를 해제하는 식으로 해결하지 않습니다.
외부 API 연결 구성과 실행은 이 예제의 검증 범위에 포함하지 않습니다.

## 해석의 한계

표식 검사는 표현 변형·의미 왜곡을 검출하지 못합니다. JSON 구분은 인가 경계가 아닙니다.
manifest는 공격자가 바꿀 수 없는 코드에 둔 학습용 원본 목록입니다. 실제 운영에서는
승인 권한·목록 갱신·롤백 보호가 별도로 필요합니다. 새 파일명뿐 아니라 승인 이름으로
내용을 교체한 경우도 test_lab.py에서 확인합니다.
replay는 저장 요청을 직접 넣어 정책을 시험하며 모델의 주입 성공률을 측정하지 않습니다.
