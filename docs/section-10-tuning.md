# 섹션 10 — 에이전트 설정 튜닝 가이드

**이전 단계:** [섹션 09 — 운영 중 관리 방법](./section-09-operations.md)  
**다음 단계:** [섹션 11 — 오류 해결 방법](./section-11-troubleshooting.md)

---

## 개요

시스템이 안정적으로 운영된 후, 콘텐츠 품질과 API 비용 효율을 최적화하기 위한 튜닝 방법을 설명합니다.  
모든 설정은 `config/settings.yaml` 파일에서 변경합니다.

---

## 10-1. 콘텐츠 품질 튜닝

### 포스트 길이 조정

```yaml
# config/settings.yaml
blog:
  min_word_count: 1500       # 품질 검수 통과 최소 기준
  target_word_count: 2500    # LLM에 요청하는 목표 분량
```

| 목표 | 설정 예시 | 효과 |
|-----|---------|------|
| 짧고 빠른 포스트 | `min: 800, target: 1200` | 비용 절감, 생성 속도 향상 |
| 표준 포스트 | `min: 1500, target: 2500` | 기본 설정 |
| 심층 가이드 | `min: 2500, target: 4000` | 고품질, 높은 API 비용 |

> **주의:** `target_word_count`를 높이면 LLM 토큰 사용량이 증가해 비용이 높아집니다.

### 독자 수준 조정

```yaml
agents:
  content_generation:
    audience_level: "중급 개발자"    # 변경 가능한 값:
                                    # "입문자"
                                    # "중급 개발자" (기본값)
                                    # "시니어 개발자"
```

| 수준 | 특징 |
|-----|------|
| 입문자 | 기본 개념 설명 중심, 비유·예시 많음, 전문 용어 최소화 |
| 중급 개발자 | 실용적 예제 중심, 배경 지식 가정 |
| 시니어 개발자 | 심층 구현 세부사항, 성능·아키텍처 중심, 코드 비중 높음 |

### SEO 기준 강화

`agents/seo_optimization_agent.py` 파일을 수정합니다.

```python
# agents/seo_optimization_agent.py 에서 수정
MIN_SEO_SCORE = 70.0       # 기본값: 70.0 → 75.0 으로 상향 가능
MIN_READABILITY = 65.0     # 기본값: 65.0
```

---

## 10-2. API 비용 최적화

### 현재 비용 구조

| 구성 요소 | 사용 API | 포스트 1개 기준 비용 |
|---------|---------|----------------|
| 콘텐츠 생성 | GPT-4o (input+output) | $0.03~0.08 |
| SEO 최적화 | GPT-4o | $0.01~0.02 |
| 코드 수정 (오류 시) | GPT-4o | $0.01~0.03 |
| 이미지 생성 | DALL-E 3 (2장) | $0.08 |
| **합계** | | **약 $0.13~0.21** |

### 비용 절감 전략 1 — GPT-4o-mini 사용

```yaml
llm:
  openai:
    model: gpt-4o-mini    # gpt-4o 대비 약 15배 저렴 (품질 소폭 저하)
    max_tokens: 3000
```

예상 비용: 포스트 1개당 약 **$0.01~0.02** (이미지 제외)

### 비용 절감 전략 2 — 이미지 생성 선택적 비활성화

`agents/image_generation_agent.py`에서 이미지 생성 조건을 추가합니다.

```python
# agents/image_generation_agent.py
from core.config import settings

async def execute(self, draft: PostDraft) -> PostDraft:
    if not settings.enable_image_generation:   # 새 설정 추가
        self.logger.info("이미지 생성 비활성화")
        return draft
    # 기존 이미지 생성 로직 ...
```

`.env` 파일에 추가:
```dotenv
ENABLE_IMAGE_GENERATION=false   # 이미지 생성 비활성화
```

### 비용 절감 전략 3 — 일일 게시 수 축소

```yaml
blog:
  posts_per_day: 1    # 2 → 1 로 줄이기
```

### 월별 예상 비용 계산 예시

```
포스트 1개 비용: $0.15 (표준 설정)
하루 2개 × 30일 = 60개/월
월 총 비용: 60 × $0.15 = $9.00

포스트 1개 비용: $0.03 (gpt-4o-mini + 이미지 없음)
하루 1개 × 30일 = 30개/월
월 총 비용: 30 × $0.03 = $0.90
```

---

## 10-3. 주제 탐색 범위 조정

### 탐색 소스 우선순위 조정

`agents/topic_discovery_agent.py`의 소스 가중치를 변경합니다.

```python
# agents/topic_discovery_agent.py 에서 수정
SOURCE_WEIGHTS = {
    "github_trending": 1.5,    # GitHub Trending 우선
    "hacker_news": 1.0,
    "dev_to": 0.8,
}
```

### 특정 카테고리만 허용

```yaml
# config/settings.yaml
agents:
  topic_discovery:
    allowed_categories:
      - "백엔드"
      - "AI/ML"
      - "데브옵스"
    # 위 카테고리 외의 주제는 자동 제외
```

