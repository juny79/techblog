# 섹션 09 — 운영 중 관리 방법

**이전 단계:** [섹션 08 — Celery 자동 스케줄 실행](./section-08-celery-schedule.md)  
**다음 단계:** [섹션 10 — 에이전트 설정 튜닝](./section-10-tuning.md)

---

## 개요

자동화 시스템이 정상 가동된 이후의 일상적인 운영 절차를 설명합니다.  
주요 관리 항목은 세 가지입니다.

1. **Human Review Queue 처리** — 품질 기준 미달 포스트 수동 검토
2. **로그 모니터링** — 파이프라인 이상 감지
3. **주간 분석 리포트 확인** — 게시 포스트 성과 추적

---

## 9-1. Human Review Queue 처리

### 큐에 쌓이는 조건

품질 검수(Soul Stone)가 3회 연속 실패하면 해당 포스트는 사람이 검토해야 할 큐에 등록됩니다.  
실패 사유 예시:
- 단어 수 부족 (min_word_count 미달)
- SEO 점수 미달 (< 70점)
- H2 소제목 없음
- 이미지 없음

### 큐 조회

```python
# ops/list_review_queue.py
import asyncio
import json
from sqlalchemy import select
from core.database import AsyncSessionFactory, HumanReviewRecord

async def main():
    async with AsyncSessionFactory() as session:
        result = await session.execute(
            select(HumanReviewRecord)
            .where(HumanReviewRecord.resolved == False)
            .order_by(HumanReviewRecord.queued_at.desc())
        )
        records = result.scalars().all()

    if not records:
        print("✅ Human Review 대기 포스트 없음")
        return

    print(f"⚠ Human Review 대기 포스트: {len(records)}건")
    print("=" * 60)
    for r in records:
        print(f"ID       : {r.id}")
        print(f"주제     : {r.topic_title}")
        issues = json.loads(r.issues) if isinstance(r.issues, str) else r.issues
        print(f"실패 사유: {', '.join(issues)}")
        print(f"대기 시각: {r.queued_at}")
        print("-" * 60)

asyncio.run(main())
```

```powershell
# ops 폴더 생성 후 실행
New-Item -ItemType Directory -Force -Path ops
python ops/list_review_queue.py
```

### 초안 내용 확인 및 수정

```python
# ops/inspect_review_item.py
import asyncio
import json
import sys
from sqlalchemy import select
from core.database import AsyncSessionFactory, HumanReviewRecord

async def main(record_id: str):
    async with AsyncSessionFactory() as session:
        result = await session.execute(
            select(HumanReviewRecord).where(HumanReviewRecord.id == record_id)
        )
        record = result.scalar_one_or_none()

    if not record:
        print(f"ID {record_id} 를 찾을 수 없습니다.")
        return

    draft = json.loads(record.draft_json) if isinstance(record.draft_json, str) else record.draft_json

    print(f"제목   : {draft.get('title', '(없음)')}")
    print(f"단어 수: {len(draft.get('content_markdown', '').split())}")
    print(f"\n--- 본문 앞부분 ---")
    print(draft.get("content_markdown", "")[:500])

# 사용법: python ops/inspect_review_item.py <record_id>
if len(sys.argv) > 1:
    asyncio.run(main(sys.argv[1]))
else:
    print("사용법: python ops/inspect_review_item.py <record_id>")
```

```powershell
python ops/inspect_review_item.py xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

### 검토 완료 처리

검토 후 해당 레코드를 `resolved = True`로 업데이트합니다.

```python
# ops/resolve_review_item.py
import asyncio
import sys
from datetime import datetime
from sqlalchemy import select
from core.database import AsyncSessionFactory, HumanReviewRecord

async def main(record_id: str):
    async with AsyncSessionFactory() as session:
        result = await session.execute(
            select(HumanReviewRecord).where(HumanReviewRecord.id == record_id)
        )
        record = result.scalar_one_or_none()

        if not record:
            print(f"ID {record_id} 를 찾을 수 없습니다.")
            return

        record.resolved = True
        record.resolved_at = datetime.utcnow()
        await session.commit()

    print(f"✅ ID {record_id} 검토 완료 처리되었습니다.")

if len(sys.argv) > 1:
    asyncio.run(main(sys.argv[1]))
else:
    print("사용법: python ops/resolve_review_item.py <record_id>")
```

```powershell
python ops/resolve_review_item.py xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

### 수동 게시 (검토 후 재게시)

초안 내용을 수정한 후 게시 에이전트를 직접 실행할 수 있습니다.

```python
# ops/manual_publish.py
import asyncio
import json
import sys
from sqlalchemy import select
from core.database import AsyncSessionFactory, HumanReviewRecord
from core.models import PostDraft
from agents.publishing_agent import PublishingAgent

async def main(record_id: str):
    async with AsyncSessionFactory() as session:
        result = await session.execute(
            select(HumanReviewRecord).where(HumanReviewRecord.id == record_id)
        )
        record = result.scalar_one_or_none()

    if not record:
        print(f"ID {record_id} 를 찾을 수 없습니다.")
        return

    draft_data = json.loads(record.draft_json) if isinstance(record.draft_json, str) else record.draft_json
    draft = PostDraft(**draft_data)

    agent = PublishingAgent()
    print("게시 중...")
    draft = await agent.execute(draft)
    print(f"✅ 게시 완료: {draft.published_url}")

if len(sys.argv) > 1:
    asyncio.run(main(sys.argv[1]))
else:
    print("사용법: python ops/manual_publish.py <record_id>")
```

---

## 9-2. 로그 모니터링

### Docker 환경 — 실시간 로그 스트리밍

