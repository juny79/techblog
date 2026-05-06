# 섹션 11 — 자주 발생하는 오류 및 해결 방법

**이전 단계:** [섹션 10 — 에이전트 설정 튜닝](./section-10-tuning.md)  
**다음 단계:** [섹션 12 — 보안 체크리스트](./section-12-security.md)

---

## 개요

에이전트 시스템 운영 중 발생하는 오류 유형과 단계별 해결 방법을 정리합니다.  
오류 발생 시 **로그에서 오류 메시지를 확인**한 후 해당 항목을 찾아 해결하세요.

---

## 11-1. LLM API 오류

### ❌ `AuthenticationError: Incorrect API key provided`

**증상:** 콘텐츠 생성, SEO 최적화 에이전트 실행 즉시 실패  
**로그 패턴:**
```
openai.AuthenticationError: Incorrect API key provided: sk-xxx...
```

**원인 및 해결:**

1. `.env` 파일의 API 키 값 확인
   ```powershell
   python -c "from core.config import settings; print(repr(settings.openai_api_key[:20]))"
   ```
   - 앞뒤 공백이 포함되어 있으면 제거합니다.
   - `sk-`로 시작하지 않으면 잘못된 키입니다.

2. OpenAI 대시보드에서 키 상태 확인  
   https://platform.openai.com/api-keys → 키가 `Active` 상태인지 확인

3. 키 재생성 후 `.env` 파일 업데이트
   ```powershell
   # .env 수정 후 Worker 재시작 필요
   docker compose restart techblog-worker
   ```

---

### ❌ `RateLimitError: Rate limit reached for gpt-4o`

**증상:** 동시 요청이 많을 때 일부 에이전트가 실패  
**로그 패턴:**
```
openai.RateLimitError: Rate limit reached for model `gpt-4o` in organization ...
```

**해결:**

1. `config/settings.yaml`에서 재시도 간격 증가
   ```yaml
   agents:
     content_generation:
       retry_delay: 30      # 재시도 대기 시간(초) 증가
       max_retries: 5
   ```

2. 동시 실행 수 제한 (`orchestrator/thanos.py`)
   ```python
   # 기존: asyncio.Semaphore(2) → 1로 줄이기
   self._semaphore = asyncio.Semaphore(1)
   ```

3. GPT-4o-mini로 전환 (Rate Limit이 더 높음)
   ```yaml
   llm:
     openai:
       model: gpt-4o-mini
   ```

---

### ❌ `InsufficientQuotaError: You exceeded your current quota`

**증상:** API 잔여 크레딧 소진  
**해결:**
1. https://platform.openai.com/settings/organization/billing 에서 결제 정보 확인
2. 크레딧 충전 또는 월 한도 증가
3. 임시 방편으로 Anthropic 폴백 활성화:
   ```dotenv
   ANTHROPIC_API_KEY=sk-ant-xxxxxx
   ```
   `config/settings.yaml`:
   ```yaml
   llm:
     default: anthropic
   ```

---

## 11-2. 티스토리 API 오류

### ❌ `Tistory API error: status 400`

**증상:** 게시 에이전트 실패  
**로그 패턴:**
```
TistoryAPIError: {'tistory': {'status': '400', 'error_message': '...'}}
```

**원인별 해결:**

| 오류 메시지 | 원인 | 해결 |
|-----------|------|------|
| `access_token is not valid` | Access Token 만료 또는 오류 | 섹션 02의 Phase A~C 재실행 |
| `blog is not found` | 블로그 이름 오류 | `.env`의 `TISTORY_BLOG_NAME` 재확인 |
| `category is not exist` | 카테고리 ID 오류 | 섹션 02의 2-3절 카테고리 ID 재확인 |
| `content is empty` | 본문 HTML 변환 실패 | 마크다운 내 특수문자 확인 |

**Access Token 재발급 절차 요약:**

```powershell
# Step 1: 브라우저에서 Authorization Code 요청
# https://www.tistory.com/oauth/authorize?client_id={APP_ID}&redirect_uri=http://localhost:8000/callback&response_type=code

# Step 2: Access Token 교환
$APP_ID = "..."
$SECRET = "..."
$CODE   = "..."   # 브라우저 주소창에서 복사
Invoke-RestMethod -Uri "https://www.tistory.com/oauth/access_token?client_id=$APP_ID&client_secret=$SECRET&redirect_uri=http://localhost:8000/callback&code=$CODE&grant_type=authorization_code"

# Step 3: .env 업데이트
# TISTORY_ACCESS_TOKEN=새로운_토큰값
```

