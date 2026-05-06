# 섹션 12 — 보안 체크리스트

**이전 단계:** [섹션 11 — 오류 해결 방법](./section-11-troubleshooting.md)  
**전체 가이드:** [setup-guide.md](./setup-guide.md)

---

## 개요

자동화 시스템을 안전하게 운영하기 위해 반드시 확인해야 할 보안 사항을 점검합니다.  
특히 API 키, 데이터베이스 자격증명, 코드 샌드박스 안전성은 운영 시작 전에 확인이 필요합니다.

---

## 12-1. API 키 및 자격증명 보안

### 검사 1: .env 파일이 Git에 포함되지 않는지 확인

```powershell
# .gitignore 에 .env가 포함되어 있는지 확인
Select-String -Path .gitignore -Pattern "^\.env"

# Git 추적 파일 중 .env가 있는지 확인 (있으면 즉시 제거)
git ls-files --error-unmatch .env 2>&1
# 출력이 없거나 "error: pathspec '.env' did not match" 이면 안전
```

**만약 .env가 이미 커밋된 경우:**
```powershell
# 커밋 이력에서 .env 제거
git rm --cached .env
git commit -m "chore: remove .env from tracking"

# .gitignore에 추가
Add-Content .gitignore "`n.env"
```

> **주의:** 이미 원격 저장소에 푸시된 경우 API 키를 **즉시 재발급**해야 합니다.  
> 유출된 키는 발급 즉시 무효화합니다.

---

### 검사 2: 소스 코드에 하드코딩된 자격증명 없는지 확인

```powershell
# API 키 패턴 검색
Select-String -Recurse -Path "*.py" -Pattern "sk-proj-|sk-ant-|access_token\s*=\s*['""]"

# 일반적인 자격증명 패턴 검색
Select-String -Recurse -Path "*.py" -Pattern "password\s*=\s*['""][^'""]"
```

출력이 없어야 안전합니다.  
자격증명이 발견되면 환경 변수로 이동합니다.

---

### 검사 3: 민감한 파일의 권한 설정 (Linux/macOS)

```bash
# .env 파일을 소유자만 읽을 수 있도록 설정
chmod 600 .env

# 확인
ls -la .env
# -rw------- 1 user user ... .env
```

---

## 12-2. 데이터베이스 보안

### 검사 4: PostgreSQL 기본 비밀번호 변경

`docker-compose.yml`의 기본 비밀번호 `password`는 반드시 변경합니다.

**Step 1: `docker-compose.yml` 수정**
```yaml
postgres:
  environment:
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}    # 환경 변수로 분리
```

**Step 2: `.env`에 강력한 비밀번호 추가**
```dotenv
POSTGRES_PASSWORD=MyStr0ng!P@ssw0rd#2026
DATABASE_URL=postgresql+asyncpg://techblog:MyStr0ng!P@ssw0rd#2026@localhost:5432/techblog
```

**비밀번호 강도 기준:**
- 최소 12자 이상
- 대문자, 소문자, 숫자, 특수문자 포함
- 사전에 있는 단어 사용 금지

**Step 3: 컨테이너 재생성**
```powershell
docker compose down -v   # 기존 볼륨 삭제
docker compose up -d postgres redis
python -c "import asyncio; from core.database import init_db; asyncio.run(init_db())"
```

---

### 검사 5: DB 포트가 외부에 노출되지 않는지 확인

`docker-compose.yml`의 포트 바인딩이 `127.0.0.1:`로 시작하는지 확인합니다.

```yaml
# 올바른 설정 (로컬호스트만 접근 가능)
ports:
  - "127.0.0.1:5432:5432"

# 잘못된 설정 (모든 인터페이스에서 접근 가능 — 위험)
ports:
  - "5432:5432"
  - "0.0.0.0:5432:5432"
