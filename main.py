"""
Techblog Automation — Entry Point

Usage:
  # Run the full pipeline once (immediately)
  python main.py run

  # Run pipeline for specific topics
  python main.py run --topics "Rust 웹 프레임워크 비교" "Go 언어 성능 최적화"

  # Run only analytics collection
  python main.py analytics

  # Start Celery worker (for production scheduling)
  celery -A orchestrator.thanos worker --loglevel=info

  # Start Celery beat scheduler (for production cron)
  celery -A orchestrator.thanos beat --loglevel=info
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from core.database import init_db
from core.models import TopicData
from orchestrator.thanos import thanos
from utils.logger import get_logger

logger = get_logger("main")


async def run_pipeline(topic_titles: list[str] | None = None) -> None:
    await init_db()

    topics = None
    if topic_titles:
        topics = [
            TopicData(
                title=title,
                keywords=title.split(),
                category="개발 일반",
                trend_score=80.0,
                source="manual",
            )
            for title in topic_titles
        ]

    run = await thanos.snap(topics=topics)

    print("\n" + "=" * 60)
    print("  Snap complete! 🟣")
    print("=" * 60)
    print(f"  Run ID         : {run.run_id}")
    print(f"  Published      : {run.total_posts_published}")
    print(f"  Failed         : {run.total_posts_failed}")
    print(f"  Human Review   : {run.total_posts_human_review}")
    print(f"  Status         : {run.status.value}")
    if run.error_log:
        print(f"  Errors         : {run.error_log}")
    print("=" * 60 + "\n")

    for post in run.posts:
        if post.published_url:
            print(f"  ✅ {post.title}")
            print(f"     {post.published_url}\n")


async def run_analytics() -> None:
    await init_db()
    await thanos.collect_analytics()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Techblog Automation — Thanos Orchestrator"
    )
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Execute the full pipeline.")
    run_parser.add_argument(
        "--topics",
        nargs="*",
        help="Optional list of topic titles to use instead of auto-discovery.",
    )

    subparsers.add_parser("analytics", help="Collect analytics for published posts.")

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.command == "run":
        asyncio.run(run_pipeline(topic_titles=getattr(args, "topics", None)))
    elif args.command == "analytics":
        asyncio.run(run_analytics())
    else:
        print(__doc__)
        sys.exit(0)


if __name__ == "__main__":
    main()
