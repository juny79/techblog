# 섹션 01 — 시스템 요구사항 확인

**이전 단계:** 없음 (첫 번째 단계)  
**다음 단계:** [섹션 02 — 외부 서비스 계정 생성](./section-02-external-services.md)

---

## 개요

에이전트를 실행하기 전에 운영 환경의 소프트웨어 버전이 요구사항을 충족하는지 확인합니다.  
버전 불일치는 런타임 오류나 패키지 설치 실패의 주요 원인입니다.

---

## 1-1. Python 설치 및 버전 확인

### 현재 버전 확인

```powershell
# Windows PowerShell
python --version
# 또는
python3 --version
```

**요구 버전:** Python **3.12.0** 이상

**정상 출력 예시:**
```
Python 3.12.3
```

### Python 3.12가 설치되어 있지 않은 경우

#### Windows

1. https://www.python.org/downloads/ 에 접속합니다.
2. **"Download Python 3.12.x"** 버튼을 클릭해 설치 파일을 내려받습니다.
3. 설치 프로그램 실행 시 반드시 **"Add Python to PATH"** 체크박스를 선택합니다.
4. **"Install Now"** 를 클릭해 설치합니다.
5. 설치 완료 후 터미널(PowerShell)을 재시작하고 버전을 재확인합니다.

#### macOS

```bash
# Homebrew를 통한 설치 (Homebrew가 없으면 https://brew.sh 에서 먼저 설치)
brew install python@3.12

# PATH 등록 (zsh 기준)
echo 'export PATH="/opt/homebrew/opt/python@3.12/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

python3.12 --version
```

#### Ubuntu / Debian

```bash
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3.12-dev python3-pip
python3.12 --version
```

### pip 버전 확인 및 업그레이드

```powershell
pip --version
# 24.0 미만이면 업그레이드 권장
pip install --upgrade pip
```

---

## 1-2. Docker Desktop 설치 및 확인

Docker는 PostgreSQL(데이터베이스)과 Redis(메시지 큐)를 컨테이너로 실행하는 데 사용됩니다.

### 현재 버전 확인

```powershell
docker --version
docker compose version
```

**요구 버전:**
- Docker Engine: **24.0** 이상
- Docker Compose: **2.24** 이상

**정상 출력 예시:**
```
Docker version 26.1.3, build b72abbb
Docker Compose version v2.27.0
```

### Docker Desktop이 설치되어 있지 않은 경우

#### Windows

1. https://www.docker.com/products/docker-desktop/ 에서 **"Download for Windows"** 를 클릭합니다.
2. 설치 파일을 실행하고 모든 기본 옵션을 유지한 채 설치합니다.
3. 설치 완료 후 **Docker Desktop 앱을 실행**합니다. (시스템 트레이에 고래 아이콘이 나타나야 함)
4. Docker Desktop이 완전히 시작될 때까지(고래 아이콘이 정지 상태) 30~60초 대기합니다.
5. PowerShell을 재시작하고 버전을 재확인합니다.

> **WSL2 백엔드 권장:** Docker Desktop 설치 중 "Use WSL 2 instead of Hyper-V" 옵션이 나타나면 활성화하세요. 성능이 더 좋습니다.

#### macOS

```bash
# Homebrew 사용
brew install --cask docker

# 이후 Applications 폴더에서 Docker 앱 실행
open /Applications/Docker.app
```

#### Ubuntu

```bash
# 공식 설치 스크립트
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker

# Docker Compose 플러그인 설치
sudo apt install docker-compose-plugin
```

### Docker 정상 동작 확인

```powershell
docker run --rm hello-world
```

**정상 출력 (일부):**
```
Hello from Docker!
This message shows that your installation appears to be working correctly.
```

---

## 1-3. Node.js 설치 및 확인

Node.js는 코드 예제 에이전트(Code Example Agent)가 JavaScript/TypeScript 코드를 샌드박스에서 실행할 때 필요합니다.

### 현재 버전 확인

```powershell
node --version
npm --version
```

**요구 버전:** Node.js **20 LTS** 이상

**정상 출력 예시:**
```
v20.14.0
10.7.0
```

