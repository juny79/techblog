# 섹션 06 — 에이전트별 동작 확인 (단계적 검증)

**이전 단계:** [섹션 05 — 데이터베이스 초기화](./section-05-database-init.md)  
**다음 단계:** [섹션 07 — 전체 파이프라인 테스트](./section-07-pipeline-test.md)

---

## 개요

전체 파이프라인을 한 번에 실행하기 전에 각 에이전트를 독립적으로 검증합니다.  
에이전트별 단계 테스트를 통해 문제 발생 시 원인 파악이 쉬워집니다.

**검증 순서:**

```
Power Stone     → Mind Stone → Code Example + Image (병렬)
(주제 탐색)      (콘텐츠 생성)  (코드 검증)     (이미지 생성)
     ↓
Reality Stone   → Soul Stone  → Space Stone
(SEO 최적화)    (품질 검수)    (티스토리 게시)
```

---

## 6-1. Power Stone — 주제 탐색 에이전트

**역할:** GitHub Trending, Hacker News, dev.to에서 실시간 기술 주제를 수집하고 카테고리/점수를 부여합니다.  
**외부 의존:** 인터넷 연결 (API 키 불필요)

### 테스트 파일 작성

`tests/test_topic_agent.py` 파일을 생성합니다.

```python
# tests/test_topic_agent.py
import asyncio
from agents.topic_discovery_agent import TopicDiscoveryAgent

async def main():
    print("=" * 50)
    print("  Power Stone — 주제 탐색 에이전트 테스트")
    print("=" * 50)

    agent = TopicDiscoveryAgent()
    print("\n[1] 단일 주제 탐색...")
    topics = await agent.discover_batch(count=1)

    if not topics:
        print("❌ 주제 탐색 실패 — 인터넷 연결을 확인하세요.")
        return

    topic = topics[0]
    print(f"✅ 주제 탐색 성공")
    print(f"   제목     : {topic.title}")
    print(f"   카테고리 : {topic.category}")
    print(f"   키워드   : {topic.keywords}")
    print(f"   트렌드점수: {topic.trend_score:.1f}")
    print(f"   출처     : {topic.source}")

    print("\n[2] 복수 주제 탐색 (3개)...")
    topics = await agent.discover_batch(count=3)
    print(f"✅ 수집된 주제 수: {len(topics)}개")
    for i, t in enumerate(topics, 1):
        print(f"   {i}. [{t.trend_score:.0f}점] {t.title}")

asyncio.run(main())
```

### 실행

```powershell
python tests/test_topic_agent.py
```

### 예상 출력

```
==================================================
  Power Stone — 주제 탐색 에이전트 테스트
==================================================

[1] 단일 주제 탐색...
✅ 주제 탐색 성공
   제목     : Rust로 만드는 고성능 REST API
   카테고리 : 백엔드
   키워드   : ['Rust', 'Axum', 'REST', 'API', '성능']
   트렌드점수: 94.0
   출처     : github_trending

[2] 복수 주제 탐색 (3개)...
✅ 수집된 주제 수: 3개
   1. [94점] Rust로 만드는 고성능 REST API
   2. [88점] React 19 Server Components 완벽 가이드
   3. [81점] Kubernetes 운영 실전 패턴
```

---

## 6-2. Mind Stone — 콘텐츠 생성 에이전트

**역할:** LLM(GPT-4o)을 호출해 한국어 마크다운 블로그 포스트를 생성합니다.  
**외부 의존:** OpenAI API 키 (비용 발생: 포스트 1개당 약 $0.03~0.08)

### 테스트 파일 작성

