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
    1. Upload all images to Tistory and replace local paths with hosted URLs.
    2. Convert Markdown → HTML.
    3. Inject thumbnail image tag at the top of the HTML body.
    4. Call Tistory write API.
    5. Store tistory_post_id and published_url on the draft.
    """

    def __init__(self) -> None:
        super().__init__(name="publishing", max_retries=3)

    async def execute(self, draft: PostDraft) -> PostDraft:
        if not draft.content_markdown:
            raise ValueError("No content to publish.")

        # Step 1: Upload images and collect hosted URLs
        await self._upload_images(draft)

        # Step 2: Convert markdown to HTML
        html_body = self._markdown_to_html(draft.content_markdown)

        # Step 3: Inject thumbnail at the top
        thumbnail = draft.thumbnail()
        if thumbnail and thumbnail.tistory_url:
            img_tag = (
                f'<figure><img src="{thumbnail.tistory_url}" '
                f'alt="{thumbnail.alt_text}" style="max-width:100%;"/></figure>\n\n'
            )
            html_body = img_tag + html_body

        draft.content_html = html_body

        # Step 4: Publish to Tistory
        category_id = draft.seo.tistory_category_id or settings.tistory_default_category_id
        tags = draft.seo.tags[:10]

        result = await tistory_client.write_post(
            title=draft.seo.seo_title or draft.title,
            content=html_body,
            category_id=category_id,
            tags=tags,
            visibility=settings.tistory_visibility,
        )

        tistory_data = result.get("tistory", {})
        post_id = str(tistory_data.get("postId", ""))
        post_url = tistory_data.get("url", "")

        if not post_id:
            raise RuntimeError(f"Tistory did not return postId. Response: {result}")

        draft.tistory_post_id = post_id
        draft.published_url = post_url
        draft.pipeline_status = PipelineStatus.COMPLETED

        self.logger.info(f"Published: {post_url} (postId={post_id})")
        return draft

    # ─── Helpers ───────────────────────────────────────────────────────────────

    async def _upload_images(self, draft: PostDraft) -> None:
        """Upload local images to Tistory and update tistory_url on each asset."""
        for asset in draft.images:
            if asset.local_path and not asset.tistory_url:
                try:
                    url = await tistory_client.attach_file(asset.local_path)
                    asset.tistory_url = url
                    self.logger.info(f"Image uploaded: {asset.image_type} → {url}")
                except Exception as exc:
                    self.logger.warning(f"Image upload failed ({asset.image_type}): {exc}")

        # Replace local image references in markdown with Tistory URLs
        for asset in draft.images:
            if asset.local_path and asset.tistory_url:
                draft.content_markdown = draft.content_markdown.replace(
                    asset.local_path, asset.tistory_url
                )

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
