# 섹션 03 — 프로젝트 환경 세팅

**이전 단계:** [섹션 02 — 외부 서비스 계정 생성](./section-02-external-services.md)  
**다음 단계:** [섹션 04 — Docker 인프라 실행](./section-04-docker-infrastructure.md)

---

## 개요

Python 가상환경을 생성하고, 모든 의존 패키지를 설치한 뒤, 에이전트가 참조하는 환경 변수 파일(`.env`)과 설정 파일(`settings.yaml`)을 완성합니다.

---

## 3-1. 프로젝트 루트 디렉터리 확인

모든 명령은 프로젝트 루트(`techblog/`) 폴더에서 실행해야 합니다.

```powershell
# 현재 위치 확인
Get-Location

# techblog 폴더로 이동 (경로는 실제 위치에 맞게 수정)
Set-Location C:\Users\user\Downloads\techblog

# 폴더 구조 확인
Get-ChildItem -Name
```

**예상 출력 (주요 항목):**
```
agents/
config/
core/
docs/
orchestrator/
utils/
.env.example
docker-compose.yml
main.py
requirements.txt
```

---

## 3-2. Python 가상환경 생성

가상환경을 사용하면 시스템 Python과 프로젝트 패키지가 충돌하지 않습니다.

```powershell
# 가상환경 생성 (.venv 폴더 생성)
python -m venv .venv
```

**생성 확인:**
```powershell
Test-Path .venv
# 출력: True
```

---

## 3-3. 가상환경 활성화

```powershell
# Windows PowerShell
.venv\Scripts\Activate.ps1
```

```bash
# macOS / Linux
source .venv/bin/activate
```

**활성화 확인:** 터미널 프롬프트 앞에 `(.venv)` 표시가 나타나면 성공입니다.
```
(.venv) PS C:\Users\user\Downloads\techblog>
```

> **주의:** 새 터미널을 열 때마다 가상환경을 다시 활성화해야 합니다.  
> 이후 모든 명령은 가상환경이 활성화된 상태에서 실행합니다.

---

## 3-4. pip 업그레이드 및 패키지 설치

```powershell
# pip 최신화
python -m pip install --upgrade pip

# 전체 패키지 설치
pip install -r requirements.txt
```

패키지 수가 많아 3~10분 소요됩니다. 설치 중 아래와 같은 메시지가 정상 출력됩니다.

```
Collecting openai>=1.30.0
  Downloading openai-1.35.3-py3-none-any.whl (325 kB)
...
Successfully installed openai-1.35.3 anthropic-0.30.1 ...
```

### 설치 결과 확인

```powershell
# 핵심 패키지 설치 확인
python -c "
import openai, anthropic, celery, sqlalchemy, pydantic
import markdown2, structlog, PIL
print('모든 핵심 패키지 정상 설치 확인 완료')
"
```

### 설치된 전체 패키지 목록 확인

```powershell
pip list
```

아래 패키지들이 목록에 있어야 합니다.

| 패키지 | 최소 버전 |
|-------|---------|
| openai | 1.30.0 |
| anthropic | 0.25.0 |
| celery | 5.4.0 |
| sqlalchemy | 2.0.30 |
| pydantic | 2.7.0 |
| pydantic-settings | 2.2.0 |
| redis | 5.0.0 |
| httpx | 0.27.0 |
| markdown2 | 2.4.13 |
| structlog | 24.1.0 |
| pillow | 10.3.0 |
| beautifulsoup4 | 4.12.0 |
| feedparser | 6.0.11 |

---

## 3-5. 환경 변수 파일 (.env) 작성

### .env 파일 생성

`.env.example` 파일을 복사해 `.env` 파일을 만듭니다.

```powershell
# Windows
Copy-Item .env.example .env
```

```bash
# macOS / Linux
cp .env.example .env
```

### .env 파일 내용 편집

메모장 또는 VS Code로 `.env` 파일을 엽니다.

