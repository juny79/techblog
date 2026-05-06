# 섹션 08 — 자동 스케줄 실행 : Celery Worker & Beat 기동

**이전 단계:** [섹션 07 — 전체 파이프라인 테스트](./section-07-pipeline-test.md)  
**다음 단계:** [섹션 09 — 운영 중 관리 방법](./section-09-operations.md)

---

## 개요

섹션 07의 수동 1회 실행이 성공적으로 완료되면, 이제 Celery를 통해 매일 자동으로 파이프라인이 실행되도록 설정합니다.

**Celery 구성 요소:**

| 구성 요소 | 역할 |
|---------|------|
| **Celery Worker** | 실제 태스크(파이프라인)를 실행하는 프로세스 |
| **Celery Beat** | 스케줄에 따라 태스크를 Worker에게 발행하는 스케줄러 |
| **Redis (Broker)** | Worker와 Beat 간 메시지 전달 큐 |

---

## 8-1. 등록된 스케줄 확인

`orchestrator/thanos.py`에 정의된 스케줄을 확인합니다.

```python
# orchestrator/thanos.py 의 beat_schedule 섹션
beat_schedule = {
    "daily-topic-discovery": {
        "task": "orchestrator.thanos.task_daily_pipeline",
        "schedule": crontab(hour=6, minute=0),    # 매일 오전 06:00 KST
    },
    "weekly-analytics": {
        "task": "orchestrator.thanos.task_weekly_analytics",
        "schedule": crontab(hour=10, minute=0, day_of_week=1),  # 월요일 오전 10:00 KST
    },
}
```

현재 서버의 시간대가 KST (Asia/Seoul)로 설정되어 있는지 확인합니다.

```powershell
python -c "
from orchestrator.thanos import celery_app
print('Timezone:', celery_app.conf.timezone)
print('Beat schedule:')
for name, cfg in celery_app.conf.beat_schedule.items():
    print(f'  {name}: {cfg[\"schedule\"]}')
"
```

---

## 8-2. 로컬 환경 — 터미널 2개로 Worker + Beat 실행

로컬 개발 환경에서는 터미널 2개를 나란히 열어 실행합니다.

### 터미널 1 — Celery Worker 시작

```powershell
# 가상환경 활성화 (새 터미널에서 반드시 재활성화)
.venv\Scripts\Activate.ps1

# Worker 시작
celery -A orchestrator.thanos worker --loglevel=info --concurrency=2
```

**정상 시작 출력:**
```
 -------------- celery@HOSTNAME v5.4.0 (opalescent)
--- ***** -----
-- ******* ---- Windows-11-10.0.22631-SP0 2026-05-07 09:00:00
- *** --- * ---
- ** ---------- [config]
- ** ---------- .> app:         techblog:0x...
- ** ---------- .> transport:   redis://localhost:6379/0
- ** ---------- .> results:     redis://localhost:6379/0
- *** --- * --- .> concurrency: 2 (prefork)
-- ******* ----
--- ***** ----- [queues]
 -------------- .> celery           exchange=celery ...

[tasks]
  . orchestrator.thanos.task_daily_pipeline
  . orchestrator.thanos.task_weekly_analytics

[2026-05-07 09:00:00,000: INFO/MainProcess] celery@HOSTNAME ready.
```

`celery@HOSTNAME ready.` 메시지가 나타나야 정상입니다.

---

### 터미널 2 — Celery Beat 시작

```powershell
# 새 터미널에서 가상환경 활성화
.venv\Scripts\Activate.ps1

# Beat 시작
celery -A orchestrator.thanos beat --loglevel=info
```

**정상 시작 출력:**
```
celery beat v5.4.0 (opalescent) is starting.
__    -    ... __   -        _
...

[2026-05-07 09:00:00,000: INFO/MainProcess] beat: Starting...
[2026-05-07 09:00:00,000: INFO/MainProcess] Scheduler: Sending due task daily-topic-discovery (orchestrator.thanos.task_daily_pipeline)
```

---

## 8-3. 스케줄 즉시 실행 테스트

스케줄 시간까지 기다리지 않고 태스크를 즉시 실행해 Worker 동작을 검증합니다.

```powershell
# 새 터미널 (가상환경 활성화 후)
python -c "
from orchestrator.thanos import task_daily_pipeline
result = task_daily_pipeline.delay()
print(f'태스크 ID: {result.id}')
print(f'상태: {result.status}')
"
```

Worker 터미널에서 태스크가 수신되고 처리되는 로그를 확인합니다.

```
[2026-05-07 09:00:10,000: INFO/MainProcess] Task orchestrator.thanos.task_daily_pipeline[abc123] received
[2026-05-07 09:00:10,000: INFO/Worker-1] Starting daily pipeline run...
...
[2026-05-07 09:05:30,000: INFO/Worker-1] Snap complete! Published: 1, Failed: 0
[2026-05-07 09:05:30,000: INFO/MainProcess] Task orchestrator.thanos.task_daily_pipeline[abc123] succeeded
```