---

### ❌ `ConnectionError: Failed to connect to www.tistory.com`

**증상:** 티스토리 API 연결 자체가 안 됨  
**해결:**
1. 인터넷 연결 확인: `Invoke-RestMethod -Uri https://www.tistory.com`
2. 방화벽/프록시 설정 확인
3. DNS 확인: `Resolve-DnsName www.tistory.com`

---

## 11-3. 데이터베이스 오류

### ❌ `asyncpg.exceptions.ConnectionRefusedError`

**증상:** 데이터베이스 관련 모든 작업 실패  
**로그 패턴:**
```
asyncpg.exceptions.ConnectionRefusedError: Connection refused
```

**해결:**
```powershell
# PostgreSQL 컨테이너 상태 확인
docker compose ps postgres

# 컨테이너가 없거나 stopped 상태라면
docker compose up -d postgres

# 헬스체크 대기 후 재확인
Start-Sleep -Seconds 15
docker compose ps postgres
```

---

### ❌ `sqlalchemy.exc.ProgrammingError: relation "posts" does not exist`

**증상:** 테이블이 없음  
**해결:** 데이터베이스 초기화 재실행
```powershell
python -c "import asyncio; from core.database import init_db; asyncio.run(init_db())"
```

---

### ❌ `asyncpg.exceptions.TooManyConnectionsError`

**증상:** DB 연결 풀 소진  
**해결:**
```yaml
# config/settings.yaml
database:
  pool_size: 5          # 기본값: 10 → 낮추기
  max_overflow: 10
```

또는 PostgreSQL 설정에서 최대 연결 수 증가:
```powershell
docker exec techblog-postgres psql -U techblog -c "SHOW max_connections;"
# docker-compose.yml의 postgres 서비스에 command 추가:
# command: postgres -c max_connections=200
```

---

## 11-4. Redis / Celery 오류

### ❌ `redis.exceptions.ConnectionError: Error connecting to Redis`

**해결:**
```powershell
docker compose up -d redis

# Redis 연결 확인
docker exec techblog-redis redis-cli ping
# 출력: PONG
```

---

### ❌ Worker가 태스크를 수신하지 못함

**확인 절차:**
```powershell
# Worker 상태 확인
celery -A orchestrator.thanos inspect ping

# 등록된 태스크 확인
celery -A orchestrator.thanos inspect registered

# 활성 태스크 확인
celery -A orchestrator.thanos inspect active
```

**Worker 응답 없음 → 재시작:**
```powershell
# Docker
docker compose restart techblog-worker

# 로컬: Worker 터미널에서 Ctrl+C 후 재실행
celery -A orchestrator.thanos worker --loglevel=debug --concurrency=1
```

---

### ❌ `kombu.exceptions.OperationalError: [Errno 111] Connection refused`

**원인:** Celery가 Redis에 연결할 수 없음  
**해결:**
```powershell
# .env의 REDIS_URL 확인
python -c "from core.config import settings; print(settings.redis_url)"

# Redis 컨테이너 재시작
docker compose restart redis
```

---

## 11-5. 품질 검수 반복 실패

### ❌ `QualityCheckError: 글자 수 부족` 반복 발생

**원인:** LLM이 지속적으로 짧은 콘텐츠를 생성  
**해결:**

1. `config/settings.yaml`에서 목표 분량 일시 하향 조정:
   ```yaml
   blog:
     target_word_count: 1500    # 2500 → 1500
     min_word_count: 800        # 1500 → 800
   ```

2. `content_generation_agent.py`의 프롬프트에서 분량 요구를 더 명시적으로 지정:
   ```python
   f"반드시 {target_word_count}자 이상의 한국어로 작성하세요. 이 분량 미달 시 재작성이 필요합니다."
   ```

3. `max_tokens` 증가:
   ```yaml
   llm:
     openai:
       max_tokens: 6000    # 4096 → 6000
   ```

---

### ❌ `QualityCheckError: SEO 점수 미달` 반복 발생

**해결:**
1. `seo_optimization_agent.py`의 최소 SEO 점수 기준 일시 하향:
   ```python
   MIN_SEO_SCORE = 60.0    # 70.0 → 60.0
   ```

2. SEO 에이전트가 생성하는 태그 수 증가:
   ```python
   SEO_SYSTEM_PROMPT = "... 태그는 반드시 8개 이상 생성하세요. ..."
   ```

---

## 11-6. 이미지 생성 오류

