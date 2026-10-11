# 11장 Team Lab

작성한 위협 모델과 고정 감사 표본을 검토하는 로컬 랩입니다. sample_audit.jsonl은 작성 표본이며 모델 실측 로그가 아닙니다. 외부 공격·메일 발송은 없습니다.

```bash
docker compose build
docker compose run --rm lab python team_lab.py model
docker compose run --rm lab python team_lab.py evaluate --version 1
docker compose run --rm lab python team_lab.py evaluate --version 2
docker compose run --rm lab python -m unittest test_team_lab -v
docker compose down
```

위협 모델은 노드 7·흐름 7·위협 5개입니다. 검사는 연결과 필수 필드만 확인하며 의미와 위험의 충분성은 사람이 검토합니다. 고정 8개 trace에서는 v1 TP/FP/FN/TN=2/1/2/3, v2=4/0/0/4입니다. 같은 표본에 맞춘 작은 규칙의 결과이며 운영 성능을 나타내지 않습니다.

외부 after-read 메일, after-read 삭제, 가짜 인증 표식의 기록을 탐지합니다. approve는 정책 판단입니다. 결과가 승인 대기인지도 확인하며 실행·발송 성공은 실제 파일 효과로 대조합니다. 실제 ch12/project 실행 폴더의 audit/audit.jsonl을 --input으로 받아 detect할 수 있습니다. evaluate의 정답표는 작성 표본 전용입니다. 전체 실제 감사 원문에는 민감한 값이 있을 수 있으므로 공개 저장소에 복사하지 않습니다.

시나리오 입력과 전후 도구 효과는 ch12/project/redteam_lab.py에서 확인합니다. 먼저 replay로 가드를 확인하고, live로 모델 경로를 확인합니다. 둘의 결과를 합산하지 않습니다.
