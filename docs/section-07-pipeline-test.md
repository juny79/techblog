# 섹션 07 — 전체 파이프라인 1회 테스트 실행

**이전 단계:** [섹션 06 — 에이전트별 동작 확인](./section-06-agent-verification.md)  
**다음 단계:** [섹션 08 — Celery 자동 스케줄 실행](./section-08-celery-schedule.md)

---

## 개요

섹션 06에서 각 에이전트가 개별적으로 정상 동작하는 것을 확인했다면, 이제 Thanos 오케스트레이터가 모든 에이전트를 순서대로 실행하는 전체 파이프라인을 1회 테스트합니다.

**파이프라인 실행 흐름:**

```
[시작]
  ↓
Power Stone (주제 탐색)
  ↓
Mind Stone (콘텐츠 생성)
  ↓          ↓
Code Agent  Image Agent  ← 병렬 실행
  ↓          ↓
   (결과 합산)
  ↓
Reality Stone (SEO 최적화)
  ↓
Soul Stone (품질 검수)
  ↓ 통과         ↓ 3회 실패
Space Stone    Human Review Queue
(티스토리 게시)
  ↓
Time Stone (성과 수집)
  ↓
[완료]
```

---

## 7-1. 테스트 전 사전 점검

파이프라인 실행 전 아래 항목을 재확인합니다.

```powershell
# 1. Docker 컨테이너 상태
docker compose ps

# 2. .env 설정 로드 확인
python -c "from core.config import settings; print('BLOG:', settings.tistory_blog_name)"

# 3. visibility 설정 확인 (반드시 0 = 비공개 유지)
python -c "
from core.config import load_yaml_settings
cfg = load_yaml_settings()
vis = cfg.get('blog', {}).get('tistory', {}).get('visibility', '?')
print(f'visibility: {vis}  (0=비공개, 3=공개)')
if str(vis) != '0':
    print('⚠ 테스트 중에는 visibility를 0으로 설정하세요!')
"
```

**체크리스트:**
- [ ] postgres, redis 컨테이너 모두 `healthy`
- [ ] `visibility: 0` (비공개) 확인
- [ ] OpenAI API 잔여 크레딧 확인 (약 $0.15~0.30 소요)

---

## 7-2. 방법 1 — 주제를 직접 지정해 실행 (첫 테스트 권장)

주제를 직접 지정하면 예측 가능한 결과를 얻을 수 있어 첫 번째 테스트에 적합합니다.

```powershell
python main.py run --topics "Python asyncio 비동기 프로그래밍 완벽 정리"
```

---

## 7-3. 방법 2 — 자동 주제 탐색 후 실행

```powershell
python main.py run
```

Power Stone 에이전트가 실시간으로 트렌딩 주제를 탐색해 자동으로 포스트를 생성합니다.

---

## 7-4. 실행 중 콘솔 출력 해설

파이프라인이 실행되면 아래와 같은 로그가 출력됩니다.

```
[2026-05-07 09:00:01] snap_begin  run_id=abc12345
```
→ Thanos 오케스트레이터가 파이프라인 실행을 시작합니다.

```
[2026-05-07 09:00:03] power_stone  Discovering topics...
[2026-05-07 09:00:05] power_stone  Selected: Python asyncio 비동기 프로그래밍 완벽 정리
```
→ Power Stone이 주제를 탐색하고 선택합니다.

```
[2026-05-07 09:00:08] mind_stone   Generating content...
[2026-05-07 09:01:12] mind_stone   Done: 2841 chars, 4 code_blocks
```
→ Mind Stone이 LLM을 통해 포스트 본문을 생성합니다. (약 1분 소요)

```
[2026-05-07 09:01:12] parallel     Starting code+image agents
[2026-05-07 09:01:30] image_agent  Thumbnail saved: storage/images/abc12345_thumbnail.png
[2026-05-07 09:01:32] image_agent  Content image saved: storage/images/abc12345_content.png
[2026-05-07 09:01:34] code_agent   3/4 blocks valid, 1 auto-fixed
```
→ 코드 검증과 이미지 생성이 병렬로 진행됩니다.

```
[2026-05-07 09:01:35] reality_stone  SEO score: 82.4
[2026-05-07 09:01:36] soul_stone     Quality check: PASSED (score=100.0)
```
→ SEO 분석 후 품질 검수를 통과합니다.

```
[2026-05-07 09:01:40] space_stone   Uploading images...
[2026-05-07 09:01:45] space_stone   Published: https://mytech.tistory.com/43 (postId=43)
```
→ 이미지를 업로드하고 티스토리에 포스트를 게시합니다.