```python
# tests/test_content_agent.py
import asyncio
from agents.content_generation_agent import ContentGenerationAgent
from core.models import PostDraft, TopicData

async def main():
    print("=" * 50)
    print("  Mind Stone — 콘텐츠 생성 에이전트 테스트")
    print("=" * 50)

    draft = PostDraft(
        topic=TopicData(
            title="Python asyncio 비동기 프로그래밍 완벽 정리",
            keywords=["Python", "asyncio", "비동기", "async", "await"],
            category="백엔드",
            trend_score=90.0,
        )
    )

    agent = ContentGenerationAgent()

    print("\nLLM 호출 중... (30초~2분 소요)")
    draft = await agent.execute(draft)

    print(f"\n✅ 콘텐츠 생성 성공")
    print(f"   제목       : {draft.title}")
    print(f"   본문 길이  : {len(draft.content_markdown)}자")
    print(f"   단어 수    : {len(draft.content_markdown.split())}단어")
    print(f"   코드 블록  : {len(draft.code_blocks)}개")
    print(f"\n--- 본문 앞 300자 ---")
    print(draft.content_markdown[:300])
    print("...")

    # 마크다운 구조 확인
    h2_count = draft.content_markdown.count("\n## ")
    print(f"\n   H2 소제목  : {h2_count}개")
    code_langs = [b.language for b in draft.code_blocks]
    print(f"   코드 언어  : {set(code_langs)}")

asyncio.run(main())
```

### 실행

```powershell
python tests/test_content_agent.py
```

### 예상 출력

```
==================================================
  Mind Stone — 콘텐츠 생성 에이전트 테스트
==================================================

LLM 호출 중... (30초~2분 소요)

✅ 콘텐츠 생성 성공
   제목       : Python asyncio 비동기 프로그래밍 완벽 정리: async/await부터 실전까지
   본문 길이  : 3241자
   단어 수    : 512단어
   코드 블록  : 4개

--- 본문 앞 300자 ---
## 들어가며

현대 웹 애플리케이션은 수많은 I/O 작업을 동시에 처리해야 합니다.
Python 3.4부터 도입된 `asyncio`는 이러한 비동기 처리를 ...
...

   H2 소제목  : 5개
   코드 언어  : {'python'}
```

---

## 6-3. Code Example 에이전트

**역할:** 마크다운 내 코드 블록을 실제 실행해 유효성을 검증하고, 오류 시 LLM으로 자동 수정합니다.  
**외부 의존:** 없음 (로컬 subprocess 실행)

### 테스트 파일 작성

```python
# tests/test_code_agent.py
import asyncio
from agents.code_example_agent import CodeExampleAgent
from core.models import PostDraft, CodeBlock

async def main():
    print("=" * 50)
    print("  Code Example 에이전트 테스트")
    print("=" * 50)

    # 유효한 코드 1개 + 오류가 있는 코드 1개
    draft = PostDraft(title="코드 검증 테스트")
    draft.code_blocks = [
        CodeBlock(
            index=0,
            language="python",
            code='print("Hello, TechBlog!")\nresult = 1 + 2\nprint(f"결과: {result}")'
        ),
        CodeBlock(
            index=1,
            language="python",
            code="# 의도적 문법 오류\ndef broken(\n    pass"
        ),
        CodeBlock(
            index=2,
            language="javascript",
            code='console.log("JavaScript 코드 실행 테스트");'
        ),
    ]

    agent = CodeExampleAgent()
    print("\n코드 블록 검증 중...")
    draft = await agent.execute(draft)

    for block in draft.code_blocks:
        if block.is_valid:
            print(f"✅ 블록 {block.index} ({block.language}): 유효")
        else:
            print(f"⚠️  블록 {block.index} ({block.language}): 검증 실패")
        if block.fixed_code:
            print(f"   → 자동 수정됨")

asyncio.run(main())
```

### 실행

```powershell
python tests/test_code_agent.py
```

### 예상 출력

```
==================================================
  Code Example 에이전트 테스트
==================================================

코드 블록 검증 중...
✅ 블록 0 (python): 유효
⚠️  블록 1 (python): 검증 실패
   → 자동 수정됨
✅ 블록 2 (javascript): 유효
```

---

## 6-4. Image Generation 에이전트

**역할:** DALL-E 3를 통해 섬네일(1200×628)과 본문 이미지(800×450)를 생성합니다.  
**외부 의존:** OpenAI API (비용 발생: 이미지 2장 약 $0.08)

> **비용 발생 주의:** 이 테스트는 실제 DALL-E 3 API를 호출합니다.

### 테스트 파일 작성

