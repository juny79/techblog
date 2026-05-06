from __future__ import annotations

import asyncio
import os
import uuid
from io import BytesIO
from typing import Optional

import httpx
from PIL import Image, ImageDraw, ImageFont

from agents.base_agent import BaseAgent
from core.models import PostDraft, ImageAsset
from core.config import settings
from utils.llm_client import llm_client

THUMBNAIL_SIZE = (1200, 628)
CONTENT_IMAGE_SIZE = (800, 450)


class ImageGenerationAgent(BaseAgent):
    """
    Space Stone — generates thumbnail and in-body images via DALL-E 3.

    For each post:
    - 1 thumbnail (1200×628)
    - 1 content illustration (800×450)

    Images are saved locally under settings.image_storage_path.
    Tistory upload is handled later by PublishingAgent.
    """

    def __init__(self) -> None:
        super().__init__(name="image_generation", max_retries=3)
        os.makedirs(settings.image_storage_path, exist_ok=True)

    async def execute(self, draft: PostDraft) -> PostDraft:
        if not draft.topic:
            raise ValueError("No topic on draft for ImageGenerationAgent.")

        topic = draft.topic
        thumbnail_prompt = await self._build_prompt(topic.title, "thumbnail")
        content_prompt = await self._build_prompt(topic.title, "content")

        thumbnail, content_img = await asyncio.gather(
            self._generate_image(thumbnail_prompt, THUMBNAIL_SIZE, "thumbnail", draft.post_id),
            self._generate_image(content_prompt, CONTENT_IMAGE_SIZE, "content", draft.post_id),
            return_exceptions=True,
        )

        if isinstance(thumbnail, ImageAsset):
            draft.images.append(thumbnail)
            self.logger.info(f"Thumbnail saved: {thumbnail.local_path}")
        else:
            self.logger.warning(f"Thumbnail generation failed: {thumbnail}")

        if isinstance(content_img, ImageAsset):
            draft.images.append(content_img)
            self.logger.info(f"Content image saved: {content_img.local_path}")
        else:
            self.logger.warning(f"Content image generation failed: {content_img}")

        return draft

    # ─── Prompt Builder ────────────────────────────────────────────────────────

    async def _build_prompt(self, title: str, image_type: str) -> str:
        style = (
            "modern tech blog thumbnail, minimalist design, dark blue gradient background, "
            "subtle circuit board pattern, professional typography space"
        )
        if image_type == "content":
            style = (
                "clean tech illustration, light background, isometric style, "
                "professional software engineering concept art, no text"
            )
        return (
            f"A {style} representing the concept: '{title}'. "
            "High quality, 4K, suitable for a Korean tech blog."
        )

    # ─── Image Generation ──────────────────────────────────────────────────────

    async def _generate_image(
        self,
        prompt: str,
        size: tuple[int, int],
        image_type: str,
        post_id: str,
    ) -> ImageAsset:
        import openai
        client = openai.AsyncOpenAI(api_key=settings.openai_api_key)

        dalle_size = "1792x1024" if size[0] > size[1] else "1024x1024"
        response = await client.images.generate(
            model=settings.dalle_model,
            prompt=prompt,
            n=1,
            size=dalle_size,
            quality="standard",
        )
        image_url = response.data[0].url

        # Download and resize
        async with httpx.AsyncClient(timeout=60) as http:
            img_response = await http.get(image_url)
        img = Image.open(BytesIO(img_response.content)).convert("RGB")
        img = img.resize(size, Image.LANCZOS)

        # Save locally
        filename = f"{post_id}_{image_type}_{uuid.uuid4().hex[:8]}.png"
        local_path = os.path.join(settings.image_storage_path, filename)
        img.save(local_path, "PNG", optimize=True)

        return ImageAsset(
            image_type=image_type,
            local_path=local_path,
            alt_text=f"{image_type} image for: {prompt[:80]}",
            width=size[0],
            height=size[1],
            prompt_used=prompt,
        )