```powershell
# Worker 전체 로그
docker compose logs -f techblog-worker

# 오류 로그만 필터링
docker compose logs -f techblog-worker | Select-String -Pattern "ERROR|CRITICAL|Failed"

# 특정 에이전트 로그만 보기
docker compose logs techblog-worker | Select-String "publishing_agent"

# 오늘 날짜 로그만 보기
$today = Get-Date -Format "yyyy-MM-dd"
docker compose logs techblog-worker | Select-String $today
```

### 로컬 환경 — 로그 파일 저장

```powershell
# 실행 시 로그를 파일로도 저장
python main.py run 2>&1 | Tee-Object -FilePath "logs\run_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
```

### 로그 패턴별 의미

| 로그 패턴 | 의미 |
|---------|------|
| `snap_begin run_id=...` | 새 파이프라인 실행 시작 |
| `Snap complete!` | 파이프라인 정상 완료 |
| `QualityCheckError` | 품질 기준 미달 (재시도 예정) |
| `queued_for_human_review` | Human Review 큐 등록 |
| `LLMClient: OpenAI failed, trying anthropic` | OpenAI 실패, Anthropic 폴백 전환 |
| `Published: https://...` | 티스토리 게시 완료 |
| `ERROR` | 예외 발생 — 상세 메시지 확인 필요 |

### 오류 발생 시 대응 절차

1. **오류 로그 확인**
   ```powershell
   docker compose logs techblog-worker | Select-String "ERROR" | Select-Object -Last 20
   ```

2. **오류 원인 파악** — [섹션 11 — 오류 해결](./section-11-troubleshooting.md) 참조

3. **Worker 재시작**
   ```powershell
   docker compose restart techblog-worker
   ```

4. **수동 재실행** (필요 시)
   ```powershell
   python main.py run --topics "이전에 실패한 주제"
   ```

---

## 9-3. 게시된 포스트 이력 조회

```python
# ops/list_posts.py
import asyncio
from sqlalchemy import select, desc
from core.database import AsyncSessionFactory, PostRecord

async def main():
    async with AsyncSessionFactory() as session:
        result = await session.execute(
            select(PostRecord)
            .order_by(desc(PostRecord.created_at))
            .limit(10)
        )
        posts = result.scalars().all()

    print(f"{'날짜':12} {'상태':10} {'SEO':6} {'단어':6} 제목")
    print("─" * 80)
    for p in posts:
        date = p.created_at.strftime("%m/%d %H:%M") if p.created_at else "?"
        status = p.pipeline_status or "unknown"
        seo = f"{p.seo_score:.0f}" if p.seo_score else "-"
        words = str(p.word_count) if p.word_count else "-"
        title = (p.title or "")[:40]
        print(f"{date:12} {status:10} {seo:6} {words:6} {title}")

asyncio.run(main())
```

```powershell
python ops/list_posts.py
```

---

## 9-4. 주간 분석 리포트 확인

### 자동 수집 주기

매주 월요일 오전 10:00 KST에 `task_weekly_analytics` 태스크가 자동 실행됩니다.

### 수동 실행

```powershell
python main.py analytics
```

**출력 예시:**
```
==================================================
  주간 기술블로그 성과 리포트 (2026-05-07)
==================================================
  총 포스트 수    : 14
  총 조회수       : 6,842
  총 좋아요       : 94
  총 댓글         : 31
  평균 조회수     : 488.7
  최고 성과 포스트: 43 (1,423 views)
==================================================
```

### Slack 알림 설정

`.env` 파일에 Slack Webhook URL을 추가하면 리포트가 Slack으로도 전송됩니다.

```dotenv
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T.../B.../xxx
```

**Slack Webhook URL 생성 방법:**
1. https://api.slack.com/apps 에서 앱 생성
2. **"Incoming Webhooks"** 기능 활성화
3. 알림을 받을 채널 선택 후 Webhook URL 복사

### DB에서 분석 데이터 직접 조회

```python
# ops/analytics_query.py
import asyncio
from sqlalchemy import select, func, desc
from core.database import AsyncSessionFactory, AnalyticsRecord

async def main():
    async with AsyncSessionFactory() as session:
        # 조회수 상위 5개 포스트
        result = await session.execute(
            select(
                AnalyticsRecord.tistory_post_id,
                func.max(AnalyticsRecord.views).label("max_views"),
                func.max(AnalyticsRecord.likes).label("max_likes"),
            )
            .group_by(AnalyticsRecord.tistory_post_id)
            .order_by(desc("max_views"))
            .limit(5)
        )
        rows = result.all()

    print("조회수 상위 5개 포스트:")
    for row in rows:
        print(f"  포스트 {row.tistory_post_id}: {row.max_views}회 조회, {row.max_likes}개 좋아요")

asyncio.run(main())
```

```powershell
python ops/analytics_query.py
```

---

## 9-5. 일일 운영 체크리스트

매일 아침 아래 항목을 확인하는 것을 권장합니다.

```powershell
# 1. 컨테이너 상태
docker compose ps

# 2. 어제 파이프라인 실행 결과
python ops/list_posts.py

# 3. Human Review 대기 항목
python ops/list_review_queue.py

# 4. 오류 로그
docker compose logs --since=24h techblog-worker | Select-String "ERROR"
```

---

## 완료 기준

- [ ] `ops/list_review_queue.py` 실행 및 큐 상태 확인
- [ ] `ops/list_posts.py` 실행 및 최근 게시 이력 확인
- [ ] `python main.py analytics` 실행 및 리포트 확인
- [ ] 로그 모니터링 방법 숙지
- [ ] (선택) Slack 알림 설정 완료

모든 항목 완료 후 → **[섹션 10](./section-10-tuning.md)** 으로 이동