```python
# tests/test_image_agent.py
import asyncio
import os
from agents.image_generation_agent import ImageGenerationAgent
from core.models import PostDraft, TopicData

async def main():
    print("=" * 50)
    print("  Image Generation 에이전트 테스트")
    print("  ⚠ DALL-E 3 API 호출 (약 $0.08 발생)")
    print("=" * 50)

    draft = PostDraft(
        title="Python asyncio 비동기 프로그래밍 완벽 정리",
        topic=TopicData(
            title="Python asyncio 비동기 프로그래밍",
            keywords=["Python", "asyncio", "비동기"],
            category="백엔드",
        )
    )

    agent = ImageGenerationAgent()
    print("\n이미지 생성 중... (30초~1분 소요)")
    draft = await agent.execute(draft)

    print(f"\n✅ 이미지 생성 완료: {len(draft.images)}장")
    for img in draft.images:
        exists = os.path.exists(img.local_path)
        print(f"   [{img.image_type}]")
        print(f"   크기  : {img.width}x{img.height}")
        print(f"   경로  : {img.local_path}")
        print(f"   파일  : {'존재함 ✅' if exists else '없음 ❌'}")

asyncio.run(main())
```

### 실행

```powershell
python tests/test_image_agent.py
```

### 예상 출력

```
==================================================
  Image Generation 에이전트 테스트
  ⚠ DALL-E 3 API 호출 (약 $0.08 발생)
==================================================

이미지 생성 중... (30초~1분 소요)

✅ 이미지 생성 완료: 2장
   [thumbnail]
   크기  : 1200x628
   경로  : ./storage/images/xxxxxxxx_thumbnail.png
   파일  : 존재함 ✅
   [content]
   크기  : 800x450
   경로  : ./storage/images/xxxxxxxx_content.png
   파일  : 존재함 ✅
```

생성된 이미지 파일을 직접 열어 내용을 확인합니다.

```powershell
# 이미지 파일 목록 확인
Get-ChildItem storage\images\
```

---

## 6-5. SEO Optimization 에이전트 (Reality Stone)

**역할:** LLM을 통해 SEO 메타데이터(제목, 설명, 태그)를 생성하고, 가독성 점수를 계산합니다.  
**외부 의존:** OpenAI API

### 테스트 파일 작성

```python
# tests/test_seo_agent.py
import asyncio
from agents.seo_optimization_agent import SEOOptimizationAgent
from core.models import PostDraft, TopicData

SAMPLE_CONTENT = """
## 들어가며

Python의 asyncio는 비동기 I/O를 처리하기 위한 표준 라이브러리입니다.

## asyncio 기본 개념

`async def`로 선언된 함수는 코루틴(coroutine)이 됩니다.
`await` 키워드는 비동기 작업이 완료될 때까지 일시 중단합니다.

## 실전 예제

```python
import asyncio

async def fetch_data(url: str) -> str:
    await asyncio.sleep(1)  # 네트워크 요청 시뮬레이션
    return f"Data from {url}"

async def main():
    results = await asyncio.gather(
        fetch_data("https://api1.example.com"),
        fetch_data("https://api2.example.com"),
    )
    print(results)

asyncio.run(main())
\```

## 결론

asyncio를 활용하면 I/O 바운드 작업에서 큰 성능 향상을 얻을 수 있습니다.
"""

async def main():
    print("=" * 50)
    print("  Reality Stone — SEO 최적화 에이전트 테스트")
    print("=" * 50)

    draft = PostDraft(
        title="Python asyncio 비동기 프로그래밍 완벽 정리",
        content_markdown=SAMPLE_CONTENT,
        topic=TopicData(
            title="Python asyncio",
            keywords=["Python", "asyncio"],
            category="백엔드",
        )
    )

    agent = SEOOptimizationAgent()
    print("\nSEO 분석 중...")
    draft = await agent.execute(draft)

    seo = draft.seo
    print(f"\n✅ SEO 메타데이터 생성 완료")
    print(f"   SEO 제목    : {seo.seo_title}")
    print(f"   메타 설명   : {seo.meta_description}")
    print(f"   태그        : {seo.tags}")
    print(f"   카테고리 ID : {seo.tistory_category_id}")
    print(f"   가독성 점수 : {seo.readability_score:.1f} / 100")
    print(f"   SEO 점수    : {seo.seo_score:.1f} / 100")

asyncio.run(main())
```