```

```powershell
# 현재 포트 바인딩 확인
docker compose ps
# 또는
netstat -ano | Select-String ":5432"
# "127.0.0.1:5432" 만 나와야 정상
```

---

## 12-3. 코드 샌드박스 보안

Code Example 에이전트는 LLM이 생성한 코드를 실제로 실행합니다.  
다음 보안 사항을 반드시 확인합니다.

### 검사 6: 코드 실행 타임아웃 설정 확인

`agents/code_example_agent.py`에서 타임아웃이 설정되어 있는지 확인합니다.

```python
# agents/code_example_agent.py 에서 확인
EXECUTION_TIMEOUT = 30    # 초 (기본값: 30초)

# subprocess 실행 시 timeout 파라미터 확인
result = subprocess.run(
    cmd,
    capture_output=True,
    text=True,
    timeout=EXECUTION_TIMEOUT,    # 이 파라미터가 반드시 존재해야 함
    cwd=temp_dir
)
```

타임아웃이 없으면 무한 루프 코드가 에이전트를 영구적으로 차단할 수 있습니다.

### 검사 7: 위험한 시스템 명령어 차단

```python
# agents/code_example_agent.py 에 추가 권장
BLOCKED_PATTERNS = [
    r"import\s+os.*system",
    r"subprocess\.call",
    r"subprocess\.Popen",
    r"__import__",
    r"exec\(",
    r"eval\(",
    r"open\s*\(.*['\"]w['\"]",   # 파일 쓰기
    r"shutil\.rmtree",
    r"os\.remove",
]

def is_safe_code(code: str) -> bool:
    import re
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, code):
            return False
    return True
```

---

## 12-4. API 사용량 한도 설정

### 검사 8: OpenAI 월 지출 한도 설정

1. https://platform.openai.com/settings/organization/limits 접속
2. **"Soft limit"** 설정: 예산의 80% (예: $20이면 $16)
3. **"Hard limit"** 설정: 최대 예산 (예: $20)

이메일 알림이 등록된 주소로 발송되므로 실제 사용 주소를 등록합니다.

### 검사 9: Anthropic 크레딧 알림 설정

1. https://console.anthropic.com/settings/billing 접속
2. Low Balance 알림 활성화

---

## 12-5. 티스토리 계정 보안

### 검사 10: Access Token 노출 범위 최소화

티스토리 Access Token은 블로그 전체에 대한 쓰기 권한을 가집니다.  
다음 사항을 확인합니다.

- Access Token이 `.env` 파일에만 저장되어 있는지 확인
- 로그 파일에 Access Token이 출력되지 않는지 확인:

```powershell
# 로그에서 토큰 패턴 검색
Select-String -Recurse -Path "logs\*.log" -Pattern "access_token=[a-zA-Z0-9]+"
```

`utils/tistory_client.py`에서 로그 마스킹이 되어 있는지 확인합니다.

```python
# 토큰은 앞 8자만 로그에 출력
logger.debug("Tistory API call", token_prefix=self.access_token[:8] + "...")
```

---

## 12-6. 네트워크 및 컨테이너 보안

### 검사 11: Docker 컨테이너 권한 최소화

`docker-compose.yml`에서 컨테이너가 root 권한으로 실행되지 않도록 합니다.

```yaml
# docker-compose.yml 에 추가 권장
techblog-worker:
  security_opt:
    - no-new-privileges:true
  read_only: true                    # 파일시스템 읽기 전용
  tmpfs:
    - /tmp                           # /tmp는 임시 파일 허용
  volumes:
    - image_storage:/app/storage/images   # 이미지 저장 폴더만 쓰기 허용
```

### 검사 12: 불필요한 포트 비노출 확인

외부에 열려 있는 포트 목록을 확인합니다.

```powershell
netstat -ano | Where-Object { $_ -match "LISTENING" } |
  Where-Object { $_ -match ":5432|:6379|:5555" }
```

모든 포트가 `127.0.0.1:xxxx` 형태여야 합니다.  
`0.0.0.0:xxxx`가 나타나면 외부 접근이 가능한 상태입니다.

---

## 12-7. 정기 보안 점검 자동화

아래 스크립트를 주기적으로 실행해 보안 상태를 점검합니다.

```python
# ops/security_check.py
import os
import subprocess
import re