### Node.js 20 LTS가 설치되어 있지 않은 경우

#### 방법 1 — 공식 설치 파일 (Windows/macOS)

1. https://nodejs.org/en/download 에서 **LTS** 버전을 선택합니다.
2. 운영체제에 맞는 설치 파일을 내려받아 실행합니다.

#### 방법 2 — nvm 사용 (권장)

```bash
# macOS / Linux
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
source ~/.bashrc   # 또는 ~/.zshrc

nvm install 20
nvm use 20
nvm alias default 20
```

```powershell
# Windows — nvm-windows 사용
# https://github.com/coreybutler/nvm-windows/releases 에서 nvm-setup.exe 설치 후
nvm install 20
nvm use 20
```

---

## 1-4. Git 설치 및 확인

```powershell
git --version
```

**요구 버전:** Git **2.40** 이상

**설치되어 있지 않은 경우:**

- Windows: https://git-scm.com/download/win
- macOS: `brew install git`
- Ubuntu: `sudo apt install git`

---

## 1-5. 운영체제별 추가 확인 사항

### Windows 추가 확인

```powershell
# PowerShell 실행 정책 확인 (스크립트 실행 허용 필요)
Get-ExecutionPolicy
```

`Restricted`라면 아래 명령을 **관리자 권한 PowerShell**에서 실행합니다.

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### macOS 추가 확인

```bash
# Xcode Command Line Tools 설치 여부 확인
xcode-select -p

# 미설치 시
xcode-select --install
```

### 포트 충돌 확인

에이전트가 사용하는 포트가 이미 사용 중인지 확인합니다.

```powershell
# Windows
netstat -ano | Select-String ":5432|:6379|:5555"
```

```bash
# macOS / Linux
lsof -i :5432 -i :6379 -i :5555
```

| 포트 | 용도 |
|------|------|
| 5432 | PostgreSQL |
| 6379 | Redis |
| 5555 | Flower (Celery 모니터링, 선택) |

사용 중인 포트가 있으면 `docker-compose.yml`의 포트 매핑을 변경하거나 해당 프로세스를 종료합니다.

---

## 1-6. 전체 요구사항 일괄 확인 스크립트

아래 스크립트를 `check_requirements.py`로 저장해 실행하면 한 번에 모든 요구사항을 확인합니다.

```python
# check_requirements.py
import subprocess
import sys

def check(name, cmd, min_version, parse_fn):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
        version_str = result.stdout.strip() or result.stderr.strip()
        version = parse_fn(version_str)
        ok = version >= min_version
        status = "✅" if ok else "❌"
        print(f"{status} {name}: {version_str.split(chr(10))[0]}")
        if not ok:
            print(f"   → 최소 요구: {'.'.join(map(str, min_version))}")
    except Exception as e:
        print(f"❌ {name}: 확인 실패 ({e})")

def parse_semver(s):
    import re
    m = re.search(r'(\d+)\.(\d+)', s)
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)

print("=" * 40)
print("  시스템 요구사항 확인")
print("=" * 40)
check("Python",         "python --version",         (3, 12), parse_semver)
check("pip",            "pip --version",             (24, 0), parse_semver)
check("Docker",         "docker --version",          (24, 0), parse_semver)
check("Docker Compose", "docker compose version",   (2, 24), parse_semver)
check("Node.js",        "node --version",            (20, 0), parse_semver)
check("Git",            "git --version",             (2, 40), parse_semver)
print("=" * 40)
```

```powershell
python check_requirements.py
```

**모든 항목이 ✅ 이어야** 다음 단계로 진행할 수 있습니다.

---

## 완료 기준

- [ ] `python --version` → 3.12.x 이상
- [ ] `pip --version` → 24.x 이상
- [ ] `docker --version` → 24.x 이상
- [ ] `docker compose version` → 2.24 이상
- [ ] `node --version` → 20.x 이상
- [ ] `git --version` → 2.40 이상
- [ ] `docker run --rm hello-world` → 정상 출력

모든 항목 완료 후 → **[섹션 02](./section-02-external-services.md)** 로 이동