### 실행

```powershell
python tests/test_seo_agent.py
```

---

## 6-6. Quality Review 에이전트 (Soul Stone)

**역할:** 6가지 품질 기준을 검사하고 미달 시 `QualityCheckError`를 발생시킵니다.  
**외부 의존:** 없음

### 테스트 파일 작성

```python
# tests/test_quality_agent.py
import asyncio
from agents.quality_review_agent import QualityReviewAgent, QualityCheckError
from core.models import PostDraft, TopicData, SEOMetadata, ImageAsset, CodeBlock

# 품질 기준을 통과하는 샘플 포스트 구성
LONG_CONTENT = """
## 들어가며

""" + ("Python asyncio는 비동기 I/O 처리를 위한 표준 라이브러리입니다. " * 80) + """

## 핵심 개념

""" + ("async/await 패턴을 사용하면 동시 처리 성능을 높일 수 있습니다. " * 80) + """

## 마치며

지금까지 asyncio의 핵심 개념을 살펴보았습니다.
"""

async def main():
    print("=" * 50)
    print("  Soul Stone — 품질 검수 에이전트 테스트")
    print("=" * 50)

    # --- 케이스 1: 통과 예상 ---
    print("\n[케이스 1] 품질 기준 통과 케이스")
    draft = PostDraft(
        title="Python asyncio 비동기 프로그래밍 완벽 정리",
        content_markdown=LONG_CONTENT,
        topic=TopicData(title="asyncio", keywords=["Python"], category="백엔드"),
    )
    draft.seo = SEOMetadata(readability_score=80.0, seo_score=85.0)
    draft.images = [
        ImageAsset(image_type="thumbnail", local_path="./storage/images/test.png",
                   width=1200, height=628)
    ]
    draft.code_blocks = [
        CodeBlock(index=0, language="python", code="print('ok')", is_valid=True)
    ]

    agent = QualityReviewAgent()
    try:
        draft = await agent.execute(draft)
        report = draft.quality_report
        print(f"✅ 품질 검수 통과! (점수: {report.overall_score:.1f})")
    except QualityCheckError as e:
        print(f"❌ 품질 검수 실패 (예상치 못한 실패)")
        for issue in e.issues:
            print(f"   - {issue}")

    # --- 케이스 2: 실패 예상 ---
    print("\n[케이스 2] 품질 기준 미달 케이스 (단어 수 부족, 이미지 없음)")
    short_draft = PostDraft(
        title="짧은 포스트",
        content_markdown="## 소제목\n짧은 내용",
        topic=TopicData(title="테스트", keywords=[], category="개발 일반"),
    )
    short_draft.seo = SEOMetadata(readability_score=50.0, seo_score=40.0)

    try:
        short_draft = await agent.execute(short_draft)
        print("❌ 통과 (예상과 다름)")
    except QualityCheckError as e:
        print(f"✅ 예상대로 실패 감지 ({len(e.issues)}개 이슈)")
        for issue in e.issues:
            print(f"   - {issue}")

asyncio.run(main())
```

### 실행

```powershell
python tests/test_quality_agent.py
```

---

## 6-7. Publishing 에이전트 (Space Stone)

**역할:** 마크다운 포스트를 HTML로 변환해 티스토리 API로 게시합니다.  
**외부 의존:** 티스토리 Access Token

> **주의:** 이 테스트는 티스토리에 실제 포스트를 생성합니다.  
> `config/settings.yaml`의 `visibility: 0` (비공개) 상태에서 실행하세요.

### 테스트 파일 작성

