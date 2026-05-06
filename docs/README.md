# 기술블로그 자동배포 에이전트 — 섹션별 상세 안내서 인덱스

이 폴더에는 기술블로그 자동화 에이전트 세팅 및 운영을 위한 **12개 섹션 상세 안내서**가 있습니다.  
순서대로 진행하면 처음 설치부터 운영까지 완료할 수 있습니다.

---

## 섹션 목록

| # | 파일 | 내용 요약 | 소요 시간 |
|---|------|---------|---------|
| 01 | [section-01-system-requirements.md](./section-01-system-requirements.md) | Python 3.12, Docker, Node.js, Git 설치 및 버전 확인 | 10~20분 |
| 02 | [section-02-external-services.md](./section-02-external-services.md) | 티스토리 OAuth 토큰 발급, OpenAI/Anthropic API 키 발급 | 20~40분 |
| 03 | [section-03-project-environment.md](./section-03-project-environment.md) | Python 가상환경, pip 패키지 설치, .env 작성 | 10~20분 |
| 04 | [section-04-docker-infrastructure.md](./section-04-docker-infrastructure.md) | Docker Compose로 PostgreSQL·Redis 실행 및 연결 확인 | 10~15분 |
| 05 | [section-05-database-init.md](./section-05-database-init.md) | DB 테이블 생성 (posts, analytics, human_review_queue) | 5분 |
| 06 | [section-06-agent-verification.md](./section-06-agent-verification.md) | 6개 에이전트 개별 동작 테스트 스크립트 포함 | 30~60분 |
| 07 | [section-07-pipeline-test.md](./section-07-pipeline-test.md) | Thanos 오케스트레이터 전체 파이프라인 1회 테스트 | 5~10분 |
| 08 | [section-08-celery-schedule.md](./section-08-celery-schedule.md) | Celery Worker·Beat 기동, 자동 스케줄 설정 | 10~20분 |
| 09 | [section-09-operations.md](./section-09-operations.md) | Human Review 큐 처리, 로그 모니터링, 분석 리포트 | 상시 |
| 10 | [section-10-tuning.md](./section-10-tuning.md) | 콘텐츠 품질·비용·스케줄 최적화 튜닝 | 30분 |
| 11 | [section-11-troubleshooting.md](./section-11-troubleshooting.md) | LLM/티스토리/DB/Redis/품질 오류 해결 방법 | 참조용 |
| 12 | [section-12-security.md](./section-12-security.md) | API 키 보안, DB 비밀번호 변경, 보안 체크리스트 | 20~30분 |

---

## 빠른 시작 경로

### 처음 세팅하는 경우

```
01 → 02 → 03 → 04 → 05 → 06 → 07 → 08 → 12
```

### 이미 운영 중인 시스템 관리

```
09 (일상 운영)
10 (품질·비용 조정)
11 (오류 발생 시)
```

### 보안 점검만 하는 경우

```
12
```

---

## 관련 파일

| 파일 | 역할 |
|-----|------|
| [setup-guide.md](./setup-guide.md) | 전체 12섹션 요약 개요서 |
| [techblog-automation-agent-plan.md](./techblog-automation-agent-plan.md) | 에이전트 아키텍처 설계 보고서 |
