from __future__ import annotations

import re
from typing import Optional

import markdown2

from agents.base_agent import BaseAgent
from core.models import PostDraft, PipelineStatus
from core.config import settings
from utils.tistory_client import tistory_client


class PublishingAgent(BaseAgent):
    """
    Space Stone — deploys the polished post to Tistory.

    Steps:
    1. Convert Markdown → HTML.
    2. Embed local images as base64 Data URI (Open API 종료 대응).
    3. Inject thumbnail at the top of the HTML body.
    4. Call TistoryPlaywrightClient.write_post().
    5. Store post_id and published_url on the draft.
    """

    def __init__(self) -> None:
        super().__init__(name="publishing", max_retries=3)

    async def execute(self, draft: PostDraft) -> PostDraft:
        if not draft.content_markdown:
            raise ValueError("No content to publish.")

        # Step 1: Convert markdown to HTML
        html_body = self._markdown_to_html(draft.content_markdown)

        # Step 2: Embed local images as base64 Data URI
        html_body = self._embed_images(html_body, draft)

        # Step 3: Inject thumbnail at the top
        thumbnail = draft.thumbnail()
        if thumbnail and thumbnail.local_path:
            try:
                data_uri = tistory_client.image_to_data_uri(thumbnail.local_path)
                img_tag = (
                    f'<figure><img src="{data_uri}" '
                    f'alt="{thumbnail.alt_text}" style="max-width:100%;"/></figure>\n\n'
                )
                html_body = img_tag + html_body
            except Exception as exc:
                self.logger.warning(f"썸네일 base64 변환 실패: {exc}")

        draft.content_html = html_body

        # Step 4: Playwright로 티스토리 발행
        category_id = draft.seo.tistory_category_id or settings.tistory_default_category_id
        tags = draft.seo.tags[:10]

        result = await tistory_client.write_post(
            title=draft.seo.seo_title or draft.title,
            content=html_body,
            category_id=category_id,
            tags=tags,
            visibility=settings.tistory_visibility,
        )

        post_id = str(result.get("post_id", ""))
        post_url = result.get("url", "")

        if not post_id:
            raise RuntimeError(f"발행 후 postId를 확인할 수 없습니다. Response: {result}")

        draft.tistory_post_id = post_id
        draft.published_url = post_url
        draft.pipeline_status = PipelineStatus.COMPLETED

        self.logger.info(f"Published: {post_url} (postId={post_id})")
        return draft

    # ─── Helpers ───────────────────────────────────────────────────────────────

    def _embed_images(self, html: str, draft: PostDraft) -> str:
        """
        마크다운→HTML 변환 후 남아 있는 로컬 이미지 경로를
        base64 Data URI로 교체합니다.
        """
        for asset in draft.images:
            if asset.local_path:
                try:
                    data_uri = tistory_client.image_to_data_uri(asset.local_path)
                    html = html.replace(asset.local_path, data_uri)
                except Exception as exc:
                    self.logger.warning(f"이미지 base64 변환 실패 ({asset.local_path}): {exc}")
        return html

    def _markdown_to_html(self, markdown_text: str) -> str:
        """Convert markdown to HTML with syntax highlighting extras."""
        html = markdown2.markdown(
            markdown_text,
            extras=[
                "fenced-code-blocks",
                "tables",
                "strike",
                "task_list",
                "header-ids",
                "code-friendly",
            ],
        )
        return html