---

## 8-4. 태스크 실행 결과 확인

```powershell
python -c "
from orchestrator.thanos import celery_app

# 최근 완료된 태스크 결과 조회
inspect = celery_app.control.inspect()
active = inspect.active()
reserved = inspect.reserved()
print('활성 태스크:', active)
print('대기 태스크:', reserved)
"
```

---

## 8-5. Docker Compose — 프로덕션 환경 실행 (권장)

로컬 터미널이 닫혀도 Worker와 Beat가 계속 실행되도록 Docker 컨테이너로 실행합니다.

### docker-compose.yml에 Worker/Beat 서비스 정의 확인

```yaml
  techblog-worker:
    build: .
    container_name: techblog-worker
    command: celery -A orchestrator.thanos worker --loglevel=info --concurrency=4
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - TISTORY_ACCESS_TOKEN=${TISTORY_ACCESS_TOKEN}
      # ... 기타 환경 변수
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - image_storage:/app/storage/images
    restart: unless-stopped

  techblog-scheduler:
    build: .
    container_name: techblog-scheduler
    command: celery -A orchestrator.thanos beat --loglevel=info
    depends_on:
      - techblog-worker
    restart: unless-stopped
```

### 전체 서비스 스택 실행

```powershell
# 전체 서비스 시작 (postgres, redis, worker, scheduler)
docker compose up -d

# 실행 상태 확인
docker compose ps
```

**정상 실행 상태:**
```
NAME                    STATUS
techblog-postgres       Up (healthy)
techblog-redis          Up (healthy)
techblog-worker         Up
techblog-scheduler      Up
```

### Worker 로그 실시간 확인

```powershell
docker compose logs -f techblog-worker
```

### 스케줄러 로그 실시간 확인

```powershell
docker compose logs -f techblog-scheduler
```

---

## 8-6. Celery Flower — 웹 대시보드 (선택)

Celery Flower는 웹 브라우저에서 태스크 실행 현황을 모니터링할 수 있는 대시보드입니다.

```powershell
# Flower 설치
pip install flower

# Flower 실행 (Worker 실행 중인 상태에서)
celery -A orchestrator.thanos flower --port=5555
```

브라우저에서 http://localhost:5555 접속

**대시보드 확인 항목:**
- 등록된 Worker 목록 및 상태
- 완료/실패/활성 태스크 수
- 태스크별 실행 시간 히스토리
- 실시간 태스크 스트림

---

## 8-7. 스케줄 변경 방법

실행 시간을 변경하려면 `orchestrator/thanos.py`의 `beat_schedule`을 수정합니다.

```python
# 예: 매일 오전 9시로 변경
"daily-topic-discovery": {
    "task": "orchestrator.thanos.task_daily_pipeline",
    "schedule": crontab(hour=9, minute=0),
},
```

변경 후 Worker와 Beat를 재시작합니다.

```powershell
# 로컬 환경: 터미널에서 Ctrl+C 후 재실행

# Docker 환경:
docker compose restart techblog-worker techblog-scheduler
```

### Crontab 표현식 참고

| 표현식 | 의미 |
|-------|------|
| `crontab(hour=6, minute=0)` | 매일 오전 06:00 |
| `crontab(hour=9, minute=30)` | 매일 오전 09:30 |
| `crontab(hour=6, minute=0, day_of_week='1-5')` | 평일(월~금) 오전 06:00 |
| `crontab(hour=10, minute=0, day_of_week=0)` | 매주 일요일 오전 10:00 |
| `crontab(minute=0)` | 매 시간 정각 |

---

## 8-8. Worker 정상 종료 및 재시작

```powershell
# 로컬 Worker 정상 종료 (처리 중인 태스크 완료 후 종료)
# Worker 터미널에서
Ctrl + C

# 강제 종료가 필요한 경우
celery -A orchestrator.thanos control shutdown

# Docker Worker 재시작
docker compose restart techblog-worker

# Docker 전체 종료
docker compose stop
```

---

## 완료 기준

- [ ] Celery Worker 정상 시작 (`ready.` 메시지 확인)
- [ ] Celery Beat 정상 시작 (`beat: Starting...` 메시지 확인)
- [ ] `task_daily_pipeline.delay()` 즉시 실행 → Worker가 수신 및 처리 완료
- [ ] (Docker 환경) `docker compose ps` → worker, scheduler 모두 `Up` 상태
- [ ] (선택) Flower 대시보드 http://localhost:5555 접근 확인

모든 항목 완료 후 → **[섹션 09](./section-09-operations.md)** 로 이동