```
============================================================
  Snap complete!
============================================================
  Run ID       : abc12345
  Published    : 1
  Failed       : 0
  Human Review : 0
  Status       : completed
============================================================

  ✅ Python asyncio 비동기 프로그래밍 완벽 정리
     https://mytech.tistory.com/43
```
→ 최종 결과를 요약합니다.

---

## 7-5. 파이프라인 실행 소요 시간

| 단계 | 소요 시간 | 변동 요인 |
|------|---------|---------|
| 주제 탐색 | 5~15초 | 외부 사이트 응답 속도 |
| 콘텐츠 생성 | 30초~2분 | LLM 응답 속도, 목표 분량 |
| 코드 검증 (병렬) | 5~30초 | 코드 블록 수, 오류 여부 |
| 이미지 생성 (병렬) | 30~60초 | DALL-E 서버 응답 속도 |
| SEO 최적화 | 10~30초 | LLM 응답 속도 |
| 품질 검수 | 1~3초 | 로컬 처리 |
| 이미지 업로드 | 5~15초 | 네트워크 속도 |
| 티스토리 게시 | 3~8초 | API 응답 속도 |
| **합계** | **약 2~5분** | |

---

## 7-6. 게시 결과 직접 확인

파이프라인이 완료되면 아래 방법으로 결과를 확인합니다.

### 티스토리 블로그에서 확인

1. https://www.tistory.com/manage/posts 접속
2. 비공개 목록에서 생성된 포스트 클릭
3. 아래 항목들을 직접 검토합니다.

| 확인 항목 | 기대 결과 |
|---------|---------|
| 제목 | 자연스러운 한국어 기술 제목 |
| 본문 | 1500자 이상, 소제목(##) 포함 |
| 코드 블록 | 문법 강조(하이라이트) 적용 |
| 섬네일 이미지 | 포스트 상단에 표시 |
| 태그 | 관련 기술 키워드 5~10개 |
| 카테고리 | 올바른 카테고리로 분류 |

### DB에서 이력 확인

```python
# check_result.py
import asyncio
from sqlalchemy import select, desc
from core.database import AsyncSessionFactory, PostRecord

async def main():
    async with AsyncSessionFactory() as session:
        result = await session.execute(
            select(PostRecord).order_by(desc(PostRecord.created_at)).limit(3)
        )
        posts = result.scalars().all()

    for p in posts:
        print(f"─" * 50)
        print(f"제목     : {p.title}")
        print(f"상태     : {p.pipeline_status}")
        print(f"URL      : {p.published_url or '미게시'}")
        print(f"단어 수  : {p.word_count}")
        print(f"SEO 점수 : {p.seo_score}")
        print(f"생성 시각: {p.created_at}")

asyncio.run(main())
```

```powershell
python check_result.py
```

---

## 7-7. 품질 검수 실패 시 동작 확인

품질 기준 미달 시 파이프라인이 어떻게 동작하는지 확인합니다.

`config/settings.yaml`의 `min_word_count`를 일시적으로 매우 높게 설정합니다.

```yaml
blog:
  min_word_count: 99999    # 의도적으로 통과 불가 수준으로 설정
```

파이프라인을 실행하면:

1. Soul Stone이 품질 검수 실패를 감지합니다.
2. Thanos가 문제 유형에 따라 관련 에이전트를 재실행합니다.
3. 3회 실패 후 `human_review_queue` 테이블에 등록됩니다.

**Human Review Queue 확인:**
```powershell
docker exec -it techblog-postgres psql -U techblog -d techblog -c "
SELECT topic_title, issues, queued_at
FROM human_review_queue
WHERE resolved = false;"
```

테스트 후 `settings.yaml`의 `min_word_count`를 원래 값으로 복원합니다.

---

## 7-8. 공개 전환 절차

테스트가 완료되고 포스트 품질에 만족한다면 공개로 전환합니다.

**방법 1 — 전체 자동 공개 (이후 게시되는 포스트 모두)**

`config/settings.yaml`:
```yaml
blog:
  tistory:
    visibility: 3    # 0 → 3 으로 변경
```

**방법 2 — 개별 수동 공개 (기존 비공개 포스트만)**

티스토리 블로그 관리 → 포스트 선택 → 편집 → 공개로 변경

---

## 완료 기준

- [ ] `python main.py run --topics "주제"` 오류 없이 완료
- [ ] 콘솔에 `Snap complete!` 및 티스토리 URL 출력
- [ ] 티스토리 비공개 포스트 목록에서 생성된 포스트 확인
- [ ] 포스트 내용(본문, 이미지, 코드, 태그) 품질 검토 완료
- [ ] DB `posts` 테이블에 이력 저장 확인

모든 항목 완료 후 → **[섹션 08](./section-08-celery-schedule.md)** 로 이동
