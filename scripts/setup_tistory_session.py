"""
티스토리 세션 저장 스크립트 (최초 1회만 실행)
================================================
실제 Chrome 브라우저 창을 열어 직접 카카오 로그인을 수행한 뒤,
생성된 쿠키·세션 데이터를 JSON 파일로 저장합니다.

이후 자동화 스크립트는 저장된 세션을 로드하여
로그인 없이 글쓰기 페이지에 바로 접근합니다.

실행 방법:
    python scripts/setup_tistory_session.py

세션 만료 시 (보통 30~90일):
    동일 스크립트를 다시 실행하면 갱신됩니다.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from playwright.async_api import async_playwright
from core.config import settings

SESSION_FILE = Path(settings.tistory_session_file)
TISTORY_HOME = "https://www.tistory.com"
WRITE_URL = f"https://{settings.tistory_blog_name}.tistory.com/manage/newpost/"


async def main() -> None:
    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)

    print()
    print("=" * 60)
    print("  티스토리 세션 저장 스크립트")
    print("=" * 60)
    print()
    print("  [진행 순서]")
    print("  1. 잠시 후 Chrome 브라우저가 열립니다.")
    print("  2. 카카오 계정으로 직접 로그인하세요.")
    print("     (2단계 인증·보안 문자가 있으면 직접 처리)")
    print("  3. 티스토리 홈 또는 관리 페이지가 뜨면")
    print("     이 터미널로 돌아와 Enter 를 누르세요.")
    print()
    print(f"  블로그 이름: {settings.tistory_blog_name}")
    print(f"  세션 저장 위치: {SESSION_FILE}")
    print()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--start-maximized",
            ],
        )
        ctx = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )
        page = await ctx.new_page()
        await page.goto(TISTORY_HOME)

        print("  브라우저가 열렸습니다.")
        print("  카카오 로그인을 완료한 뒤 Enter 를 누르세요...")
        print()

        # 사용자가 직접 로그인할 때까지 대기
        input("  >>> Enter 키를 누르면 세션을 저장합니다: ")

        current_url = page.url
        print(f"\n  현재 페이지: {current_url}")

        # 로그인 상태 확인
        if "login" in current_url or "kakao" in current_url:
            print()
            print("  ⚠ 아직 로그인이 완료되지 않은 것 같습니다.")
            print("  로그인을 완료한 뒤 다시 시도하세요.")
            await browser.close()
            return

        # 세션 저장
        await ctx.storage_state(path=str(SESSION_FILE))

        print()
        print(f"  ✅ 세션 저장 완료: {SESSION_FILE}")
        print()

        # 글쓰기 페이지 접근 테스트
        print("  글쓰기 페이지 접근 테스트 중...")
        await page.goto(WRITE_URL, timeout=15_000)
        await page.wait_for_timeout(2_000)

        if "login" in page.url or "kakao" in page.url:
            print()
            print("  ⚠ 글쓰기 페이지 접근 실패 (세션 문제)")
            print(f"  현재 URL: {page.url}")
            print("  블로그 이름이 맞는지 확인하세요: TISTORY_BLOG_NAME =", settings.tistory_blog_name)
        else:
            print(f"  ✅ 글쓰기 페이지 정상 접근: {page.url}")
            print()
            print("  이제 자동화 에이전트를 실행할 수 있습니다.")
            print("  다음 명령으로 테스트하세요:")
            print()
            print("    python main.py run --topics \"Python 비동기 프로그래밍\"")

        await browser.close()

    print()
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