### 특정 키워드 제외

```yaml
agents:
  topic_discovery:
    exclude_keywords:
      - "NFT"
      - "블록체인"
      - "암호화폐"
```

---

## 10-4. 품질 검수 기준 조정

`agents/quality_review_agent.py`에서 직접 수정합니다.

```python
# agents/quality_review_agent.py 에서 수정
class QualityReviewAgent(BaseAgent):
    MIN_WORD_COUNT = 1500          # 최소 단어 수
    MIN_SEO_SCORE = 70.0           # 최소 SEO 점수 (0~100)
    MAX_PLAGIARISM_RATIO = 0.2     # 최대 중복률 (0~1)
    MIN_IMAGES = 1                 # 최소 이미지 수
    MIN_H2_SECTIONS = 2            # 최소 H2 소제목 수
    REQUIRE_CODE_BLOCKS = True     # 코드 블록 필수 여부
```

**기준 완화 예시 (시작 단계 권장):**
```python
MIN_WORD_COUNT = 1000
MIN_SEO_SCORE = 60.0
MIN_IMAGES = 0             # 이미지 없어도 통과
REQUIRE_CODE_BLOCKS = False
```

---

## 10-5. 스케줄 튜닝

### 게시 시간대 최적화

기술 블로그 독자 방문 패턴 분석에 기반한 권장 게시 시간:

| 시간대 | 특징 |
|-------|------|
| **오전 07:00~09:00** | 출근 전 모바일 독자 (트래픽 많음) |
| **점심 12:00~13:00** | 점심 시간 독자 |
| **저녁 20:00~22:00** | 퇴근 후 집중 독자 (체류 시간 길음) |

```python
# orchestrator/thanos.py 에서 수정
beat_schedule = {
    "daily-topic-discovery": {
        "task": "orchestrator.thanos.task_daily_pipeline",
        "schedule": crontab(hour=7, minute=0),   # 오전 7시로 변경
    },
}
```

### 하루 2회 게시 설정

```python
beat_schedule = {
    "morning-pipeline": {
        "task": "orchestrator.thanos.task_daily_pipeline",
        "schedule": crontab(hour=7, minute=0),
    },
    "evening-pipeline": {
        "task": "orchestrator.thanos.task_daily_pipeline",
        "schedule": crontab(hour=20, minute=0),
    },
}
```

---

## 10-6. LLM 프롬프트 튜닝

### 콘텐츠 생성 프롬프트 수정

`agents/content_generation_agent.py`의 시스템 프롬프트를 조정해 포스트 스타일을 변경할 수 있습니다.

```python
# agents/content_generation_agent.py 에서 수정
SYSTEM_PROMPT = """
당신은 한국의 시니어 소프트웨어 엔지니어가 운영하는 기술 블로그의 콘텐츠 작성자입니다.

작성 스타일:
- 실용적이고 바로 사용할 수 있는 예제 중심
- 이론보다 실전 코드 비중 높게
- 각 섹션은 핵심 포인트로 시작
- 마치며 섹션에 핵심 요약 포함

구조 요구사항:
- ## 소제목 4~6개 필수
- 코드 블록 최소 3개
- 총 {target_word_count}자 이상 작성

금지 사항:
- 과장된 표현 (혁신적인, 획기적인 등)
- 영어 원문 번역투 문장
"""
```

### SEO 프롬프트 수정

```python
# agents/seo_optimization_agent.py 에서 수정
SEO_SYSTEM_PROMPT = """
당신은 한국 기술 블로그 SEO 전문가입니다.
검색 의도: 실용적인 기술 가이드를 찾는 개발자
타겟 키워드 밀도: 2~3%
제목 형식: [핵심 기술] + [혜택/방법] 패턴 권장
  예: "Python asyncio 완벽 정리: 비동기 처리 실전 가이드"
"""
```

---

## 10-7. 설정 변경 후 반영 절차

설정 파일 변경 후 아래 절차로 반영합니다.

```powershell
# 1. settings.yaml 수정 저장

# 2. 설정 로드 확인
python -c "
from core.config import load_yaml_settings
cfg = load_yaml_settings()
print('posts_per_day:', cfg['blog']['posts_per_day'])
print('target_word_count:', cfg['blog']['target_word_count'])
"

# 3. Worker 재시작 (설정 변경 반영)
# Docker 환경
docker compose restart techblog-worker techblog-scheduler

# 로컬 환경: Worker 터미널에서 Ctrl+C 후 재실행
```

---

## 완료 기준

- [ ] 블로그 목표에 맞는 `target_word_count` 설정 완료
- [ ] `audience_level` 독자 수준 확인 및 조정
- [ ] `model` 설정 확인 (품질/비용 균형)
- [ ] 게시 시간대 최적화 (`beat_schedule`)
- [ ] (선택) 품질 검수 기준 조정

모든 항목 완료 후 → **[섹션 11](./section-11-troubleshooting.md)** 참조
