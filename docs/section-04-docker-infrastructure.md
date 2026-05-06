# 섹션 04 — 인프라 실행 : Docker Compose

**이전 단계:** [섹션 03 — 프로젝트 환경 세팅](./section-03-project-environment.md)  
**다음 단계:** [섹션 05 — 데이터베이스 초기화](./section-05-database-init.md)

---

## 개요

에이전트 시스템은 두 가지 인프라 서비스에 의존합니다.

| 서비스 | 역할 | Docker 이미지 |
|-------|------|-------------|
| **PostgreSQL 16** | 포스트 이력, 분석 데이터, Human Review 큐 저장 | `postgres:16-alpine` |
| **Redis 7** | Celery 태스크 큐 및 결과 백엔드 | `redis:7-alpine` |

이 섹션에서는 Docker Compose를 이용해 두 서비스를 실행하고, 연결 상태를 검증합니다.

---

## 4-1. docker-compose.yml 내용 확인

```powershell
Get-Content docker-compose.yml
```

주요 서비스 정의를 확인합니다.

```yaml
services:
  postgres:
    image: postgres:16-alpine
    container_name: techblog-postgres
    environment:
      POSTGRES_USER: techblog
      POSTGRES_PASSWORD: password      # 프로덕션에서는 반드시 변경
      POSTGRES_DB: techblog
    ports:
      - "127.0.0.1:5432:5432"          # 로컬호스트에서만 접근 가능
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U techblog"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: techblog-redis
    ports:
      - "127.0.0.1:6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5
```

---

## 4-2. PostgreSQL / Redis 컨테이너 실행

```powershell
# 프로젝트 루트에서 실행
docker compose up -d postgres redis
```

**실행 중 출력 예시:**
```
[+] Running 3/3
 ✔ Network techblog_default     Created
 ✔ Container techblog-postgres  Started
 ✔ Container techblog-redis     Started
```

---

## 4-3. 컨테이너 상태 확인

### 실행 상태 확인

```powershell
docker compose ps
```

**정상 상태 (healthy):**
```
NAME                STATUS              PORTS
techblog-postgres   Up (healthy)        127.0.0.1:5432->5432/tcp
techblog-redis      Up (healthy)        127.0.0.1:6379->6379/tcp
```

> `starting` 상태라면 헬스체크가 완료될 때까지 10~30초 기다린 후 재확인합니다.  
> `unhealthy` 상태라면 4-6절 트러블슈팅을 참고하세요.

### 컨테이너 로그 확인

```powershell
# PostgreSQL 시작 로그
docker compose logs postgres

# Redis 시작 로그
docker compose logs redis
```

**PostgreSQL 정상 시작 로그 (마지막 부분):**
```
LOG:  database system is ready to accept connections
```

**Redis 정상 시작 로그:**
```
* Ready to accept connections tcp
```

---

## 4-4. PostgreSQL 연결 직접 테스트

### psql 클라이언트로 연결

```powershell
docker exec -it techblog-postgres psql -U techblog -d techblog
```

psql 프롬프트(`techblog=#`)가 나타나면 연결 성공입니다.

```sql
-- 현재 데이터베이스 확인
\conninfo

-- 종료
\q
```

**정상 출력:**
```
You are connected to database "techblog" as user "techblog" via socket in "/var/run/postgresql" at port "5432".
```

### Python에서 PostgreSQL 연결 테스트

```python
# test_db_connection.py
import asyncio
import asyncpg

async def test():
    try:
        conn = await asyncpg.connect(
            user="techblog",
            password="password",
            database="techblog",
            host="127.0.0.1",
            port=5432
        )
        version = await conn.fetchval("SELECT version()")
        print(f"✅ PostgreSQL 연결 성공")
        print(f"   버전: {version[:60]}...")
        await conn.close()
    except Exception as e:
        print(f"❌ PostgreSQL 연결 실패: {e}")

asyncio.run(test())
```