```powershell
# VS Code로 열기
code .env

# 또는 메모장으로 열기
notepad .env
```

아래 내용을 참고해 각 값을 섹션 02에서 수집한 실제 값으로 채웁니다.

```dotenv
# ════════════════════════════════════════════════
#  LLM 설정
# ════════════════════════════════════════════════
# OpenAI — 필수
OPENAI_API_KEY=sk-proj-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

# Anthropic — 선택 (폴백 LLM)
ANTHROPIC_API_KEY=sk-ant-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

# ════════════════════════════════════════════════
#  티스토리 API 설정 — 모두 필수
# ════════════════════════════════════════════════
TISTORY_APP_ID=발급받은_App_ID
TISTORY_SECRET_KEY=발급받은_Secret_Key
TISTORY_ACCESS_TOKEN=발급받은_Access_Token
TISTORY_BLOG_NAME=내블로그이름

# ════════════════════════════════════════════════
#  데이터베이스 / Redis
#  (Docker Compose 기본값과 일치 — 변경 불필요)
# ════════════════════════════════════════════════
DATABASE_URL=postgresql+asyncpg://techblog:password@localhost:5432/techblog
REDIS_URL=redis://localhost:6379/0

# ════════════════════════════════════════════════
#  포스팅 설정
# ════════════════════════════════════════════════
POSTS_PER_DAY=2
MIN_WORD_COUNT=1500

# ════════════════════════════════════════════════
#  슬랙 알림 — 선택
# ════════════════════════════════════════════════
# SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T.../B.../xxx

# ════════════════════════════════════════════════
#  이미지 저장 경로 — 선택 (기본값 사용 가능)
# ════════════════════════════════════════════════
IMAGE_STORAGE_PATH=./storage/images
```

### .env 파일 작성 시 주의사항

1. **공백 금지:** `KEY = value` (X) → `KEY=value` (O)
2. **따옴표 불필요:** `KEY="value"` 는 따옴표가 값에 포함됩니다.
3. **주석 처리:** `#` 으로 시작하는 줄은 무시됩니다.
4. **줄바꿈 금지:** 하나의 값이 여러 줄에 걸치면 안 됩니다.

### .env 파일 로드 확인

```powershell
python -c "
from core.config import settings
print('OPENAI_API_KEY:', settings.openai_api_key[:8] + '...' if settings.openai_api_key else '미설정')
print('TISTORY_BLOG_NAME:', settings.tistory_blog_name)
print('DATABASE_URL:', settings.database_url[:30] + '...')
"
```

**정상 출력 예시:**
```
OPENAI_API_KEY: sk-proj-...
TISTORY_BLOG_NAME: mytech
DATABASE_URL: postgresql+asyncpg://techblog:p...
```

---

## 3-6. 설정 파일 (settings.yaml) 확인 및 수정

`config/settings.yaml` 파일은 API 키를 제외한 모든 운영 설정을 담습니다.  
자주 조정하게 될 항목 위주로 설명합니다.

```powershell
code config/settings.yaml
```

### 주요 설정 항목별 설명

#### 블로그 게시 설정

```yaml
blog:
  posts_per_day: 2              # 하루 자동 게시 포스트 수 (초기: 1 권장)
  min_word_count: 1500          # 품질 검수 최소 단어 수 (낮출수록 관대한 기준)
  target_word_count: 2500       # LLM에 요청하는 목표 분량

  tistory:
    visibility: 0               # 0=비공개 / 3=공개 (테스트 중에는 0 유지)
    default_category_id: 1      # 섹션 02에서 확인한 카테고리 ID 입력
```

> **테스트 기간 중에는 반드시 `visibility: 0`(비공개)으로 유지하세요.**  
> 품질 미달 포스트가 공개적으로 게시되는 상황을 방지합니다.

#### LLM 설정

