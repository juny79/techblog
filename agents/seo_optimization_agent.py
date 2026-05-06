from __future__ import annotations

import json
import re
from typing import Optional

from agents.base_agent import BaseAgent
from core.models import PostDraft, SEOMetadata
from core.config import settings
from utils.llm_client import llm_client

SEO_SYSTEM_PROMPT = """당신은 한국어 기술 블로그 SEO 전문가입니다.
블로그 포스트 본문을 분석하여 검색 최적화 메타데이터를 JSON 형식으로 출력합니다.

반드시 아래 JSON 형식만 반환하세요:
{
  "seo_title": "클릭율이 높은 최적화된 제목 (60자 이내)",
  "meta_description": "검색 결과 표시용 설명문 (155자 이내)",
  "tags": ["태그1", "태그2", "태그3", "태그4", "태그5"],
  "primary_keyword": "핵심 검색 키워드"
}
"""


class SEOOptimizationAgent(BaseAgent):
    """
    Reality Stone — enriches the draft with SEO metadata.

    1. Generates seo_title, meta_description, and tags via LLM.
    2. Calculates keyword density for primary keyword.
    3. Computes a basic readability score (average sentence length proxy).
    4. Assigns the Tistory category ID.
    """

    CATEGORY_MAP: dict[str, int] = {
        "백엔드": 1,
        "프론트엔드": 2,
        "데브옵스": 3,
        "AI/ML": 4,
        "모바일": 5,
        "보안": 6,
        "개발 일반": 7,
    }

    def __init__(self) -> None:
        super().__init__(name="seo_optimization", max_retries=2)

    async def execute(self, draft: PostDraft) -> PostDraft:
        if not draft.content_markdown:
            raise ValueError("No content to optimize.")

        # Truncate long content for LLM prompt
        snippet = draft.content_markdown[:3000]
        user_prompt = (
            f"포스트 제목: {draft.title}\n\n"
            f"핵심 키워드: {', '.join(draft.topic.keywords if draft.topic else [])}\n\n"
            f"본문 (앞부분):\n{snippet}"
        )

        raw = await llm_client.complete(
            system_prompt=SEO_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_tokens=512,
            temperature=0.3,
        )

        seo_data = self._parse_json(raw)

        primary_keyword = seo_data.get("primary_keyword", draft.title)
        tags = seo_data.get("tags", [])[:10]
        category = draft.topic.category if draft.topic else "개발 일반"

        draft.seo = SEOMetadata(
            seo_title=seo_data.get("seo_title", draft.title)[:60],
            meta_description=seo_data.get("meta_description", "")[:155],
            tags=tags,
            category=category,
            tistory_category_id=self.CATEGORY_MAP.get(category, settings.tistory_default_category_id),
            readability_score=self._readability_score(draft.content_markdown),
            keyword_density=self._keyword_density(draft.content_markdown, primary_keyword),
        )

        self.logger.info(
            f"SEO metadata: title={draft.seo.seo_title!r}, "
            f"tags={tags}, readability={draft.seo.readability_score:.1f}"
        )
        return draft

    # ─── Helpers ───────────────────────────────────────────────────────────────

    def _parse_json(self, raw: str) -> dict:
        """Extract and parse JSON from LLM output (may contain extra text)."""
        try:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
        return {}

    def _readability_score(self, text: str) -> float:
        """
        Simple Korean readability proxy:
        Lower average sentence length → higher score (max 100).
        """
        sentences = re.split(r"[.!?。]+", text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 5]
        if not sentences:
            return 50.0
        avg_len = sum(len(s) for s in sentences) / len(sentences)
        # Ideal avg sentence length ~40 chars. Score 100 at 40, degrades linearly.
        score = max(0.0, 100.0 - max(0.0, avg_len - 40.0) * 1.5)
        return round(score, 1)

    def _keyword_density(self, text: str, keyword: str) -> dict[str, float]:
        if not keyword:
            return {}
        total_words = len(text.split())
        count = len(re.findall(re.escape(keyword), text, re.IGNORECASE))
        density = round((count / total_words * 100) if total_words > 0 else 0.0, 2)
        return {keyword: density}
