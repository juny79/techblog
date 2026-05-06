# 기술블로그 자동배포를 위한 Agent 세팅 및 절차 상세 안내서

**문서 버전:** v1.0  
**최종 수정일:** 2026년 5월 6일  
**대상 OS:** Windows 10/11, macOS 13+, Ubuntu 22.04+

---

## 목차

1. [시스템 요구사항 확인](#1-시스템-요구사항-확인)
2. [사전 준비 — 외부 서비스 계정 생성](#2-사전-준비--외부-서비스-계정-생성)
   - 2.1 [티스토리 Open API 앱 등록 및 Access Token 발급](#21-티스토리-open-api-앱-등록-및-access-token-발급)
   - 2.2 [OpenAI API 키 발급](#22-openai-api-키-발급)
   - 2.3 [Anthropic API 키 발급 (선택 — 폴백용)](#23-anthropic-api-키-발급-선택--폴백용)
3. [프로젝트 환경 세팅](#3-프로젝트-환경-세팅)
   - 3.1 [Python 가상환경 생성 및 패키지 설치](#31-python-가상환경-생성-및-패키지-설치)
   - 3.2 [환경 변수 파일 (.env) 작성](#32-환경-변수-파일-env-작성)
   - 3.3 [설정 파일 (settings.yaml) 확인 및 수정](#33-설정-파일-settingsyaml-확인-및-수정)
4. [인프라 실행 — Docker Compose](#4-인프라-실행--docker-compose)
5. [데이터베이스 초기화](#5-데이터베이스-초기화)
6. [에이전트별 동작 확인 (단계적 검증)](#6-에이전트별-동작-확인-단계적-검증)
   - 6.1 [Power Stone — 주제 탐색 에이전트](#61-power-stone--주제-탐색-에이전트)
   - 6.2 [Mind Stone — 콘텐츠 생성 에이전트](#62-mind-stone--콘텐츠-생성-에이전트)
   - 6.3 [Reality Stone / Code / Image 에이전트](#63-reality-stone--code--image-에이전트)
   - 6.4 [Soul Stone — 품질 검수 에이전트](#64-soul-stone--품질-검수-에이전트)
   - 6.5 [Space Stone — 게시 에이전트 (티스토리 연동 최종 확인)](#65-space-stone--게시-에이전트-티스토리-연동-최종-확인)
7. [전체 파이프라인 1회 테스트 실행](#7-전체-파이프라인-1회-테스트-실행)
8. [자동 스케줄 실행 — Celery Worker & Beat 기동](#8-자동-스케줄-실행--celery-worker--beat-기동)
9. [운영 중 관리 방법](#9-운영-중-관리-방법)
   - 9.1 [Human Review Queue 처리](#91-human-review-queue-처리)
   - 9.2 [로그 모니터링](#92-로그-모니터링)
   - 9.3 [주간 분석 리포트 확인](#93-주간-분석-리포트-확인)
10. [에이전트 설정 튜닝 가이드](#10-에이전트-설정-튜닝-가이드)
11. [자주 발생하는 오류 및 해결 방법](#11-자주-발생하는-오류-및-해결-방법)
12. [보안 체크리스트](#12-보안-체크리스트)

---

## 1. 시스템 요구사항 확인

아래 항목을 모두 충족해야 에이전트가 정상 동작합니다.

| 항목 | 최소 버전 | 확인 명령 |
|------|----------|-----------|
| Python | 3.12 이상 | `python --version` |
| pip | 24.0 이상 | `pip --version` |
| Docker Desktop | 4.28 이상 | `docker --version` |
| Docker Compose | 2.24 이상 | `docker compose version` |
| Node.js (코드 샌드박스용) | 20 LTS 이상 | `node --version` |
| Git | 2.40 이상 | `git --version` |

> **Windows 사용자 주의:** Python 명령이 `python3`일 경우, 아래 모든 `python` 명령을 `python3`으로 대체하세요.

---

## 2. 사전 준비 — 외부 서비스 계정 생성

### 2.1 티스토리 Open API 앱 등록 및 Access Token 발급

티스토리 API를 통해 포스트를 자동 게시하려면 **OAuth 2.0 Access Token**이 필요합니다.

#### Step 1 — 티스토리 앱 등록

1. 티스토리에 로그인한 상태에서 아래 URL에 접속합니다.  
   👉 https://www.tistory.com/guide/api/manage/register

2. 다음 정보를 입력합니다.

   | 항목 | 입력값 예시 |
   |------|-----------|
   | 앱 이름 | `TechBlog Automation` |
   | 설명 | `기술 블로그 자동 포스팅 에이전트` |
   | 서비스 URL | `http://localhost:8000` |
   | CallBack 경로 | `http://localhost:8000/callback` |

3. 등록 완료 후 **App ID**와 **Secret Key**를 복사해 메모해 둡니다.

#### Step 2 — Authorization Code 발급

브라우저 주소창에 아래 URL을 직접 입력합니다.  
`{APP_ID}` 부분을 발급받은 실제 App ID로 교체하세요.

```
https://www.tistory.com/oauth/authorize
  ?client_id={APP_ID}
  &redirect_uri=http://localhost:8000/callback
  &response_type=code
```

티스토리 로그인 및 권한 허용을 완료하면 브라우저 주소창이 아래와 같이 변경됩니다.

```
http://localhost:8000/callback?code=AUTHORIZATION_CODE_HERE
```

주소창에서 `code=` 뒤의 값을 복사해 둡니다.

#### Step 3 — Access Token 발급

아래 curl 명령을 터미널에서 실행합니다.  
`{APP_ID}`, `{SECRET_KEY}`, `{CODE}` 를 각각 실제 값으로 교체하세요.

```bash
curl -X GET "https://www.tistory.com/oauth/access_token" \
  -G \
  --data-urlencode "client_id={APP_ID}" \
  --data-urlencode "client_secret={SECRET_KEY}" \
  --data-urlencode "redirect_uri=http://localhost:8000/callback" \
  --data-urlencode "code={CODE}" \
  --data-urlencode "grant_type=authorization_code"
```

**응답 예시:**
```
access_token=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

반환된 `access_token` 값을 복사해 둡니다. 이 값은 `.env` 파일의 `TISTORY_ACCESS_TOKEN`에 입력됩니다.

> **토큰 유효기간:** 티스토리 Access Token은 만료 기간이 별도로 명시되지 않으나, 장기간 미사용 또는 비밀번호 변경 시 만료될 수 있습니다. 만료 시 위 절차를 반복해 재발급하세요.

#### Step 4 — 블로그 이름 확인

티스토리 블로그 주소에서 블로그 이름을 확인합니다.

```
https://{블로그이름}.tistory.com
```

예: `https://mytech.tistory.com` → 블로그 이름은 `mytech`

---

### 2.2 OpenAI API 키 발급

1. https://platform.openai.com/signup 에서 계정을 생성합니다.
2. 로그인 후 https://platform.openai.com/api-keys 에 접속합니다.
3. **"Create new secret key"** 버튼을 클릭합니다.
4. 키 이름을 `techblog-agent`로 입력하고 생성합니다.
5. 생성된 키(`sk-...`)를 반드시 즉시 복사합니다. *(창을 닫으면 다시 확인 불가)*

> **비용 절감 팁:**  
> - GPT-4o 기준 포스트 1개 생성 비용: 약 $0.03~0.08  
> - OpenAI 대시보드에서 월 사용 한도(Usage Limit)를 $10~20로 설정하는 것을 권장합니다.  
> - https://platform.openai.com/settings/organization/limits

---

### 2.3 Anthropic API 키 발급 (선택 — 폴백용)

OpenAI API 장애 시 자동으로 Claude로 전환되는 폴백 기능을 사용하려면 Anthropic 키도 발급합니다.

1. https://console.anthropic.com 에서 계정을 생성합니다.
2. **"API Keys"** 메뉴에서 **"Create Key"** 를 클릭합니다.
3. 생성된 키(`sk-ant-...`)를 복사해 둡니다.

> Anthropic 키가 없어도 OpenAI 키만으로 시스템은 정상 동작합니다.

---

## 3. 프로젝트 환경 세팅

### 3.1 Python 가상환경 생성 및 패키지 설치

프로젝트 루트 디렉터리(`techblog/`)에서 아래 명령을 순서대로 실행합니다.

```bash
# 1. 가상환경 생성
python -m venv .venv

# 2. 가상환경 활성화
# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate

# 3. pip 최신화
pip install --upgrade pip

# 4. 패키지 설치
pip install -r requirements.txt
```

설치 완료 후 아래 명령으로 핵심 패키지가 정상 설치되었는지 확인합니다.

```bash
python -c "import openai, anthropic, celery, sqlalchemy, pydantic; print('OK')"
```

출력이 `OK`이면 정상입니다.

---

### 3.2 환경 변수 파일 (.env) 작성

`.env.example` 파일을 복사해 `.env` 파일을 생성합니다.

```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

`.env` 파일을 텍스트 편집기로 열고 아래 항목들을 실제 값으로 채웁니다.

```dotenv
# ─── 필수 항목 ────────────────────────────────────────
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# ─── Tistory (모두 필수) ──────────────────────────────
TISTORY_APP_ID=발급받은_App_ID
TISTORY_SECRET_KEY=발급받은_Secret_Key
TISTORY_ACCESS_TOKEN=발급받은_Access_Token
TISTORY_BLOG_NAME=내블로그이름         # tistory 주소에서 앞부분 (예: mytech)

# ─── 선택 항목 ────────────────────────────────────────
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxx  # 폴백 LLM 사용 시

# ─── 게시 설정 ────────────────────────────────────────
POSTS_PER_DAY=2           # 하루에 자동 생성할 포스트 수
MIN_WORD_COUNT=1500        # 품질 검수 최소 단어 수
```

> **보안 주의:**  
> `.env` 파일은 절대로 Git에 커밋하지 마세요.  
> `.gitignore` 파일에 `.env`가 포함되어 있는지 반드시 확인하세요.

---

### 3.3 설정 파일 (settings.yaml) 확인 및 수정

`config/settings.yaml` 파일에서 블로그 운영 방식을 세부 조정할 수 있습니다.

**주요 조정 항목:**

```yaml
blog:
  posts_per_day: 2           # 1~5 권장. 처음엔 1로 시작 권장
  min_word_count: 1500       # 품질 기준 최소 글자 수
  target_word_count: 2500    # LLM 목표 생성 분량

  tistory:
    visibility: 3            # 3=공개 / 0=비공개 (테스트 시 0으로 설정 권장)
    default_category_id: 1   # 티스토리 블로그의 카테고리 ID

agents:
  topic_discovery:
    topics_per_run: 5        # 1회 실행 시 탐색할 주제 수

  content_generation:
    audience_level: "중급 개발자"   # 독자 수준 (입문자 / 중급 개발자 / 시니어)

llm:
  default: openai            # 기본 LLM (openai / anthropic)
```

> **테스트 단계에서는 `visibility: 0`(비공개)으로 설정**하여 실수로 미완성 포스트가 공개되는 것을 방지하세요.  
> 검증 완료 후 `visibility: 3`(공개)으로 변경합니다.

---

## 4. 인프라 실행 — Docker Compose

PostgreSQL(데이터베이스)과 Redis(메시지 큐)를 Docker로 실행합니다.

```bash
# 컨테이너 빌드 및 백그라운드 실행
docker compose up -d postgres redis

# 실행 상태 확인
docker compose ps
```

**정상 실행 결과:**
```
NAME              STATUS
techblog-postgres Running (healthy)
techblog-redis    Running (healthy)
```

두 서비스 모두 `healthy` 상태여야 합니다. `starting` 상태라면 10~20초 후 다시 확인하세요.

**연결 테스트:**
```bash
# PostgreSQL 연결 확인
docker exec -it techblog-postgres-1 psql -U techblog -d techblog -c "\conninfo"

# Redis 연결 확인
docker exec -it techblog-redis-1 redis-cli ping
# 출력: PONG
```

---

## 5. 데이터베이스 초기화

에이전트가 사용할 테이블을 생성합니다. 프로젝트 루트에서 실행합니다.

```bash
python -c "
import asyncio
from core.database import init_db
asyncio.run(init_db())
print('데이터베이스 초기화 완료')
"
```

**생성되는 테이블:**

| 테이블명 | 용도 |
|---------|------|
| `posts` | 생성·게시된 포스트 메타데이터 |
| `analytics` | 게시 후 수집된 성과 데이터 |
| `human_review_queue` | 품질 검수 실패로 사람 검토가 필요한 포스트 |

---

## 6. 에이전트별 동작 확인 (단계적 검증)

전체 파이프라인을 한 번에 실행하기 전에, 각 에이전트를 독립적으로 테스트합니다.  
문제 발생 시 어느 단계에서 오류가 발생했는지 빠르게 파악할 수 있습니다.

### 6.1 Power Stone — 주제 탐색 에이전트

GitHub Trending, Hacker News, dev.to에서 실시간 기술 주제를 수집합니다.

```python
# test_topic.py
import asyncio
from agents.topic_discovery_agent import TopicDiscoveryAgent

async def main():
    agent = TopicDiscoveryAgent()
    topics = await agent.discover_batch(count=3)
    for t in topics:
        print(f"[{t.trend_score:.0f}점] {t.title}")
        print(f"  카테고리: {t.category} | 키워드: {t.keywords}")
        print()

asyncio.run(main())
```

```bash
python test_topic.py
```

**정상 출력 예시:**
```
[95점] Building a REST API with Rust and Axum
  카테고리: 백엔드 | 키워드: ['REST', 'API', 'Rust', 'Axum']

[87점] Understanding React Server Components in 2026
  카테고리: 프론트엔드 | 키워드: ['React', 'Server', 'Components']
```

---

### 6.2 Mind Stone — 콘텐츠 생성 에이전트

LLM을 호출해 마크다운 블로그 포스트를 생성합니다.  
**OpenAI API 키가 올바르게 설정되어 있어야 합니다.**

```python
# test_content.py
import asyncio
from agents.content_generation_agent import ContentGenerationAgent
from core.models import PostDraft, TopicData

async def main():
    draft = PostDraft(
        topic=TopicData(
            title="Python 비동기 프로그래밍 완벽 정리",
            keywords=["Python", "asyncio", "비동기"],
            category="백엔드",
        )
    )
    agent = ContentGenerationAgent()
    draft = await agent.execute(draft)

    print(f"제목: {draft.title}")
    print(f"본문 길이: {len(draft.content_markdown)} 자")
    print(f"코드 블록 수: {len(draft.code_blocks)}개")
    print("\n--- 본문 앞부분 ---")
    print(draft.content_markdown[:500])

asyncio.run(main())
```

```bash
python test_content.py
```

**정상 출력 예시:**
```
제목: Python 비동기 프로그래밍 완벽 정리
본문 길이: 3124 자
코드 블록 수: 4개

--- 본문 앞부분 ---
## 들어가며

Python 3.4에서 처음 도입된 `asyncio`는 ...
```

---

### 6.3 Reality Stone / Code / Image 에이전트

#### 코드 예제 에이전트 테스트

```python
# test_code.py
import asyncio
from agents.code_example_agent import CodeExampleAgent
from core.models import PostDraft, CodeBlock

async def main():
    draft = PostDraft(title="테스트")
    draft.code_blocks = [
        CodeBlock(index=0, language="python", code="print('Hello, Techblog!')"),
        CodeBlock(index=1, language="python", code="x = 1 / 0  # 의도적 오류"),
    ]
    agent = CodeExampleAgent()
    draft = await agent.execute(draft)

    for block in draft.code_blocks:
        status = "✅ 통과" if block.is_valid else "❌ 실패"
        print(f"블록 {block.index}: {status}")
        if block.fixed_code:
            print(f"  → 자동 수정됨")

asyncio.run(main())
```

```bash
python test_code.py
```

#### 이미지 생성 에이전트 테스트

> **비용 발생:** DALL-E 3 이미지 1장 생성 시 약 $0.04 비용이 발생합니다.  
> 테스트 전 확인 후 실행하세요.

```python
# test_image.py
import asyncio
from agents.image_generation_agent import ImageGenerationAgent
from core.models import PostDraft, TopicData

async def main():
    draft = PostDraft(
        topic=TopicData(title="Python 비동기 프로그래밍")
    )
    agent = ImageGenerationAgent()
    draft = await agent.execute(draft)

    for img in draft.images:
        print(f"[{img.image_type}] {img.local_path} ({img.width}x{img.height})")

asyncio.run(main())
```

```bash
python test_image.py
```

---

### 6.4 Soul Stone — 품질 검수 에이전트

콘텐츠가 최소 기준을 충족하는지 검증합니다.

```python
# test_quality.py
import asyncio
from agents.quality_review_agent import QualityReviewAgent, QualityCheckError
from core.models import PostDraft, TopicData, SEOMetadata, ImageAsset

async def main():
    # 의도적으로 짧은 콘텐츠로 실패 케이스 확인
    draft = PostDraft(title="테스트 포스트")
    draft.content_markdown = "## 소제목\n이것은 짧은 테스트 본문입니다."
    draft.seo = SEOMetadata(readability_score=80.0)

    agent = QualityReviewAgent()
    try:
        draft = await agent.execute(draft)
        print("품질 검수 통과!")
    except QualityCheckError as e:
        print(f"품질 검수 실패 (예상된 결과):")
        for issue in e.issues:
            print(f"  - {issue}")

asyncio.run(main())
```

```bash
python test_quality.py
```

**정상 출력 예시 (의도적 실패):**
```
품질 검수 실패 (예상된 결과):
  - 글자 수 부족: 6 단어 (최소 1500)
  - 이미지 없음 (최소 1장 필요)
```

---

### 6.5 Space Stone — 게시 에이전트 (티스토리 연동 최종 확인)

> **⚠️ 중요:** 이 테스트는 실제 티스토리에 포스트를 생성합니다.  
> `settings.yaml`에서 `visibility: 0`(비공개)으로 설정한 후 실행하세요.

```python
# test_publish.py
import asyncio
from agents.publishing_agent import PublishingAgent
from core.models import PostDraft, TopicData, SEOMetadata

async def main():
    draft = PostDraft(
        title="[테스트] 자동 게시 동작 확인",
        content_markdown=(
            "## 개요\n\n"
            "이 포스트는 자동화 에이전트 세팅 확인용 테스트 포스트입니다.\n\n"
            "## 결론\n\n"
            "자동화 배포 시스템이 정상 동작하는 것을 확인했습니다.\n"
        ),
        topic=TopicData(title="테스트", keywords=["테스트"], category="개발 일반"),
    )
    draft.seo = SEOMetadata(
        seo_title="[테스트] 자동 게시 동작 확인",
        tags=["테스트", "자동화"],
        tistory_category_id=1,
    )

    agent = PublishingAgent()
    draft = await agent.execute(draft)

    print(f"게시 완료!")
    print(f"  포스트 ID : {draft.tistory_post_id}")
    print(f"  URL       : {draft.published_url}")

asyncio.run(main())
```

```bash
python test_publish.py
```

**정상 출력 예시:**
```
게시 완료!
  포스트 ID : 42
  URL       : https://mytech.tistory.com/42
```

티스토리 블로그의 비공개 포스트 목록에서 생성된 포스트를 직접 확인합니다.

---

## 7. 전체 파이프라인 1회 테스트 실행

각 에이전트가 정상 동작하는 것을 확인한 후, 전체 파이프라인을 1회 실행합니다.

### 방법 1 — 자동 주제 탐색 후 실행

```bash
python main.py run
```

### 방법 2 — 주제를 직접 지정해 실행 (권장 — 첫 테스트)

```bash
python main.py run --topics "Python asyncio 완벽 가이드"
```

**실행 과정 콘솔 출력 예시:**
```
[2026-05-06 09:00:01] snap_begin  run_id=abc123
[2026-05-06 09:00:03] Fetching topics from all sources
[2026-05-06 09:00:05] Selected topic: Python asyncio 완벽 가이드
[2026-05-06 09:00:08] Generating content for: Python asyncio 완벽 가이드
[2026-05-06 09:01:12] Content generated: 2841 chars, 4 code blocks
[2026-05-06 09:01:30] Thumbnail saved: storage/images/abc123_thumbnail.png
[2026-05-06 09:01:32] Content image saved: storage/images/abc123_content.png
[2026-05-06 09:01:35] SEO metadata: title='...' tags=[...] readability=78.4
[2026-05-06 09:01:36] Quality check PASSED (score=100.0)
[2026-05-06 09:01:40] Image uploaded: thumbnail → https://...
[2026-05-06 09:01:45] Published: https://mytech.tistory.com/43 (postId=43)

============================================================
  Snap complete! 🟣
============================================================
  Run ID       : abc123
  Published    : 1
  Failed       : 0
  Human Review : 0
  Status       : completed
============================================================

  ✅ Python asyncio 완벽 가이드 실전 정리
     https://mytech.tistory.com/43
```

---

## 8. 자동 스케줄 실행 — Celery Worker & Beat 기동

전체 파이프라인 테스트가 완료되면 Celery를 통한 자동 스케줄 실행을 활성화합니다.

### 터미널 1 — Celery Worker 실행

```bash
# 가상환경이 활성화된 상태에서 실행
celery -A orchestrator.thanos worker --loglevel=info --concurrency=2
```

**정상 실행 메시지:**
```
[tasks]
  . orchestrator.thanos.task_daily_pipeline
  . orchestrator.thanos.task_weekly_analytics

[2026-05-06 09:00:00,000: INFO/MainProcess] celery@hostname ready.
```

### 터미널 2 — Celery Beat 스케줄러 실행

```bash
celery -A orchestrator.thanos beat --loglevel=info
```

**정상 실행 메시지:**
```
[2026-05-06 09:00:00,000: INFO/MainProcess] beat: Starting...
[2026-05-06 09:00:00,000: INFO/MainProcess] Scheduler: Sending due task daily-topic-discovery
```

### 스케줄 확인

Celery Beat가 실행 중일 때 등록된 스케줄 목록을 확인합니다.

```bash
celery -A orchestrator.thanos inspect scheduled
```

| 태스크 | 실행 시간 |
|-------|---------|
| `task_daily_pipeline` | 매일 오전 06:00 (KST) |
| `task_weekly_analytics` | 매주 월요일 오전 10:00 (KST) |

### Docker로 Worker + Beat 동시 실행 (프로덕션 권장)

```bash
# 전체 서비스 스택 실행
docker compose up -d

# 실행 상태 확인
docker compose ps

# Worker 로그 실시간 확인
docker compose logs -f techblog-worker
```

---

## 9. 운영 중 관리 방법

### 9.1 Human Review Queue 처리

품질 검수를 3회 이상 실패한 포스트는 사람이 직접 검토해야 합니다.  
데이터베이스의 `human_review_queue` 테이블에 저장됩니다.

**대기 중인 포스트 목록 확인:**

```python
# review_queue.py
import asyncio
from sqlalchemy import select
from core.database import AsyncSessionFactory, HumanReviewRecord

async def list_queue():
    async with AsyncSessionFactory() as session:
        result = await session.execute(
            select(HumanReviewRecord).where(HumanReviewRecord.resolved == False)
        )
        records = result.scalars().all()

    if not records:
        print("검토 대기 포스트 없음")
        return

    for r in records:
        print(f"─────────────────────────────────")
        print(f"포스트 ID : {r.post_id}")
        print(f"주제      : {r.topic_title}")
        print(f"실패 사유 : {r.issues}")
        print(f"대기 시각 : {r.queued_at}")

asyncio.run(list_queue())
```

```bash
python review_queue.py
```

**검토 완료 처리:**

1. `draft_json` 컬럼에 저장된 포스트 초안을 수동으로 편집합니다.
2. 편집 후 `resolved = True`로 업데이트합니다.
3. 수동으로 게시 에이전트를 실행하거나 티스토리 에디터에서 직접 게시합니다.

---

### 9.2 로그 모니터링

**실시간 로그 확인 (Docker 환경):**
```bash
# Worker 로그
docker compose logs -f techblog-worker

# 특정 에이전트 로그만 필터링
docker compose logs -f techblog-worker | grep "agent.publishing"
```

**로컬 실행 환경 로그:**
```bash
# 로그 파일 저장 (선택)
python main.py run 2>&1 | tee logs/run_$(date +%Y%m%d).log
```

**로그 레벨 변경 (디버깅 시):**  
`.env` 파일에서 변경합니다.

```dotenv
# DEBUG, INFO, WARNING, ERROR 중 선택
# 기본값: INFO
```

`settings.yaml`에서도 변경 가능합니다.
```yaml
monitoring:
  log_level: DEBUG   # INFO → DEBUG 로 변경
```

---

### 9.3 주간 분석 리포트 확인

매주 월요일 오전 10시에 자동으로 수집되지만, 수동으로도 실행할 수 있습니다.

```bash
python main.py analytics
```

**출력 예시:**
```
==================================================
📊 주간 기술블로그 성과 리포트 (2026-05-06)
==================================================
총 포스트 수     : 12
총 조회수        : 4,821
총 좋아요        : 67
총 댓글          : 23
평균 조회수      : 401
최고 성과 포스트 : 43 (1,204 views)
==================================================
```

Slack 알림을 받으려면 `.env` 파일에 Slack Webhook URL을 설정합니다.

```dotenv
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T.../B.../xxx
```

---

## 10. 에이전트 설정 튜닝 가이드

운영 경험에 따라 `config/settings.yaml`을 조정해 성능과 비용을 최적화할 수 있습니다.

### 콘텐츠 품질 조정

```yaml
blog:
  target_word_count: 3000    # 더 긴 포스트 원하면 상향 (비용 증가)
  min_word_count: 2000       # 품질 기준 상향

agents:
  content_generation:
    audience_level: "시니어 개발자"  # 더 심층적인 내용 요청

  quality_review:
    # quality_review_agent.py 에서 직접 수정
    # MIN_WORD_COUNT = 2000
    # MIN_SEO_SCORE = 75.0
```

### API 비용 절감

```yaml
llm:
  default: anthropic      # Claude가 GPT-4o보다 저렴한 경우 활용
  openai:
    model: gpt-4o-mini    # 비용 절감 모델로 변경 (품질 소폭 저하)
    max_tokens: 2048      # 토큰 수 제한

blog:
  posts_per_day: 1        # 하루 1포스트로 줄이기
```

### 스케줄 조정

`config/settings.yaml`의 `schedule` 섹션과 `orchestrator/thanos.py`의 `beat_schedule`을 함께 수정합니다.

```yaml
blog:
  schedule:
    topic_discovery: "0 8 * * *"    # 오전 8시로 변경
    publishing: "0 10 * * *"        # 오전 10시 게시
```

`orchestrator/thanos.py` 에서도 같은 시간으로 수정합니다.
```python
"daily-topic-discovery": {
    "task": "orchestrator.thanos.task_daily_pipeline",
    "schedule": crontab(hour=8, minute=0),   # 오전 8시
},
```

---

## 11. 자주 발생하는 오류 및 해결 방법

### ❌ `AuthenticationError: Invalid API Key`

**원인:** OpenAI 또는 Anthropic API 키가 잘못 설정됨  
**해결:**  
1. `.env` 파일에서 `OPENAI_API_KEY` 값을 확인합니다.
2. 공백, 줄바꿈 문자가 포함되지 않았는지 확인합니다.
3. 키가 만료되었다면 OpenAI 대시보드에서 새 키를 발급합니다.

---

### ❌ `Tistory API error: {'tistory': {'status': '400', ...}}`

**원인:** 티스토리 Access Token 만료 또는 블로그 이름 오류  
**해결:**  
1. [2.1절](#21-티스토리-open-api-앱-등록-및-access-token-발급) 절차를 다시 따라 Access Token을 재발급합니다.
2. `.env`의 `TISTORY_BLOG_NAME`이 실제 티스토리 블로그 주소와 일치하는지 확인합니다.
3. 테스트용 curl 명령으로 API 연결 직접 확인:
   ```bash
   curl "https://www.tistory.com/apis/blog/info?access_token=YOUR_TOKEN&output=json"
   ```

---

### ❌ `Connection refused` (PostgreSQL / Redis)

**원인:** Docker 컨테이너가 실행 중이지 않음  
**해결:**  
```bash
docker compose ps                     # 상태 확인
docker compose up -d postgres redis   # 재시작
docker compose logs postgres          # 상세 오류 확인
```

---

### ❌ `QualityCheckError: 글자 수 부족`

**원인:** LLM이 목표 분량보다 짧은 콘텐츠 생성  
**해결:**  
1. `settings.yaml`에서 `target_word_count`를 낮춥니다 (예: 1500).
2. 또는 `content_generation_agent.py`의 `USER_PROMPT_TEMPLATE`에서 분량 요구사항을 명시적으로 강화합니다:
   ```python
   "반드시 {target_word_count}자 이상 작성하세요."
   ```
3. 품질 기준 완화가 필요한 경우 `quality_review_agent.py`의 `MIN_WORD_COUNT`를 낮춥니다.

---

### ❌ `Image generation failed: RateLimitError`

**원인:** OpenAI 이미지 생성 API 요청 한도 초과  
**해결:**  
1. `settings.yaml`의 `image_generation.max_retries`를 유지하고, 재시도 간격을 늘립니다.
2. `image_generation_agent.py`의 `ImageGenerationAgent._generate_image` 메서드에 대기 시간을 추가합니다:
   ```python
   await asyncio.sleep(5)   # 재시도 전 5초 대기
   ```
3. `posts_per_day`를 1로 낮춰 동시 API 호출 수를 줄입니다.

---

### ❌ Celery Worker가 태스크를 받지 못함

**원인:** Redis 연결 오류 또는 Beat가 실행되지 않음  
**해결:**  
```bash
# Redis 연결 확인
celery -A orchestrator.thanos inspect ping

# 등록된 태스크 목록 확인
celery -A orchestrator.thanos inspect registered

# Worker 재시작
celery -A orchestrator.thanos worker --loglevel=debug --concurrency=1
```

---

## 12. 보안 체크리스트

운영 환경 배포 전 아래 항목을 모두 확인합니다.

- [ ] `.env` 파일이 `.gitignore`에 등록되어 있음
- [ ] API 키가 소스 코드 내에 하드코딩되지 않음
- [ ] Docker 컨테이너 포트가 로컬호스트에만 바인딩됨 (`127.0.0.1:5432:5432`)
- [ ] PostgreSQL 기본 비밀번호(`password`)를 강력한 비밀번호로 변경함
- [ ] OpenAI 대시보드에서 월 사용 한도(Spend Limit)를 설정함
- [ ] 코드 샌드박스(Docker) 실행 권한이 최소 권한으로 설정됨
- [ ] 티스토리 블로그의 비공개 글 확인 후 공개 전환 프로세스를 수립함
- [ ] Slack 알림 Webhook URL이 외부에 노출되지 않음

---

## 부록 — 유용한 관리 명령 모음

```bash
# ─── 파이프라인 수동 실행 ──────────────────────────────────
python main.py run
python main.py run --topics "원하는 주제"

# ─── 분석 수동 실행 ───────────────────────────────────────
python main.py analytics

# ─── Celery 관련 ──────────────────────────────────────────
celery -A orchestrator.thanos worker --loglevel=info
celery -A orchestrator.thanos beat --loglevel=info
celery -A orchestrator.thanos inspect active
celery -A orchestrator.thanos inspect stats

# ─── Docker 관련 ──────────────────────────────────────────
docker compose up -d                    # 전체 서비스 시작
docker compose down                     # 전체 서비스 중지
docker compose logs -f techblog-worker  # Worker 로그 실시간 확인
docker compose restart techblog-worker  # Worker 재시작

# ─── DB 직접 조회 ─────────────────────────────────────────
docker exec -it techblog-postgres-1 \
  psql -U techblog -d techblog \
  -c "SELECT post_id, title, pipeline_status, published_url FROM posts ORDER BY created_at DESC LIMIT 10;"
```

---

*문의 사항이나 오류 발생 시 `Human Review Queue`를 통해 수동으로 처리하거나, 에이전트 설정을 조정하세요.*