```powershell
pip install asyncpg   # 아직 미설치 시
python test_db_connection.py
```

---

## 4-5. Redis 연결 직접 테스트

### redis-cli로 연결

```powershell
docker exec -it techblog-redis redis-cli
```

```
127.0.0.1:6379> PING
PONG
127.0.0.1:6379> SET test "techblog-ok"
OK
127.0.0.1:6379> GET test
"techblog-ok"
127.0.0.1:6379> DEL test
(integer) 1
127.0.0.1:6379> exit
```

### Python에서 Redis 연결 테스트

```python
# test_redis_connection.py
import redis

try:
    r = redis.Redis(host="127.0.0.1", port=6379, decode_responses=True)
    r.set("test_key", "techblog_ok", ex=10)
    value = r.get("test_key")
    print(f"✅ Redis 연결 성공: {value}")
    r.delete("test_key")
except Exception as e:
    print(f"❌ Redis 연결 실패: {e}")
```

```powershell
python test_redis_connection.py
```

---

## 4-6. 트러블슈팅 — 컨테이너 시작 오류

### 오류: `port is already allocated`

**원인:** 5432번 또는 6379번 포트를 이미 다른 프로세스가 사용 중입니다.

**해결 (Windows):**
```powershell
# 5432 포트 사용 프로세스 확인
netstat -ano | Select-String ":5432"

# PID 확인 후 해당 프로세스 종료 (예: PID 1234)
Stop-Process -Id 1234 -Force
```

**또는 `docker-compose.yml`의 포트를 변경:**
```yaml
ports:
  - "127.0.0.1:5433:5432"   # 5432 → 5433 으로 변경
```

변경 시 `.env`의 `DATABASE_URL`도 함께 수정합니다.
```dotenv
DATABASE_URL=postgresql+asyncpg://techblog:password@localhost:5433/techblog
```

---

### 오류: `unhealthy` 상태 지속

```powershell
# 상세 컨테이너 정보 확인
docker inspect techblog-postgres | Select-String -Pattern "Status|Error" -Context 2

# 컨테이너 재시작
docker compose restart postgres
```

---

### 오류: `Error response from daemon: No such container`

```powershell
# 기존 컨테이너 완전 제거 후 재생성
docker compose down
docker compose up -d postgres redis
```

---

### 오류: Docker Desktop이 실행 중이지 않음

```
error during connect: ... The system cannot find the file specified.
```

Docker Desktop 앱을 먼저 실행한 후 시스템 트레이의 고래 아이콘이 정지 상태가 될 때까지 기다립니다.

---

## 4-7. 컨테이너 관리 명령 참고

```powershell
# 서비스 중지 (데이터 보존)
docker compose stop postgres redis

# 서비스 재시작
docker compose restart postgres redis

# 전체 삭제 (데이터까지 삭제 — 주의!)
docker compose down -v

# 컨테이너 내부 접속
docker exec -it techblog-postgres bash
docker exec -it techblog-redis sh

# 실시간 로그 스트리밍
docker compose logs -f postgres
docker compose logs -f redis
```

---

## 4-8. 데이터 볼륨 위치 확인

Docker 볼륨에 저장된 데이터는 컨테이너를 삭제해도 유지됩니다.

```powershell
# 볼륨 목록 확인
docker volume ls | Select-String "techblog"

# 볼륨 상세 정보
docker volume inspect techblog_postgres_data
```

> `docker compose down -v` 명령은 볼륨까지 삭제합니다.  
> 기존 데이터가 필요하다면 절대 `-v` 옵션을 사용하지 마세요.

---

## 완료 기준

- [ ] `docker compose ps` → postgres, redis 모두 `Up (healthy)` 상태
- [ ] PostgreSQL 연결 테스트 성공 (psql 또는 Python)
- [ ] Redis 연결 테스트 성공 (redis-cli 또는 Python)

모든 항목 완료 후 → **[섹션 05](./section-05-database-init.md)** 로 이동