```yaml
llm:
  default: openai               # 기본 LLM 선택 (openai / anthropic)
  providers:
    - openai                    # 1순위
    - anthropic                 # 2순위 (폴백)

  openai:
    model: gpt-4o               # gpt-4o-mini 로 변경하면 비용 절감 (품질 소폭 저하)
    max_tokens: 4096

  anthropic:
    model: claude-3-7-sonnet-20250219
    max_tokens: 4096
```

#### 에이전트별 재시도 설정

```yaml
agents:
  content_generation:
    max_retries: 3              # 콘텐츠 생성 실패 시 재시도 횟수
    audience_level: "중급 개발자"   # 입문자 / 중급 개발자 / 시니어

  quality_review:
    human_review_max_retries: 3  # 품질 실패 후 Human Review 큐로 이동까지의 재시도 수

  image_generation:
    thumbnail_size: [1200, 628]  # 섬네일 크기 (픽셀)
    content_size: [800, 450]     # 본문 이미지 크기
```

#### 스케줄 설정

```yaml
blog:
  schedule:
    topic_discovery: "0 6 * * *"    # 매일 오전 06:00 (KST) 실행
    weekly_analytics: "0 10 * * 1"  # 매주 월요일 오전 10:00 분석 리포트
```

Cron 표현식 형식: `분 시 일 월 요일`

---

## 3-7. 이미지 저장 폴더 생성

에이전트가 생성한 이미지를 저장할 폴더를 미리 만듭니다.

```powershell
New-Item -ItemType Directory -Force -Path storage\images
New-Item -ItemType Directory -Force -Path logs
```

```bash
# macOS / Linux
mkdir -p storage/images logs
```

---

## 3-8. .gitignore 확인

Git을 사용한다면 민감한 파일이 커밋되지 않도록 `.gitignore`를 확인합니다.

```powershell
Get-Content .gitignore
```

아래 항목들이 포함되어 있어야 합니다.

```gitignore
.env
.venv/
storage/
logs/
__pycache__/
*.pyc
*.pyo
.pytest_cache/
```

누락된 항목이 있으면 직접 추가합니다.

```powershell
Add-Content .gitignore "`n.env`n.venv/`nstorage/`nlogs/"
```

---

## 3-9. 환경 설정 최종 확인

아래 스크립트로 환경 설정이 올바른지 한 번에 검증합니다.

```python
# check_env.py
from core.config import settings
import os

checks = [
    ("OPENAI_API_KEY",       bool(settings.openai_api_key)),
    ("TISTORY_APP_ID",       bool(settings.tistory_app_id)),
    ("TISTORY_SECRET_KEY",   bool(settings.tistory_secret_key)),
    ("TISTORY_ACCESS_TOKEN", bool(settings.tistory_access_token)),
    ("TISTORY_BLOG_NAME",    bool(settings.tistory_blog_name)),
    ("DATABASE_URL",         bool(settings.database_url)),
    ("REDIS_URL",            bool(settings.redis_url)),
]

print("=" * 45)
print("  환경 변수 설정 확인")
print("=" * 45)
all_ok = True
for name, ok in checks:
    status = "✅" if ok else "❌ 미설정"
    print(f"  {status}  {name}")
    if not ok:
        all_ok = False

print("=" * 45)
if all_ok:
    print("  모든 필수 환경 변수가 설정되었습니다.")
else:
    print("  ❌ 미설정 항목을 .env 파일에서 확인하세요.")
```

```powershell
python check_env.py
```

---

## 완료 기준

- [ ] 가상환경 생성 및 활성화 (`.venv/`)
- [ ] `pip install -r requirements.txt` 완료 (오류 없음)
- [ ] `.env` 파일 작성 완료 (실제 값으로 채움)
- [ ] `python check_env.py` → 모든 항목 ✅
- [ ] `config/settings.yaml` 의 `visibility: 0` 확인
- [ ] `storage/images/` 폴더 생성 완료

모든 항목 완료 후 → **[섹션 04](./section-04-docker-infrastructure.md)** 로 이동
