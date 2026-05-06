# 섹션 02 — 사전 준비 : 외부 서비스 계정 생성

**이전 단계:** [섹션 01 — 시스템 요구사항 확인](./section-01-system-requirements.md)  
**다음 단계:** [섹션 03 — 프로젝트 환경 세팅](./section-03-project-environment.md)

---

## 개요

자동화 에이전트가 동작하려면 아래 3가지 외부 서비스의 API 자격증명이 필요합니다.

| 서비스 | 용도 | 필수 여부 |
|-------|------|---------|
| 티스토리 Open API | 블로그 포스트 자동 게시 | **필수** |
| OpenAI | GPT-4o 콘텐츠 생성 / DALL-E 3 이미지 생성 | **필수** |
| Anthropic | Claude 3.7 폴백 LLM | 선택 |

이 섹션이 끝나면 수집해야 할 값:

```
TISTORY_APP_ID=
TISTORY_SECRET_KEY=
TISTORY_ACCESS_TOKEN=
TISTORY_BLOG_NAME=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=          (선택)
```

---

## 2-1. 티스토리 Open API — App 등록

### Step 1: 티스토리 로그인 확인

1. https://www.tistory.com 에 접속해 본인 계정으로 로그인합니다.
2. 자동 포스팅을 원하는 **티스토리 블로그가 개설되어 있어야** 합니다.  
   블로그가 없다면 https://www.tistory.com/start 에서 먼저 생성하세요.

### Step 2: App 등록 페이지 접속

브라우저에서 아래 URL로 이동합니다.

```
https://www.tistory.com/guide/api/manage/register
```

> 로그인 상태에서 접속해야 합니다. 로그인되어 있지 않으면 로그인 페이지로 리다이렉트됩니다.

### Step 3: App 정보 입력

아래 표를 참고해 각 항목을 입력합니다.

| 입력 항목 | 권장 입력값 | 설명 |
|---------|----------|------|
| 서비스명 (앱 이름) | `TechBlog Automation` | 식별용 이름. 자유롭게 설정 가능 |
| 설명 | `기술 블로그 자동 포스팅 에이전트` | 선택 항목 |
| 서비스 URL | `http://localhost:8000` | 로컬 개발 환경이므로 localhost 사용 |
| CallBack URL | `http://localhost:8000/callback` | OAuth 인증 후 리다이렉트 주소 |
| 서비스 형태 | `Web` | 선택 |

### Step 4: App ID / Secret Key 복사

등록 완료 화면에서 아래 두 값을 안전한 곳(메모장 등)에 즉시 복사합니다.

```
App ID      = 1234567890abcdef    ← 이 값이 TISTORY_APP_ID
Secret Key  = abcdef1234567890    ← 이 값이 TISTORY_SECRET_KEY
```

---

## 2-2. 티스토리 Access Token 발급 (OAuth 2.0 인증 흐름)

티스토리는 OAuth 2.0 Authorization Code Flow를 사용합니다.  
총 3단계로 진행됩니다.

---

### Phase A: Authorization Code 요청

브라우저 주소창에 아래 URL을 직접 입력합니다.  
`{APP_ID}` 를 2-1에서 발급받은 실제 App ID로 교체하세요.

```
https://www.tistory.com/oauth/authorize?client_id={APP_ID}&redirect_uri=http://localhost:8000/callback&response_type=code
```

**예시 (App ID가 `abc123xyz`인 경우):**
```
https://www.tistory.com/oauth/authorize?client_id=abc123xyz&redirect_uri=http://localhost:8000/callback&response_type=code
```

접속 후 다음 화면이 나타납니다.

1. **"TechBlog Automation 앱이 다음 권한을 요청합니다"** 화면
2. **"허가하기"** 버튼 클릭

클릭 후 브라우저 주소창이 아래 형태로 변경됩니다.

