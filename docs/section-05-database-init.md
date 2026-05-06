# 섹션 05 — 데이터베이스 초기화

**이전 단계:** [섹션 04 — Docker 인프라 실행](./section-04-docker-infrastructure.md)  
**다음 단계:** [섹션 06 — 에이전트별 동작 확인](./section-06-agent-verification.md)

---

## 개요

에이전트 시스템이 데이터를 저장할 3개의 테이블을 PostgreSQL에 생성합니다.  
이 작업은 최초 1회만 수행하면 됩니다.

---

## 5-1. 생성될 테이블 구조

### `posts` — 게시 포스트 이력

| 컬럼명 | 타입 | 설명 |
|-------|------|------|
| `id` | UUID | 기본 키 |
| `topic_title` | TEXT | 포스트 주제 |
| `title` | TEXT | 생성된 제목 |
| `tistory_post_id` | INTEGER | 티스토리 포스트 ID |
| `published_url` | TEXT | 게시된 URL |
| `pipeline_status` | TEXT | 파이프라인 상태 (COMPLETED / FAILED 등) |
| `category` | TEXT | 기술 카테고리 |
| `word_count` | INTEGER | 최종 본문 글자 수 |
| `seo_score` | FLOAT | SEO 점수 |
| `created_at` | TIMESTAMP | 생성 시각 |
| `published_at` | TIMESTAMP | 게시 시각 |
| `draft_json` | JSONB | 전체 `PostDraft` 직렬화 데이터 |

### `analytics` — 성과 분석 데이터

| 컬럼명 | 타입 | 설명 |
|-------|------|------|
| `id` | UUID | 기본 키 |
| `post_id` | UUID | `posts.id` 참조 |
| `tistory_post_id` | INTEGER | 티스토리 포스트 ID |
| `views` | INTEGER | 조회수 |
| `likes` | INTEGER | 좋아요 수 |
| `comments` | INTEGER | 댓글 수 |
| `collected_at` | TIMESTAMP | 데이터 수집 시각 |

### `human_review_queue` — Human Review 대기 큐

| 컬럼명 | 타입 | 설명 |
|-------|------|------|
| `id` | UUID | 기본 키 |
| `post_id` | UUID | 관련 포스트 ID |
| `topic_title` | TEXT | 주제 |
| `issues` | JSONB | 품질 검수 실패 사유 목록 |
| `draft_json` | JSONB | 수정 가능한 포스트 초안 |
| `resolved` | BOOLEAN | 검토 완료 여부 |
| `queued_at` | TIMESTAMP | 큐 등록 시각 |
| `resolved_at` | TIMESTAMP | 검토 완료 시각 |

---

## 5-2. 데이터베이스 초기화 실행

가상환경이 활성화된 상태에서 프로젝트 루트에서 실행합니다.

```powershell
python -c "
import asyncio
from core.database import init_db

async def main():
    await init_db()
    print('데이터베이스 초기화 완료')

asyncio.run(main())
"
```

**정상 출력:**
```
데이터베이스 초기화 완료
```

오류 없이 완료되면 3개의 테이블이 생성됩니다.

---

## 5-3. 테이블 생성 확인

psql 클라이언트로 직접 확인합니다.

```powershell
docker exec -it techblog-postgres psql -U techblog -d techblog
```

psql 프롬프트에서:

```sql
-- 테이블 목록 확인
\dt

-- 각 테이블 구조 확인
\d posts
\d analytics
\d human_review_queue

-- 종료
\q
```

**`\dt` 정상 출력:**
```
         List of relations
 Schema |        Name        | Type  |  Owner
--------+--------------------+-------+---------
 public | analytics          | table | techblog
 public | human_review_queue | table | techblog
 public | posts              | table | techblog
(3 rows)
```

---

## 5-4. Python에서 테이블 접근 테스트

```python
# test_db_tables.py
import asyncio
from sqlalchemy import text
from core.database import AsyncSessionFactory

async def test():
    async with AsyncSessionFactory() as session:
        # 각 테이블에 SELECT 쿼리 실행
        tables = ["posts", "analytics", "human_review_queue"]
        for table in tables:
            result = await session.execute(
                text(f"SELECT COUNT(*) FROM {table}")
            )
            count = result.scalar()
            print(f"✅ {table}: {count}건")

asyncio.run(test())
```

```powershell
python test_db_tables.py
```

**정상 출력:**
```
✅ posts: 0건
✅ analytics: 0건
✅ human_review_queue: 0건
```

---

## 5-5. 데이터베이스 재초기화 방법 (초기화가 필요한 경우)

> **주의:** 아래 명령은 모든 데이터를 삭제합니다. 신중히 실행하세요.

```powershell
# 방법 1: Docker 볼륨 삭제 후 재시작 (완전 초기화)
docker compose down -v                    # 볼륨까지 삭제
docker compose up -d postgres redis       # 컨테이너 재시작 (빈 DB)
python -c "import asyncio; from core.database import init_db; asyncio.run(init_db())"

# 방법 2: 테이블만 삭제 후 재생성
docker exec -it techblog-postgres psql -U techblog -d techblog -c "
DROP TABLE IF EXISTS human_review_queue CASCADE;
DROP TABLE IF EXISTS analytics CASCADE;
DROP TABLE IF EXISTS posts CASCADE;
"
python -c "import asyncio; from core.database import init_db; asyncio.run(init_db())"
```

---

## 5-6. 트러블슈팅

### 오류: `asyncpg.exceptions.ConnectionRefusedError`

**원인:** PostgreSQL 컨테이너가 실행 중이지 않습니다.

```powershell
docker compose ps    # 상태 확인
docker compose up -d postgres   # 재실행
```

### 오류: `asyncpg.exceptions.InvalidPasswordError`

**원인:** `.env`의 `DATABASE_URL` 비밀번호가 `docker-compose.yml`의 `POSTGRES_PASSWORD`와 다릅니다.

1. `.env`의 `DATABASE_URL`을 확인합니다:
   ```
   DATABASE_URL=postgresql+asyncpg://techblog:password@localhost:5432/techblog
   ```
2. `docker-compose.yml`의 `POSTGRES_PASSWORD`와 일치하는지 확인합니다.

### 오류: `ModuleNotFoundError: No module named 'asyncpg'`

```powershell
pip install asyncpg
```

---

## 완료 기준

- [ ] `init_db()` 실행 오류 없음
- [ ] `\dt` → posts, analytics, human_review_queue 3개 테이블 확인
- [ ] `test_db_tables.py` → 모든 테이블 `0건` 정상 조회

모든 항목 완료 후 → **[섹션 06](./section-06-agent-verification.md)** 으로 이동