### ❌ `openai.BadRequestError: Your request was rejected as a result of our safety system`

**원인:** DALL-E 3 안전 정책 위반 프롬프트  
**해결:**
`agents/image_generation_agent.py`의 이미지 프롬프트를 더 중립적으로 수정합니다.

```python
# 기술 블로그용 안전한 이미지 프롬프트 템플릿
SAFE_PROMPT = (
    "A clean, professional technology infographic for a Korean tech blog post about {topic}. "
    "Abstract shapes, code snippets, digital art style. No people, no text overlay. "
    "Colors: dark blue, white, light gray. Corporate and modern design."
)
```

---

### ❌ 이미지 파일이 저장되지 않음

**확인:**
```powershell
# storage/images 폴더 존재 확인
Test-Path storage\images
# False라면 생성
New-Item -ItemType Directory -Force -Path storage\images

# 쓰기 권한 확인
"test" | Out-File "storage\images\test.txt"
Remove-Item "storage\images\test.txt"
```

---

## 11-7. Docker 관련 오류

### ❌ `docker: Error response from daemon: Ports are not available`

```powershell
# 포트 사용 프로세스 확인
netstat -ano | Select-String ":5432"
netstat -ano | Select-String ":6379"

# 해당 PID 종료 (예: 1234)
Stop-Process -Id 1234 -Force

# 또는 docker-compose.yml 포트 변경
# "127.0.0.1:5433:5432"  ← 5432 → 5433
```

---

### ❌ `WARN[0000] /path/docker-compose.yml: the attribute 'version' is obsolete`

**원인:** Docker Compose v2에서 `version` 속성 불필요  
**해결:** `docker-compose.yml` 파일 첫 줄의 `version: "3.9"` 라인을 삭제합니다.

---

## 11-8. 진단 도구 — 오류 원인 자동 분석

```python
# ops/diagnose.py
import asyncio
import os

async def diagnose():
    results = []

    # 1. 환경 변수 확인
    from core.config import settings
    results.append(("OPENAI_API_KEY 설정",   bool(settings.openai_api_key)))
    results.append(("TISTORY_ACCESS_TOKEN 설정", bool(settings.tistory_access_token)))
    results.append(("TISTORY_BLOG_NAME 설정",    bool(settings.tistory_blog_name)))

    # 2. PostgreSQL 연결
    try:
        from core.database import AsyncSessionFactory
        from sqlalchemy import text
        async with AsyncSessionFactory() as s:
            await s.execute(text("SELECT 1"))
        results.append(("PostgreSQL 연결", True))
    except Exception as e:
        results.append(("PostgreSQL 연결", False))

    # 3. Redis 연결
    try:
        import redis
        r = redis.Redis(host="127.0.0.1", port=6379)
        r.ping()
        results.append(("Redis 연결", True))
    except Exception:
        results.append(("Redis 연결", False))

    # 4. OpenAI API 연결
    try:
        import openai
        client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        await client.models.list()
        results.append(("OpenAI API 연결", True))
    except Exception:
        results.append(("OpenAI API 연결", False))

    # 5. 이미지 저장 폴더
    results.append(("storage/images 폴더 존재", os.path.isdir("storage/images")))

    print("=" * 50)
    print("  시스템 진단 결과")
    print("=" * 50)
    all_ok = True
    for name, ok in results:
        print(f"  {'✅' if ok else '❌'}  {name}")
        if not ok:
            all_ok = False
    print("=" * 50)
    if all_ok:
        print("  모든 항목 정상")
    else:
        print("  ❌ 항목을 위 섹션에서 확인하세요")

asyncio.run(diagnose())
```

```powershell
python ops/diagnose.py
```

---

## 오류 유형 빠른 찾기

| 오류 키워드 | 해당 섹션 |
|-----------|---------|
| `AuthenticationError` | 11-1 |
| `RateLimitError` | 11-1 |
| `InsufficientQuotaError` | 11-1 |
| `Tistory API error 400` | 11-2 |
| `access_token is not valid` | 11-2 |
| `ConnectionRefusedError` (DB) | 11-3 |
| `relation does not exist` | 11-3 |
| `redis.ConnectionError` | 11-4 |
| `Worker 태스크 수신 안됨` | 11-4 |
| `QualityCheckError 글자 수` | 11-5 |
| `QualityCheckError SEO` | 11-5 |
| `DALL-E safety system` | 11-6 |
| `Ports are not available` | 11-7 |

---

**다음 단계:** [섹션 12 — 보안 체크리스트](./section-12-security.md)
