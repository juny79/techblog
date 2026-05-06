from __future__ import annotations

import re
from typing import Optional

from agents.base_agent import BaseAgent
from core.models import PostDraft, CodeBlock
from utils.llm_client import llm_client

SYSTEM_PROMPT = """당신은 한국어 기술 블로그 전문 작가입니다.
주어진 주제에 대해 실무 개발자를 대상으로 정확하고 유익한 기술 포스트를 작성합니다.

작성 규칙:
- 마크다운 형식으로 출력합니다.
- 서론, 본론(2~4개 섹션), 결론 구조를 지킵니다.
- 각 섹션에는 ## 소제목을 사용합니다.
- 코드 예제는 반드시 ```언어명 으로 시작하는 코드 블록으로 감쌉니다.
- 결론에는 핵심 내용을 3줄 이내로 요약합니다.
- 광고성 문구나 과도한 미사여구를 사용하지 않습니다.
"""

USER_PROMPT_TEMPLATE = """다음 조건으로 기술 블로그 포스트를 작성해 주세요.

주제: {title}
요약: {summary}
핵심 키워드: {keywords}
카테고리: {category}
목표 독자: {audience_level}
목표 분량: {target_word_count}자 이상

포스트 제목도 마크다운 # 제목 형식으로 맨 위에 포함해 주세요.
"""


class ContentGenerationAgent(BaseAgent):
    """
    Mind Stone — generates the full Korean blog post via LLM.

    Output stored in:
    - draft.title
    - draft.content_markdown
    - draft.code_blocks (extracted from markdown)
    """

    def __init__(self) -> None:
        super().__init__(name="content_generation", max_retries=3)

    async def execute(self, draft: PostDraft) -> PostDraft:
        if not draft.topic:
            raise ValueError("PostDraft has no topic set before ContentGenerationAgent.")

        topic = draft.topic
        user_prompt = USER_PROMPT_TEMPLATE.format(
            title=topic.title,
            summary=topic.summary or topic.title,
            keywords=", ".join(topic.keywords),
            category=topic.category,
            audience_level="중급 개발자",
            target_word_count=2000,
        )

        self.logger.info(f"Generating content for: {topic.title}")
        raw_content = await llm_client.complete(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_tokens=4096,
            temperature=0.7,
        )

        title, body = self._split_title_and_body(raw_content)
        code_blocks = self._extract_code_blocks(body)

        draft.title = title or topic.title
        draft.content_markdown = body
        draft.code_blocks = code_blocks

        self.logger.info(
            f"Content generated: {len(body)} chars, {len(code_blocks)} code blocks"
        )
        return draft

    # ─── Helpers ───────────────────────────────────────────────────────────────

    def _split_title_and_body(self, raw: str) -> tuple[str, str]:
        lines = raw.strip().splitlines()
        title = ""
        body_start = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("# "):
                title = stripped.lstrip("# ").strip()
                body_start = i + 1
                break
        body = "\n".join(lines[body_start:]).strip()
        return title, body

    def _extract_code_blocks(self, markdown: str) -> list[CodeBlock]:
        """Extract all fenced code blocks from markdown content."""
        pattern = re.compile(r"```(\w+)?\n(.*?)```", re.DOTALL)
        blocks: list[CodeBlock] = []
        for idx, match in enumerate(pattern.finditer(markdown)):
            lang = match.group(1) or "text"
            code = match.group(2).strip()
            blocks.append(CodeBlock(index=idx, language=lang, code=code))
        return blocks
