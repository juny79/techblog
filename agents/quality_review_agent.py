from __future__ import annotations

import re
from typing import Optional

from agents.base_agent import BaseAgent
from core.models import PostDraft, QualityReport
from core.config import settings

MIN_WORD_COUNT = 1500
MIN_SEO_SCORE = 70.0
MAX_PLAGIARISM_RATIO = 0.2
MIN_IMAGE_COUNT = 1
MIN_READABILITY_SCORE = 60.0


class QualityReviewAgent(BaseAgent):
    """
    Soul Stone — the hardest stone to wield.

    Runs a multi-criteria quality gate before publishing.
    Failures are recorded in QualityReport.issues for Thanos to act upon.

    Checks:
    1. Word count (>= MIN_WORD_COUNT)
    2. All code blocks valid
    3. Plagiarism ratio (local similarity heuristic)
    4. SEO score (>= MIN_SEO_SCORE)
    5. Image presence (>= MIN_IMAGE_COUNT)
    6. Basic spelling / structure sanity
    """

    def __init__(self) -> None:
        super().__init__(name="quality_review", max_retries=1)

    async def execute(self, draft: PostDraft) -> PostDraft:
        report = QualityReport()
        issues: list[str] = []

        # 1. Word count
        word_count = len(draft.content_markdown.split())
        report.word_count = word_count
        report.word_count_pass = word_count >= MIN_WORD_COUNT
        if not report.word_count_pass:
            issues.append(f"글자 수 부족: {word_count} 단어 (최소 {MIN_WORD_COUNT})")

        # 2. Code block validity
        invalid_blocks = [b for b in draft.code_blocks if b.is_tested and not b.is_valid]
        report.code_valid_pass = len(invalid_blocks) == 0
        if not report.code_valid_pass:
            issues.append(f"유효하지 않은 코드 블록 {len(invalid_blocks)}개 존재")

        # 3. Plagiarism (heuristic: repetition ratio within document)
        plagiarism_ratio = self._estimate_repetition(draft.content_markdown)
        report.plagiarism_ratio = plagiarism_ratio
        report.plagiarism_pass = plagiarism_ratio <= MAX_PLAGIARISM_RATIO
        if not report.plagiarism_pass:
            issues.append(f"반복 콘텐츠 비율 높음: {plagiarism_ratio:.0%}")

        # 4. SEO score (via readability as proxy)
        seo_score = draft.seo.readability_score
        report.seo_score = seo_score
        report.seo_score_pass = seo_score >= MIN_SEO_SCORE
        if not report.seo_score_pass:
            issues.append(f"SEO/가독성 점수 부족: {seo_score:.1f} (최소 {MIN_SEO_SCORE})")

        # 5. Image presence
        image_count = len(draft.images)
        report.image_count = image_count
        report.image_pass = image_count >= MIN_IMAGE_COUNT
        if not report.image_pass:
            issues.append(f"이미지 없음 (최소 {MIN_IMAGE_COUNT}장 필요)")

        # 6. Basic structure check (has H2 sections)
        has_sections = bool(re.search(r"^##\s+", draft.content_markdown, re.MULTILINE))
        report.spelling_pass = has_sections
        if not has_sections:
            issues.append("본문에 ## 소제목 섹션이 없음")

        # ─── Overall pass ──────────────────────────────────────────────────────
        report.issues = issues
        passed_count = sum([
            report.word_count_pass,
            report.code_valid_pass,
            report.plagiarism_pass,
            report.seo_score_pass,
            report.image_pass,
            report.spelling_pass,
        ])
        report.score = round(passed_count / 6 * 100, 1)
        report.overall_pass = len(issues) == 0

        draft.quality_report = report

        if report.overall_pass:
            self.logger.info(f"Quality check PASSED (score={report.score})")
        else:
            self.logger.warning(
                f"Quality check FAILED (score={report.score}): {issues}"
            )
            raise QualityCheckError(issues)

        return draft

    # ─── Helpers ───────────────────────────────────────────────────────────────

    def _estimate_repetition(self, text: str) -> float:
        """
        Estimate repetition by finding duplicate sentences.
        Returns ratio of duplicate sentences to total.
        """
        sentences = [s.strip() for s in re.split(r"[.!?。\n]+", text) if len(s.strip()) > 20]
        if len(sentences) < 2:
            return 0.0
        seen: set[str] = set()
        duplicates = 0
        for sentence in sentences:
            normalized = re.sub(r"\s+", " ", sentence.lower())
            if normalized in seen:
                duplicates += 1
            seen.add(normalized)
        return round(duplicates / len(sentences), 3)


class QualityCheckError(Exception):
    """Raised by QualityReviewAgent when a post fails quality criteria."""

    def __init__(self, issues: list[str]) -> None:
        self.issues = issues
        super().__init__(f"Quality check failed: {'; '.join(issues)}")
