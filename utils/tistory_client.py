"""
Tistory Playwright Client
~~~~~~~~~~~~~~~~~~~~~~~~~~
Open API 종료(2024.02)에 대응한 브라우저 자동화 방식 구현.

사전 조건:
    python scripts/setup_tistory_session.py  # 최초 1회 — 카카오 로그인 후 세션 저장

흐름:
    1. 저장된 세션(쿠키/로컬스토리지)을 로드해 로그인 상태로 접속
    2. 글쓰기 페이지에서 HTML 모드로 전환
    3. 제목·본문·카테고리·태그 입력 후 발행
"""
from __future__ import annotations

import base64
import re
from pathlib import Path
from typing import Optional

from playwright.async_api import async_playwright, Page

from core.config import settings
from utils.logger import get_logger

logger = get_logger("tistory_playwright")

SESSION_FILE = Path(settings.tistory_session_file)
WRITE_URL = f"https://{settings.tistory_blog_name}.tistory.com/manage/newpost/"
CATEGORY_URL = f"https://{settings.tistory_blog_name}.tistory.com/manage/category/"


class TistoryPlaywrightClient:
    """
    Playwright 기반 티스토리 자동화 클라이언트.

    세션 파일이 없으면 FileNotFoundError를 발생시킵니다.
    세션이 만료되면 RuntimeError를 발생시킵니다.
    """

    # ─── 공개 API ──────────────────────────────────────────────────────────────

    async def write_post(
        self,
        title: str,
        content: str,
        category_id: Optional[int] = None,
        tags: Optional[list[str]] = None,
        visibility: int = 0,
    ) -> dict:
        """
        티스토리에 새 글을 발행합니다.

        Returns:
            {"post_id": str, "url": str}
        """
        self._check_session()

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"],
            )
            ctx = await browser.new_context(
                storage_state=str(SESSION_FILE),
                viewport={"width": 1280, "height": 900},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
            )
            page = await ctx.new_page()
            try:
                return await self._do_write(
                    page,
                    title=title,
                    html_content=content,
                    category_id=category_id,
                    tags=tags or [],
                    visibility=visibility,
                )
            finally:
                await browser.close()

    async def get_categories(self) -> list[dict]:
        """카테고리 목록을 반환합니다."""
        self._check_session()

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            ctx = await browser.new_context(storage_state=str(SESSION_FILE))
            page = await ctx.new_page()
            try:
                return await self._get_categories(page)
            finally:
                await browser.close()

    # ─── 내부 로직 ─────────────────────────────────────────────────────────────

    def _check_session(self) -> None:
        if not SESSION_FILE.exists():
            raise FileNotFoundError(
                f"세션 파일이 없습니다: {SESSION_FILE}\n"
                "다음 명령으로 세션을 저장하세요:\n"
                "  python scripts/setup_tistory_session.py"
            )

    async def _do_write(
        self,
        page: Page,
        *,
        title: str,
        html_content: str,
        category_id: Optional[int],
        tags: list[str],
        visibility: int,
    ) -> dict:
        logger.info(f"글쓰기 페이지 접속: {WRITE_URL}")
        await page.goto(WRITE_URL, wait_until="networkidle", timeout=30_000)

        # 세션 만료 감지
        if "login" in page.url or "kakao" in page.url:
            raise RuntimeError(
                "세션이 만료되었습니다.\n"
                "python scripts/setup_tistory_session.py 를 다시 실행하세요."
            )

        await self._set_title(page, title)
        await self._set_content_html(page, html_content)

        if category_id:
            await self._set_category(page, category_id)
        if tags:
            await self._set_tags(page, tags)

        return await self._publish(page, visibility)

    # ── 제목 ────────────────────────────────────────────────────────────────────

    async def _set_title(self, page: Page, title: str) -> None:
        selectors = [
            "#post-title-inp",
            "input.tf_entry[placeholder*='제목']",
            "input[placeholder*='제목을 입력하세요']",
            ".area_title input",
        ]
        for sel in selectors:
            try:
                await page.wait_for_selector(sel, timeout=5_000)
                await page.fill(sel, title)
                logger.debug(f"제목 입력 완료 [{sel}]")
                return
            except Exception:
                continue
        raise RuntimeError("제목 입력 필드를 찾을 수 없습니다.")

    # ── 본문 (HTML 모드) ─────────────────────────────────────────────────────────

    async def _set_content_html(self, page: Page, html_content: str) -> None:
        """
        에디터를 HTML 모드로 전환한 뒤 본문을 삽입합니다.
        티스토리 신형 에디터(T에디터)의 HTML 소스 모드를 이용합니다.
        """
        # 1. HTML 모드 버튼 클릭
        html_btn_selectors = [
            "button.btn_html",
            "button[data-type='html']",
            "button:has-text('HTML')",
            ".editor_mode button:has-text('HTML')",
            "[class*='htmlMode']",
            "[title='HTML']",
        ]
        for sel in html_btn_selectors:
            try:
                btn = await page.wait_for_selector(sel, timeout=3_000)
                if btn:
                    await btn.click()
                    await page.wait_for_timeout(800)
                    logger.debug(f"HTML 모드 전환 [{sel}]")
                    break
            except Exception:
                continue

        # 2. HTML 편집 텍스트 영역에 내용 입력
        textarea_selectors = [
            "textarea.tf_source",
            "textarea[data-mode='html']",
            ".CodeMirror textarea",
            ".area_write textarea",
        ]
        for sel in textarea_selectors:
            try:
                textarea = await page.wait_for_selector(sel, timeout=3_000)
                if textarea:
                    await textarea.click()
                    await page.keyboard.press("Control+A")
                    await textarea.fill(html_content)
                    logger.debug(f"본문 입력 완료 [{sel}]")
                    return
            except Exception:
                continue

        # 3. CodeMirror / contenteditable JS fallback
        await page.evaluate(
            """(html) => {
                const cmEl = document.querySelector('.CodeMirror');
                if (cmEl && cmEl.CodeMirror) {
                    cmEl.CodeMirror.setValue(html);
                    return;
                }
                const editable = document.querySelector('[contenteditable="true"]');
                if (editable) { editable.innerHTML = html; }
            }""",
            html_content,
        )
        logger.debug("본문 JS 직접 주입 완료")

    # ── 카테고리 ─────────────────────────────────────────────────────────────────

    async def _set_category(self, page: Page, category_id: int) -> None:
        try:
            open_selectors = [
                "button.btn_category",
                ".area_category button",
                "button:has-text('카테고리')",
            ]
            for sel in open_selectors:
                try:
                    btn = await page.wait_for_selector(sel, timeout=2_000)
                    if btn:
                        await btn.click()
                        await page.wait_for_timeout(400)
                        break
                except Exception:
                    continue

            item_selectors = [
                f"[data-id='{category_id}']",
                f"a[onclick*='{category_id}']",
                f"li[data-category-id='{category_id}'] a",
            ]
            for sel in item_selectors:
                try:
                    item = await page.wait_for_selector(sel, timeout=2_000)
                    if item:
                        await item.click()
                        logger.debug(f"카테고리 설정: ID={category_id}")
                        return
                except Exception:
                    continue

            logger.warning(f"카테고리 {category_id} 선택 실패 — 기본값 유지")
        except Exception as e:
            logger.warning(f"카테고리 설정 오류: {e}")

    # ── 태그 ─────────────────────────────────────────────────────────────────────

    async def _set_tags(self, page: Page, tags: list[str]) -> None:
        tag_selectors = [
            "#tagText",
            "input.tf_tag",
            "input[placeholder*='태그']",
            ".area_tag input",
        ]
        for sel in tag_selectors:
            try:
                inp = await page.wait_for_selector(sel, timeout=2_000)
                if inp:
                    for tag in tags[:10]:
                        await inp.fill(tag)
                        await page.keyboard.press("Enter")
                        await page.wait_for_timeout(150)
                    logger.debug(f"태그 입력 완료: {tags[:10]}")
                    return
            except Exception:
                continue
        logger.warning("태그 입력 필드를 찾지 못했습니다.")

    # ── 발행 ─────────────────────────────────────────────────────────────────────

    async def _publish(self, page: Page, visibility: int) -> dict:
        """발행 버튼 클릭 → 공개 설정 팝업 처리 → 발행 후 URL 추출"""

        # 1. 발행 버튼
        for sel in ["button.btn_publish", "button:has-text('발행')", ".area_footer button.btn_submit"]:
            try:
                btn = await page.wait_for_selector(sel, timeout=5_000)
                if btn:
                    await btn.click()
                    await page.wait_for_timeout(1_000)
                    break
            except Exception:
                continue

        # 2. 공개/비공개 라디오 (팝업)
        radio_sel = "input[value='0']" if visibility == 0 else "input[value='3']"
        try:
            radio = await page.wait_for_selector(radio_sel, timeout=2_000)
            if radio:
                await radio.click()
        except Exception:
            pass

        # 3. 최종 확인 버튼
        for sel in ["button.btn_post", ".layer_publish button:has-text('발행')", "button:has-text('확인')"]:
            try:
                btn = await page.wait_for_selector(sel, timeout=3_000)
                if btn:
                    await btn.click()
                    break
            except Exception:
                continue

        # 4. 페이지 이동 대기
        try:
            await page.wait_for_url(
                lambda url: "/manage/newpost/" not in url,
                timeout=20_000,
            )
        except Exception:
            pass

        post_url = page.url
        match = re.search(r"/(\d+)$", post_url)
        post_id = match.group(1) if match else ""

        logger.info(f"발행 완료: {post_url} (postId={post_id})")
        return {"post_id": post_id, "url": post_url}

    # ── 카테고리 목록 조회 ────────────────────────────────────────────────────────

    async def _get_categories(self, page: Page) -> list[dict]:
        await page.goto(CATEGORY_URL, wait_until="networkidle", timeout=30_000)
        return await page.evaluate(
            """() => {
                const items = document.querySelectorAll(
                    '.list_category li[data-id], .category_item[data-id]'
                );
                return Array.from(items).map(el => ({
                    id: el.dataset.id || '',
                    name: (el.querySelector('a') || el).textContent.trim(),
                })).filter(c => c.id);
            }"""
        )

    # ── 이미지 base64 변환 헬퍼 ──────────────────────────────────────────────────

    @staticmethod
    def image_to_data_uri(file_path: str) -> str:
        """로컬 이미지 파일을 HTML에 인라인으로 삽입 가능한 Data URI로 변환합니다."""
        path = Path(file_path)
        mime_map = {
            "jpg": "image/jpeg", "jpeg": "image/jpeg",
            "png": "image/png", "gif": "image/gif", "webp": "image/webp",
        }
        mime = mime_map.get(path.suffix.lower().lstrip("."), "image/png")
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        return f"data:{mime};base64,{b64}"


# ─── 싱글턴 인스턴스 ──────────────────────────────────────────────────────────────

tistory_client = TistoryPlaywrightClient()
