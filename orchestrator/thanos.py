from __future__ import annotations

"""
████████╗██╗  ██╗ █████╗ ███╗   ██╗ ██████╗ ███████╗
╚══██╔══╝██║  ██║██╔══██╗████╗  ██║██╔═══██╗██╔════╝
   ██║   ███████║███████║██╔██╗ ██║██║   ██║███████╗
   ██║   ██╔══██║██╔══██║██║╚██╗██║██║   ██║╚════██║
   ██║   ██║  ██║██║  ██║██║ ╚████║╚██████╔╝███████║
   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝ ╚═════╝ ╚══════╝

Main Orchestrator — "I am inevitable."

Thanos wields the six Infinity Stones (agents) to bring balance
to the techblog pipeline:

  ◆ Power Stone   → TopicDiscoveryAgent
  ◆ Mind Stone    → ContentGenerationAgent
  ◆ Reality Stone → SEOOptimizationAgent
  ◆ Soul Stone    → QualityReviewAgent
  ◆ Space Stone   → PublishingAgent
  ◆ Time Stone    → AnalyticsAgent

  Supporting Stones:
  ◈ CodeExampleAgent   (between Mind & Reality)
  ◈ ImageGenerationAgent (parallel with Code, between Mind & Reality)
"""

import asyncio
from datetime import datetime
from typing import Optional

from celery import Celery
from celery.schedules import crontab

from agents import (
    TopicDiscoveryAgent,
    ContentGenerationAgent,
    CodeExampleAgent,
    ImageGenerationAgent,
    SEOOptimizationAgent,
    QualityReviewAgent,
    QualityCheckError,
    PublishingAgent,
    AnalyticsAgent,
)
from core.models import PostDraft, PipelineRun, PipelineStatus, TopicData
from core.config import settings
from core.database import init_db, AsyncSessionFactory, PostRecord, HumanReviewRecord
from utils.logger import get_logger

logger = get_logger("thanos")

# ─── Celery App ───────────────────────────────────────────────────────────────

celery_app = Celery(
    "thanos",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Seoul",
    enable_utc=True,
    beat_schedule={
        # ◆ Power Stone fires every morning — discover today's topics
        "daily-topic-discovery": {
            "task": "orchestrator.thanos.task_daily_pipeline",
            "schedule": crontab(hour=6, minute=0),
        },
        # ◆ Time Stone fires weekly — collect performance data
        "weekly-analytics": {
            "task": "orchestrator.thanos.task_weekly_analytics",
            "schedule": crontab(hour=10, minute=0, day_of_week="monday"),
        },
    },
)


# ─── Thanos Class ─────────────────────────────────────────────────────────────