```python
# tests/test_publish_agent.py
import asyncio
from agents.publishing_agent import PublishingAgent
from core.models import PostDraft, TopicData, SEOMetadata

CONTENT = """
## 개요

이 포스트는 자동화 에이전트 세팅 검증용 테스트 포스트입니다.

## 자동화 파이프라인 구성 에이전트

- Power Stone: 주제 탐색
- Mind Stone: 콘텐츠 생성
- Reality Stone: SEO 최적화
- Soul Stone: 품질 검수
- Space Stone: 게시

## 결론

에이전트 세팅이 정상 동작하는 것을 확인했습니다.
"""

async def main():
    print("=" * 50)
    print("  Space Stone — 게시 에이전트 테스트")
    print("  ⚠ 티스토리에 실제 포스트가 생성됩니다 (비공개)")
    print("=" * 50)

    draft = PostDraft(
        title="[에이전트 세팅 확인] 자동 게시 테스트",
        content_markdown=CONTENT,
        topic=TopicData(
            title="자동화 에이전트 세팅 테스트",
            keywords=["테스트", "자동화", "에이전트"],
            category="개발 일반",
        ),
    )
    draft.seo = SEOMetadata(
        seo_title="[에이전트 세팅 확인] 자동 게시 테스트",
        tags=["테스트", "자동화"],
        tistory_category_id=1,
    )

    agent = PublishingAgent()
    print("\n티스토리 게시 중...")
    draft = await agent.execute(draft)

    print(f"\n✅ 게시 완료!")
    print(f"   포스트 ID : {draft.tistory_post_id}")
    print(f"   URL       : {draft.published_url}")
    print(f"\n티스토리 블로그 비공개 목록에서 생성된 포스트를 확인하세요.")

asyncio.run(main())
```

### 실행

```powershell
python tests/test_publish_agent.py
```

### 게시 결과 확인

1. 티스토리 블로그 관리 페이지에 접속합니다.  
   `https://www.tistory.com/manage/posts`
2. 비공개 포스트 목록에서 `[에이전트 세팅 확인] 자동 게시 테스트` 포스트를 확인합니다.
3. 포스트 내용이 올바르게 표시되는지 검토합니다.
4. 테스트 포스트는 확인 후 삭제합니다.

---

## 6-8. 모든 에이전트 일괄 검증

위 6개 테스트를 한 번에 실행하는 통합 테스트입니다.

```python
# tests/run_all_tests.py
import asyncio
import subprocess
import sys

tests = [
    ("Power Stone  (주제 탐색)",   "tests/test_topic_agent.py"),
    ("Mind Stone   (콘텐츠 생성)", "tests/test_content_agent.py"),
    ("Code Example (코드 검증)",   "tests/test_code_agent.py"),
    ("Quality Gate (품질 검수)",   "tests/test_quality_agent.py"),
    ("SEO Agent    (SEO 최적화)",  "tests/test_seo_agent.py"),
    # 이미지/게시 테스트는 비용/부작용이 있으므로 기본 제외
    # ("Image Gen    (이미지 생성)", "tests/test_image_agent.py"),
    # ("Publishing   (티스토리 게시)","tests/test_publish_agent.py"),
]

print("=" * 60)
print("  전체 에이전트 검증 시작")
print("=" * 60)
results = []
for name, path in tests:
    print(f"\n{'─' * 40}")
    print(f"  {name}")
    print(f"{'─' * 40}")
    result = subprocess.run([sys.executable, path], capture_output=False)
    results.append((name, result.returncode == 0))

print("\n" + "=" * 60)
print("  검증 결과 요약")
print("=" * 60)
for name, ok in results:
    print(f"  {'✅' if ok else '❌'}  {name}")
```

```powershell
# tests 폴더 생성
New-Item -ItemType Directory -Force -Path tests

python tests/run_all_tests.py
```

---

## 완료 기준

- [ ] Power Stone: 주제 3개 이상 정상 수집
- [ ] Mind Stone: 1500자 이상 마크다운 포스트 생성
- [ ] Code Example: 유효 코드 검증 통과, 오류 코드 자동 수정
- [ ] Image Generation: 섬네일/본문 이미지 2장 생성 및 저장
- [ ] SEO Agent: SEO 메타데이터 및 점수 생성
- [ ] Quality Gate: 통과/실패 케이스 모두 정상 동작
- [ ] Publishing: 티스토리 비공개 포스트 정상 게시

모든 항목 완료 후 → **[섹션 07](./section-07-pipeline-test.md)** 로 이동