```
http://localhost:8000/callback?code=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

> **"이 사이트에 연결할 수 없음"** 오류가 나타나도 정상입니다.  
> localhost:8000 서버가 실제로 실행 중이지 않기 때문입니다.  
> **주소창의 URL에서 `code=` 뒤의 값만 복사**하면 됩니다.

복사 예시:
```
code=e47d9c2a3b1f8e5d0c6a9b2f4e7c8d1a
```

---

### Phase B: Access Token 교환

복사한 Authorization Code를 Access Token으로 교환합니다.  
`{APP_ID}`, `{SECRET_KEY}`, `{CODE}` 를 실제 값으로 교체하고 터미널에서 실행합니다.

**PowerShell (Windows):**
```powershell
$APP_ID = "여기에_App_ID_입력"
$SECRET = "여기에_Secret_Key_입력"
$CODE   = "여기에_code_값_입력"

Invoke-RestMethod -Uri ("https://www.tistory.com/oauth/access_token" +
  "?client_id=$APP_ID" +
  "&client_secret=$SECRET" +
  "&redirect_uri=http://localhost:8000/callback" +
  "&code=$CODE" +
  "&grant_type=authorization_code")
```

**bash (macOS / Linux):**
```bash
APP_ID="여기에_App_ID_입력"
SECRET="여기에_Secret_Key_입력"
CODE="여기에_code_값_입력"

curl -G "https://www.tistory.com/oauth/access_token" \
  --data-urlencode "client_id=$APP_ID" \
  --data-urlencode "client_secret=$SECRET" \
  --data-urlencode "redirect_uri=http://localhost:8000/callback" \
  --data-urlencode "code=$CODE" \
  --data-urlencode "grant_type=authorization_code"
```

**정상 응답 예시:**
```
access_token=d8f3a2c1b5e9f4a0c7d2e3b8f1a5c9d2
```

이 값이 `TISTORY_ACCESS_TOKEN`입니다. 복사해 둡니다.

---

### Phase C: Access Token 동작 확인

발급받은 토큰으로 블로그 정보 조회가 되는지 확인합니다.

**PowerShell:**
```powershell
$TOKEN = "여기에_access_token_입력"
Invoke-RestMethod -Uri "https://www.tistory.com/apis/blog/info?access_token=$TOKEN&output=json"
```

**bash:**
```bash
TOKEN="여기에_access_token_입력"
curl "https://www.tistory.com/apis/blog/info?access_token=$TOKEN&output=json"
```

**정상 응답 예시:**
```json
{
  "tistory": {
    "status": "200",
    "item": {
      "blogs": [
        {
          "name": "mytech",
          "url": "https://mytech.tistory.com",
          "title": "내 기술 블로그"
        }
      ]
    }
  }
}
```

응답의 `name` 필드 값이 `TISTORY_BLOG_NAME`입니다.

---

## 2-3. 티스토리 카테고리 ID 확인

포스트를 특정 카테고리에 자동 분류하려면 카테고리 ID를 확인해야 합니다.

**PowerShell:**
```powershell
$TOKEN     = "여기에_access_token_입력"
$BLOG_NAME = "여기에_블로그이름_입력"

Invoke-RestMethod -Uri "https://www.tistory.com/apis/category/list?access_token=$TOKEN&output=json&blogName=$BLOG_NAME"
```

**응답 예시:**
```json
{
  "tistory": {
    "item": {
      "categories": [
        { "id": "1", "name": "전체" },
        { "id": "123456", "name": "백엔드" },
        { "id": "123457", "name": "프론트엔드" },
        { "id": "123458", "name": "DevOps" }
      ]
    }
  }
}
```

각 카테고리의 `id` 값을 기록해 둡니다.  
나중에 `config/settings.yaml`의 `tistory.default_category_id`에 사용합니다.

---

## 2-4. OpenAI API 키 발급

### Step 1: 계정 생성 또는 로그인

1. https://platform.openai.com/signup 에서 계정을 생성합니다.  
   (이미 계정이 있다면 https://platform.openai.com/login)

### Step 2: API 키 생성

1. 로그인 후 우측 상단 프로필 → **"API Keys"** 클릭  
   (또는 https://platform.openai.com/api-keys 직접 접속)
2. **"+ Create new secret key"** 버튼 클릭
3. 키 이름 입력: `techblog-agent`
4. 프로젝트는 **Default project** 선택
5. **"Create secret key"** 클릭

**생성된 키 형태:**
```
sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

