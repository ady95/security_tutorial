# 02-6 실습용 — 일부러 잘못 설정한 Ubuntu 서버 (학습용, 외부에 노출 금지)
FROM ubuntu:24.04

RUN apt-get update \
 && apt-get install -y --no-install-recommends sudo openssh-server \
 && rm -rf /var/lib/apt/lists/*

# 사용자: alice(운영자), ops(서비스 재시작 담당)
RUN useradd -m -s /bin/bash alice && useradd -m -s /bin/bash ops

# [잘못된 설정 1] root가 주기적으로 실행한다고 가정한 백업 스크립트가 누구나 쓸 수 있는 상태
RUN mkdir -p /opt/app \
 && printf '#!/bin/sh\n# root 가 매일 실행하는 백업 스크립트 (실습용 가정)\ntar czf /tmp/app-backup.tgz /opt/app/data 2>/dev/null\n' > /opt/app/backup.sh \
 && chmod 777 /opt/app/backup.sh

# [잘못된 설정 2] 비밀값이 든 설정 파일을 누구나 읽을 수 있음
RUN mkdir -p /opt/app/data \
 && printf 'DB_USER=app\nDB_PASSWORD=lab-only-db-pass-2026\n' > /opt/app/.env \
 && chmod 644 /opt/app/.env

# [잘못된 설정 3] alice 는 비밀번호 없이 모든 명령을 root 로 실행 가능 / ops 는 필요한 명령 하나만 (좋은 예)
RUN echo 'alice ALL=(ALL) NOPASSWD: ALL' > /etc/sudoers.d/alice \
 && echo 'ops ALL=(root) /usr/bin/systemctl restart nginx' > /etc/sudoers.d/ops \
 && chmod 440 /etc/sudoers.d/alice /etc/sudoers.d/ops

# [잘못된 설정 4] SSH 가 root 로그인과 비밀번호 로그인을 허용
#     (/run/sshd 는 SSH 서버가 실행 중이면 있는 디렉터리. 설정 확인 명령 sshd -T 에 필요하다)
RUN printf 'PermitRootLogin yes\nPasswordAuthentication yes\n' > /etc/ssh/sshd_config.d/50-lab.conf \
 && mkdir -p /run/sshd

# [잘못된 설정 5] 셸 기록에 비밀번호가 남아 있음
RUN printf 'cd /opt/app\nmysql -u app -plab-only-db-pass-2026 appdb\nexit\n' > /home/alice/.bash_history \
 && chown alice:alice /home/alice/.bash_history

COPY audit.sh /usr/local/sbin/audit.sh
RUN chmod 700 /usr/local/sbin/audit.sh

CMD ["sleep", "infinity"]
