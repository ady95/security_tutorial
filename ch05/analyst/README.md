# 05-2 ~ 05-4: evidence-based analysis lab

학습용 가상 자료만 사용합니다. 모델 출력은 후보이며 조치를 실행하지 않습니다.
이 폴더의 requirements.txt를 설치하고 00-4의 .env를 준비한 뒤 실행합니다.

```bash
python analysis_lab.py generate
python analysis_lab.py prepare
python analysis_lab.py ask logs
python analysis_lab.py ask review
docker compose run --rm scanner scan --config rules.yml --metrics=off --disable-version-check --json samples/weak.py > runs/sast-weak.json
python analysis_lab.py compare --llm runs/review-weak-proposal.json --sast runs/sast-weak.json
python analysis_lab.py ask hunt
python -m unittest test_analysis.py -v
docker compose down
```

*.fixture.json과 intel.fixture.md는 작성한 예시이며 모델·Semgrep의 실측 출력이 아닙니다.
외부 API 경로는 해당 모델의 reasoning_effort 지원 값을 확인하세요.
오프라인 verify 명령은 SDK·모델 없이 표본의 형식·근거 참조·정책 하한을 점검합니다.
원본 로그 전체를 모델에 넣지 않습니다. prepare는 분별 집계와 각 그룹의 처음·마지막 두 기록만 남기며
100개 그룹·16,000자 예산을 넘으면 실패합니다. 누락된 필드와 표본 밖 기록은 사람이 원본에서 확인해야 합니다.

결과 파일 이름: ask logs → runs/logs-*, ask hunt → runs/hunt-*, ask review는 대상 파일별로 runs/review-weak-*·review-fixed-*,
verify는 이름 뒤에 -verify를 붙여 모델 결과를 덮어쓰지 않습니다. 실행을 시작할 때 같은 이름의 이전 결과를 먼저 지웁니다.
verify logs는 runs/prepared.json이 필요하므로 generate·prepare를 먼저 실행합니다. verify review·hunt는 바로 실행할 수 있습니다.
llm.py는 주소에 11434가 있으면 Ollama로 보고 reasoning_effort 기본값(none)과 max_tokens를 씁니다. Ollama를 다른 포트로 띄웠다면 .env의 LLM_REASONING_EFFORT를 직접 지정하세요.