class Thanos:
    """
    The Infinity Gauntlet Orchestrator.

    Manages the full pipeline from topic discovery to analytics.
    Supports both fully-automated and human-in-the-loop modes.
    """

    # Infinity Stone → Agent mapping (for logging/metrics)
    INFINITY_STONES = {
        "power":   "topic_discovery",
        "mind":    "content_generation",
        "reality": "seo_optimization",
        "soul":    "quality_review",
        "space":   "publishing",
        "time":    "analytics",
    }

    def __init__(self) -> None:
        # Collect the stones
        self.topic_agent = TopicDiscoveryAgent()
        self.content_agent = ContentGenerationAgent()
        self.code_agent = CodeExampleAgent()
        self.image_agent = ImageGenerationAgent()
        self.seo_agent = SEOOptimizationAgent()
        self.quality_agent = QualityReviewAgent()
        self.publishing_agent = PublishingAgent()
        self.analytics_agent = AnalyticsAgent()

        self.human_review_queue: list[PostDraft] = []

    # ─── The Snap ─────────────────────────────────────────────────────────────

    async def snap(
        self,
        topics: Optional[list[TopicData]] = None,
        posts_count: Optional[int] = None,
    ) -> PipelineRun:
        """
        Execute the full pipeline — The Snap.

        If topics is None, the Power Stone discovers them automatically.
        posts_count controls how many posts to produce in one run.
        """
        run = PipelineRun(
            status=PipelineStatus.TOPIC_DISCOVERY,
            started_at=datetime.utcnow(),
        )
        logger.info("snap_begin", run_id=run.run_id)

        try:
            # ◆ POWER STONE — Discover topics
            if topics is None:
                count = posts_count or settings.posts_per_day
                logger.info("wielding_power_stone", count=count)
                topics = await self.topic_agent.discover_batch(count)

            if not topics:
                raise RuntimeError("Power Stone returned no topics.")

            logger.info(f"Topics discovered: {[t.title for t in topics]}")

            # Process each topic independently (but limited concurrency to avoid API rate limits)
            semaphore = asyncio.Semaphore(2)   # max 2 posts in parallel
            tasks = [self._process_post(topic, run, semaphore) for topic in topics]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Post pipeline error: {result}")
                    run.error_log.append(str(result))
                    run.total_posts_failed += 1
                elif isinstance(result, PostDraft):
                    run.posts.append(result)

        except Exception as exc:
            logger.error(f"Snap failed: {exc}")
            run.status = PipelineStatus.FAILED
            run.error_log.append(str(exc))
        finally:
            run.completed_at = datetime.utcnow()
            if run.status != PipelineStatus.FAILED:
                run.status = PipelineStatus.COMPLETED

        logger.info(
            "snap_complete",
            published=run.total_posts_published,
            failed=run.total_posts_failed,
            human_review=run.total_posts_human_review,
        )
        return run

    # ─── Single Post Pipeline ─────────────────────────────────────────────────

    async def _process_post(
        self,
        topic: TopicData,
        run: PipelineRun,
        semaphore: asyncio.Semaphore,
    ) -> PostDraft:
        async with semaphore:
            draft = PostDraft(topic=topic)
            logger.info(f"Processing topic: {topic.title}", post_id=draft.post_id)

            try:
                # ◆ MIND STONE — Generate content
                draft.pipeline_status = PipelineStatus.CONTENT_GENERATION
                draft = await self.content_agent.run(draft)

                # ◈ Code + Image generation in parallel
                draft = await self._parallel_enhancement(draft)

                # ◆ REALITY STONE — SEO optimization
                draft.pipeline_status = PipelineStatus.SEO_OPTIMIZATION
                draft = await self.seo_agent.run(draft)

                # ◆ SOUL STONE — Quality gate (hardest trial)
                draft = await self._wield_soul_stone(draft, run)

                if draft.pipeline_status == PipelineStatus.HUMAN_REVIEW:
                    return draft   # Handed off to human review

                # ◆ SPACE STONE — Publish to Tistory
                draft.pipeline_status = PipelineStatus.PUBLISHING
                draft = await self.publishing_agent.run(draft)

                run.total_posts_published += 1
                await self._persist_post(draft)

                # ◆ TIME STONE — Schedule delayed analytics collection
                logger.info(
                    f"Post published successfully: {draft.published_url}",
                    post_id=draft.post_id,
                )

            except Exception as exc:
                draft.pipeline_status = PipelineStatus.FAILED
                logger.error(f"Post failed: {exc}", post_id=draft.post_id)
                raise

            return draft

    async def _parallel_enhancement(self, draft: PostDraft) -> PostDraft:
        """
        Run code validation and image generation in parallel.
        Both are independent of each other after content generation.
        """
        draft.pipeline_status = PipelineStatus.CODE_REVIEW

        code_task = self._safe_run(self.code_agent, draft, "code_example")
        image_task = self._safe_run(self.image_agent, draft, "image_generation")

        code_draft, image_draft = await asyncio.gather(code_task, image_task)

        # Merge code block updates
        if code_draft:
            draft.code_blocks = code_draft.code_blocks
            draft.content_markdown = code_draft.content_markdown
            draft.agent_results.extend(
                [r for r in code_draft.agent_results if r.agent_name == "code_example"]
            )

        # Merge image updates
        if image_draft:
            draft.images = image_draft.images
            draft.agent_results.extend(
                [r for r in image_draft.agent_results if r.agent_name == "image_generation"]
            )

        return draft

    async def _safe_run(
        self,
        agent,
        draft: PostDraft,
        agent_name: str,
    ) -> Optional[PostDraft]:
        """Run an agent, returning None (not raising) on failure."""
        try:
            # Deep-copy the draft for isolated parallel processing
            import copy
            draft_copy = copy.deepcopy(draft)
            return await agent.run(draft_copy)
        except Exception as exc:
            logger.warning(f"Agent {agent_name} failed (non-fatal): {exc}")
            return None

    async def _wield_soul_stone(self, draft: PostDraft, run: PipelineRun) -> PostDraft:
        """
        ◆ SOUL STONE — Quality gate.

        Retries failed quality checks by re-running the responsible agent,
        up to human_review_max_retries times.
        After exhausting retries, the post is sent to the Human Review Queue.
        """
        draft.pipeline_status = PipelineStatus.QUALITY_CHECK
        max_attempts = settings.human_review_max_retries

        for attempt in range(1, max_attempts + 1):
            try:
                draft = await self.quality_agent.run(draft)
                return draft   # Passed!
            except QualityCheckError as qce:
                logger.warning(
                    f"Quality check failed (attempt {attempt}/{max_attempts}): {qce.issues}",
                    post_id=draft.post_id,
                )
                if attempt < max_attempts:
                    draft = await self._remediate(draft, qce.issues)
                else:
                    logger.error(
                        f"Quality check exhausted retries — sending to Human Review",
                        post_id=draft.post_id,
                    )
                    await self._queue_for_human_review(draft, qce.issues, run)
                    return draft

        return draft

    async def _remediate(self, draft: PostDraft, issues: list[str]) -> PostDraft:
        """Re-run specific agents based on which quality checks failed."""
        for issue in issues:
            if "글자 수 부족" in issue:
                logger.info("Remediating: regenerating content", post_id=draft.post_id)
                draft = await self._safe_run(self.content_agent, draft, "content_generation") or draft

            if "코드 블록" in issue:
                logger.info("Remediating: re-validating code", post_id=draft.post_id)
                draft = await self._safe_run(self.code_agent, draft, "code_example") or draft

            if "이미지 없음" in issue:
                logger.info("Remediating: regenerating images", post_id=draft.post_id)
                draft = await self._safe_run(self.image_agent, draft, "image_generation") or draft

            if "SEO" in issue or "가독성" in issue:
                logger.info("Remediating: re-running SEO optimization", post_id=draft.post_id)
                draft = await self._safe_run(self.seo_agent, draft, "seo_optimization") or draft

        return draft

    async def _queue_for_human_review(
        self,
        draft: PostDraft,
        issues: list[str],
        run: PipelineRun,
    ) -> None:
        draft.pipeline_status = PipelineStatus.HUMAN_REVIEW
        self.human_review_queue.append(draft)
        run.total_posts_human_review += 1

        async with AsyncSessionFactory() as session:
            record = HumanReviewRecord(
                post_id=draft.post_id,
                topic_title=draft.topic.title if draft.topic else "",
                issues="; ".join(issues),
                draft_json=draft.model_dump(mode="json"),
            )
            session.add(record)
            await session.commit()

        logger.info(
            f"Queued for human review: {draft.post_id}",
            issues=issues,
        )

    async def _persist_post(self, draft: PostDraft) -> None:
        """Persist published post metadata to the database."""
        try:
            async with AsyncSessionFactory() as session:
                record = PostRecord(
                    post_id=draft.post_id,
                    topic_title=draft.topic.title if draft.topic else "",
                    title=draft.title,
                    pipeline_status=draft.pipeline_status.value,
                    tistory_post_id=draft.tistory_post_id,
                    published_url=draft.published_url,
                    retry_counts=draft.retry_counts,
                    content_markdown=draft.content_markdown,
                    seo_tags=",".join(draft.seo.tags),
                    seo_score=draft.seo.readability_score,
                    quality_score=draft.quality_report.score if draft.quality_report else 0.0,
                    quality_passed=draft.quality_report.overall_pass if draft.quality_report else False,
                )
                session.add(record)
                await session.commit()
        except Exception as exc:
            logger.error(f"DB persist failed: {exc}", post_id=draft.post_id)

    # ─── Analytics Collection ─────────────────────────────────────────────────

    async def collect_analytics(self) -> None:
        """
        ◆ TIME STONE — Collect analytics for all published posts.
        Called on the weekly schedule.
        """
        from sqlalchemy import select
        async with AsyncSessionFactory() as session:
            result = await session.execute(
                __import__("sqlalchemy", fromlist=["select"]).select(PostRecord).where(
                    PostRecord.tistory_post_id != ""
                )
            )
            records = result.scalars().all()

        drafts = [
            PostDraft(
                post_id=r.post_id,
                tistory_post_id=r.tistory_post_id,
                title=r.title,
            )
            for r in records
        ]

        snapshots = await self.analytics_agent.collect_batch(drafts)
        report = self.analytics_agent.generate_weekly_report(snapshots)
        logger.info(f"\n{report}")

        await self._send_slack_report(report)

    async def _send_slack_report(self, text: str) -> None:
        if not settings.slack_webhook_url:
            return
        import httpx
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(
                    settings.slack_webhook_url,
                    json={"text": f"```{text}```"},
                )
        except Exception as exc:
            logger.warning(f"Slack notification failed: {exc}")


# ─── Singleton ────────────────────────────────────────────────────────────────

thanos = Thanos()


# ─── Celery Tasks ─────────────────────────────────────────────────────────────


@celery_app.task(name="orchestrator.thanos.task_daily_pipeline", bind=True, max_retries=1)
def task_daily_pipeline(self) -> dict:
    """
    Daily Celery task — runs the full content pipeline.
    Triggered by Celery Beat at 06:00 KST.
    """
    import asyncio

    async def _run():
        await init_db()
        run = await thanos.snap()
        return {
            "run_id": run.run_id,
            "published": run.total_posts_published,
            "failed": run.total_posts_failed,
            "human_review": run.total_posts_human_review,
        }

    loop = asyncio.get_event_loop()
    return loop.run_until_complete(_run())


@celery_app.task(name="orchestrator.thanos.task_weekly_analytics", bind=True, max_retries=1)
def task_weekly_analytics(self) -> str:
    """
    Weekly Celery task — collects analytics for all published posts.
    Triggered by Celery Beat every Monday at 10:00 KST.
    """
    import asyncio

    async def _run():
        await init_db()
        await thanos.collect_analytics()
        return "Analytics collection completed."

    loop = asyncio.get_event_loop()
    return loop.run_until_complete(_run())