> **주의:** 이 화면을 닫으면 키를 다시 볼 수 없습니다. 반드시 즉시 복사하세요.

### Step 3: 결제 정보 등록 (필수)

API를 사용하려면 결제 수단이 등록되어 있어야 합니다.

1. https://platform.openai.com/settings/organization/billing 접속
2. **"Add payment method"** 에서 신용카드 등록
3. 과도한 청구를 방지하기 위해 **"Usage limits"** 탭에서 월 한도를 설정합니다.
   - Soft limit: $15 (초과 시 이메일 알림)
   - Hard limit: $30 (초과 시 API 차단)

### Step 4: API 연결 확인

```powershell
$OPENAI_KEY = "sk-proj-xxxx..."
$body = @{
    model    = "gpt-4o-mini"
    messages = @(@{ role = "user"; content = "ping" })
} | ConvertTo-Json

Invoke-RestMethod -Uri "https://api.openai.com/v1/chat/completions" `
  -Method POST `
  -Headers @{ Authorization = "Bearer $OPENAI_KEY"; "Content-Type" = "application/json" } `
  -Body $body | Select-Object -ExpandProperty choices
```

**정상 응답:** `message.content`에 응답 텍스트가 포함되면 성공입니다.

---

## 2-5. Anthropic API 키 발급 (선택 — 폴백용)

OpenAI API 장애 시 Claude 3.7 Sonnet으로 자동 전환하는 폴백 기능용입니다.  
생략해도 시스템은 정상 동작하지만, 안정성을 높이려면 등록을 권장합니다.

### Step 1: 계정 생성

1. https://console.anthropic.com 접속
2. **"Sign up"** 클릭 후 이메일로 계정 생성

### Step 2: API 키 생성

1. 로그인 후 좌측 메뉴 **"API Keys"** 클릭
2. **"+ Create Key"** 클릭
3. 키 이름: `techblog-fallback`
4. **"Create Key"** 클릭 후 표시된 키(`sk-ant-...`) 즉시 복사

### Step 3: 크레딧 확인

https://console.anthropic.com/settings/billing 에서 잔여 크레딧을 확인합니다.  
무료 체험 크레딧이 제공되지 않으므로 카드 등록이 필요할 수 있습니다.

---

## 2-6. 수집한 자격증명 최종 정리

이 섹션이 끝나면 아래 값이 모두 준비되어 있어야 합니다.

```
✅ TISTORY_APP_ID          = 티스토리에서 발급한 App ID
✅ TISTORY_SECRET_KEY      = 티스토리에서 발급한 Secret Key
✅ TISTORY_ACCESS_TOKEN    = OAuth 인증으로 발급한 Access Token
✅ TISTORY_BLOG_NAME       = 블로그 주소에서 확인한 블로그 이름
✅ OPENAI_API_KEY          = OpenAI에서 발급한 API 키 (sk-proj-...)
☐ ANTHROPIC_API_KEY       = Anthropic에서 발급한 API 키 (선택)
```

> **보안 주의:**  
> 위 값들은 절대로 소스 코드에 직접 입력하거나 Git에 커밋하지 마세요.  
> 다음 섹션에서 `.env` 파일에만 기록합니다.

---

## 완료 기준

- [ ] 티스토리 App ID / Secret Key 확보
- [ ] 티스토리 Access Token 발급 및 동작 확인
- [ ] 블로그 이름 및 카테고리 ID 확인
- [ ] OpenAI API 키 발급 및 결제 한도 설정
- [ ] (선택) Anthropic API 키 발급

모든 항목 완료 후 → **[섹션 03](./section-03-project-environment.md)** 으로 이동