checks = []

# 1. .env가 git에 없는지 확인
result = subprocess.run(
    ["git", "ls-files", ".env"],
    capture_output=True, text=True
)
checks.append((".env Git 비추적", result.stdout.strip() == ""))

# 2. 소스 코드 내 API 키 하드코딩 확인
found = False
for root, _, files in os.walk("."):
    if ".venv" in root or ".git" in root:
        continue
    for file in files:
        if not file.endswith(".py"):
            continue
        path = os.path.join(root, file)
        with open(path, encoding="utf-8", errors="ignore") as f:
            content = f.read()
        if re.search(r"sk-proj-[A-Za-z0-9]|sk-ant-[A-Za-z0-9]", content):
            found = True
            print(f"  ⚠ API 키 발견: {path}")
checks.append(("소스 코드 내 API 키 없음", not found))

# 3. .env 파일 존재 확인
checks.append((".env 파일 존재", os.path.isfile(".env")))

# 4. storage 폴더 .gitignore 포함 확인
with open(".gitignore", encoding="utf-8") as f:
    gitignore = f.read()
checks.append(("storage/ gitignore 포함", "storage/" in gitignore))
checks.append(("logs/ gitignore 포함",    "logs/" in gitignore))

print("=" * 50)
print("  보안 점검 결과")
print("=" * 50)
all_ok = True
for name, ok in checks:
    print(f"  {'✅' if ok else '❌'}  {name}")
    if not ok:
        all_ok = False
print("=" * 50)
if all_ok:
    print("  모든 보안 항목 정상")
else:
    print("  ❌ 위 항목들을 즉시 조치하세요")
```

```powershell
python ops/security_check.py
```

---

## 최종 보안 체크리스트

운영 시작 전 아래 모든 항목을 확인합니다.

### 자격증명 보안
- [ ] `.env` 파일이 `.gitignore`에 포함됨
- [ ] `.env` 파일이 Git 추적 대상이 아님 (`git ls-files .env` → 출력 없음)
- [ ] 소스 코드 내 API 키 하드코딩 없음
- [ ] Linux/macOS: `.env` 파일 권한이 `600`

### 데이터베이스 보안
- [ ] PostgreSQL 기본 비밀번호 `password` → 강력한 비밀번호로 변경
- [ ] DB 포트 바인딩이 `127.0.0.1:5432` (외부 미노출)
- [ ] Redis 포트 바인딩이 `127.0.0.1:6379`

### API 사용 제한
- [ ] OpenAI Hard Limit 설정 완료
- [ ] OpenAI Soft Limit 설정 완료
- [ ] Anthropic Low Balance 알림 설정

### 코드 실행 보안
- [ ] Code Example 에이전트 실행 타임아웃 30초 설정 확인
- [ ] 위험 코드 패턴 차단 로직 존재 확인

### 티스토리 보안
- [ ] Access Token이 로그에 전체 출력되지 않음 (마스킹 확인)
- [ ] Access Token이 `.env`에만 저장됨

### 운영 보안
- [ ] `ops/security_check.py` 실행 → 모든 항목 ✅
- [ ] 첫 자동 게시 후 비공개 포스트 품질 확인 완료
- [ ] `visibility: 3` (공개) 전환 시 의도적으로 결정

---

## 축하합니다!

모든 12개 섹션을 완료했습니다.  
이제 기술 블로그 자동화 에이전트 시스템이 완전히 설정되고 안전하게 운영될 준비가 되었습니다.

### 운영 시작 순서 요약

```
1. docker compose up -d                       # 인프라 시작
2. celery -A orchestrator.thanos worker &     # Worker 시작
3. celery -A orchestrator.thanos beat &       # Beat 시작
4. python main.py run --topics "첫 포스트"    # 수동 1회 실행
5. 결과 확인 후 visibility: 3 (공개) 전환     # 자동 공개 활성화
```

**전체 가이드 목차:** [setup-guide.md](./setup-guide.md)
