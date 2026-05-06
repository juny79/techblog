from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

import httpx

from agents.base_agent import BaseAgent
from core.models import PostDraft, AnalyticsSnapshot
from core.config import settings
from utils.logger import get_logger

logger = get_logger("analytics_agent")


class AnalyticsAgent(BaseAgent):
    """
    Time Stone — collects performance data for published posts
    and feeds insights back to the pipeline for future improvements.

    Currently fetches:
    - Tistory post stats (views, comments, likes) via Tistory API
    - (Optional) Google Analytics 4 — requires GA4 credentials

    Results are stored as AnalyticsSnapshot objects and logged.
    """

    def __init__(self) -> None:
        super().__init__(name="analytics", max_retries=2)

    async def execute(self, draft: PostDraft) -> PostDraft:
        """
        Collect analytics for a single published post.
        Called by Thanos after a configurable delay (e.g. 24h post-publish).
        """
        if not draft.tistory_post_id:
            self.logger.warning("No tistory_post_id, skipping analytics.")
            return draft

        snapshot = await self._fetch_tistory_stats(draft)
        self._log_snapshot(snapshot)

        # Attach to draft for downstream use / DB persistence
        draft.agent_results.append(
            __import__("core.models", fromlist=["AgentResult"]).AgentResult(
                agent_name=self.name,
                status=__import__("core.models", fromlist=["AgentStatus"]).AgentStatus.SUCCESS,
                data=snapshot.model_dump(mode="json"),
            )
        )
        return draft

    async def collect_batch(self, drafts: list[PostDraft]) -> list[AnalyticsSnapshot]:
        """
        Collect analytics snapshots for a list of published posts.
        Called by Thanos on the weekly analytics schedule.
        """
        snapshots: list[AnalyticsSnapshot] = []
        for draft in drafts:
            if draft.tistory_post_id:
                try:
                    snap = await self._fetch_tistory_stats(draft)
                    snapshots.append(snap)
                    self._log_snapshot(snap)
                except Exception as exc:
                    self.logger.warning(f"Analytics fetch failed for {draft.post_id}: {exc}")
        return snapshots

    def generate_weekly_report(self, snapshots: list[AnalyticsSnapshot]) -> str:
        """Generate a plain-text weekly performance report."""
        if not snapshots:
            return "이번 주 수집된 통계 데이터가 없습니다."

        total_views = sum(s.views for s in snapshots)
        total_comments = sum(s.comments for s in snapshots)
        total_likes = sum(s.likes for s in snapshots)
        best = max(snapshots, key=lambda s: s.views)

        lines = [
            "=" * 50,
            f"📊 주간 기술블로그 성과 리포트 ({datetime.utcnow().strftime('%Y-%m-%d')})",
            "=" * 50,
            f"총 포스트 수     : {len(snapshots)}",
            f"총 조회수        : {total_views:,}",
            f"총 좋아요        : {total_likes:,}",
            f"총 댓글          : {total_comments:,}",
            f"평균 조회수      : {total_views // len(snapshots):,}",
            f"최고 성과 포스트 : {best.tistory_post_id} ({best.views:,} views)",
            "=" * 50,
        ]
        return "\n".join(lines)

    # ─── Data Fetching ─────────────────────────────────────────────────────────

    async def _fetch_tistory_stats(self, draft: PostDraft) -> AnalyticsSnapshot:
        """
        Fetch post statistics from Tistory.
        Note: Tistory's public API has limited analytics endpoints.
        Views/likes are approximated from the post list endpoint.
        """
        from utils.tistory_client import tistory_client

        posts = await tistory_client.get_post_list(page=1)
        views = 0
        likes = 0
        comments_count = 0

        for post in posts:
            if str(post.get("id", "")) == str(draft.tistory_post_id):
                views = int(post.get("count", 0))
                likes = int(post.get("likes", 0))
                comments_count = int(post.get("comments", 0))
                break

        return AnalyticsSnapshot(
            post_id=draft.post_id,
            tistory_post_id=draft.tistory_post_id,
            views=views,
            likes=likes,
            comments=comments_count,
            collected_at=datetime.utcnow(),
        )

    def _log_snapshot(self, snap: AnalyticsSnapshot) -> None:
        self.logger.info(
            "analytics_snapshot",
            post_id=snap.post_id,
            views=snap.views,
            likes=snap.likes,
            comments=snap.comments,
        )
