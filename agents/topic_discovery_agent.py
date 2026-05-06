from __future__ import annotations

import asyncio
import re
import uuid
from typing import Optional

import httpx
import feedparser

from agents.base_agent import BaseAgent
from core.models import PostDraft, TopicData
from core.config import settings


# ─── Source Scrapers ──────────────────────────────────────────────────────────


async def _fetch_github_trending(language: str = "") -> list[dict]:
    """Scrape GitHub Trending for hot repositories."""
    url = f"https://github.com/trending/{language}?since=daily"
    try:
        async with httpx.AsyncClient(timeout=20, headers={"User-Agent": "TechBlogBot/1.0"}) as client:
            response = await client.get(url)
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.text, "lxml")
        results = []
        for repo in soup.select("article.Box-row")[:10]:
            h2 = repo.select_one("h2 a")
            desc = repo.select_one("p")
            if h2:
                repo_name = h2.get_text(strip=True).replace("\n", "").replace(" ", "")
                results.append(
                    {
                        "title": repo_name,
                        "summary": desc.get_text(strip=True) if desc else "",
                        "source": "github_trending",
                        "source_url": f"https://github.com/{repo_name}",
                        "trend_score": 90.0,
                    }
                )
        return results
    except Exception:
        return []


async def _fetch_hacker_news() -> list[dict]:
    """Fetch top tech stories from Hacker News."""
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            ids_response = await client.get("https://hacker-news.firebaseio.com/v0/topstories.json")
            story_ids = ids_response.json()[:20]

            tasks = [
                client.get(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json")
                for sid in story_ids
            ]
            responses = await asyncio.gather(*tasks, return_exceptions=True)

        results = []
        for resp in responses:
            if isinstance(resp, Exception):
                continue
            story = resp.json()
            if story and story.get("type") == "story":
                results.append(
                    {
                        "title": story.get("title", ""),
                        "summary": story.get("title", ""),
                        "source": "hacker_news",
                        "source_url": story.get("url", f"https://news.ycombinator.com/item?id={story.get('id')}"),
                        "trend_score": min(float(story.get("score", 0)) / 10, 100.0),
                    }
                )
        return sorted(results, key=lambda x: x["trend_score"], reverse=True)[:10]
    except Exception:
        return []


async def _fetch_dev_to() -> list[dict]:
    """Fetch trending articles from dev.to RSS feed."""
    try:
        feed = feedparser.parse("https://dev.to/feed/tag/programming")
        results = []
        for entry in feed.entries[:10]:
            results.append(
                {
                    "title": entry.get("title", ""),
                    "summary": entry.get("summary", "")[:300],
                    "source": "dev_to",
                    "source_url": entry.get("link", ""),
                    "trend_score": 70.0,
                }
            )
        return results
    except Exception:
        return []


# ─── Topic Discovery Agent ────────────────────────────────────────────────────


class TopicDiscoveryAgent(BaseAgent):
    """
    Power Stone — discovers trending technical topics from multiple sources.

    Sources:
    - GitHub Trending
    - Hacker News Top Stories
    - dev.to RSS Feed
    """

    CATEGORY_KEYWORDS: dict[str, list[str]] = {
        "백엔드": ["api", "server", "backend", "database", "rust", "go", "python", "java", "spring"],
        "프론트엔드": ["react", "vue", "angular", "typescript", "css", "ui", "frontend", "next"],
        "데브옵스": ["docker", "kubernetes", "ci/cd", "devops", "terraform", "aws", "cloud"],
        "AI/ML": ["ai", "ml", "llm", "gpt", "deep learning", "machine learning", "transformer"],
        "모바일": ["ios", "android", "swift", "kotlin", "flutter", "react native"],
        "보안": ["security", "vulnerability", "auth", "oauth", "encryption", "cve"],
    }

    def __init__(self) -> None:
        super().__init__(name="topic_discovery", max_retries=3)

    async def execute(self, draft: PostDraft) -> PostDraft:
        """
        Discover trending topics and attach the best one to the draft.
        (Thanos uses this method to fill the pipeline with topics.)
        """
        self.logger.info("Fetching topics from all sources")

        github, hn, devto = await asyncio.gather(
            _fetch_github_trending(),
            _fetch_hacker_news(),
            _fetch_dev_to(),
            return_exceptions=True,
        )

        raw_topics: list[dict] = []
        for source_result in [github, hn, devto]:
            if isinstance(source_result, list):
                raw_topics.extend(source_result)

        self.logger.info(f"Collected {len(raw_topics)} raw topics")

        scored_topics = self._deduplicate_and_score(raw_topics)
        top_topics = scored_topics[:settings.topics_per_run]

        if not top_topics:
            raise RuntimeError("No topics discovered from any source.")

        # Attach the highest-priority topic to this draft
        best = top_topics[0]
        draft.topic = TopicData(
            topic_id=str(uuid.uuid4()),
            title=best["title"],
            summary=best.get("summary", ""),
            keywords=self._extract_keywords(best["title"]),
            category=self._classify_category(best["title"]),
            trend_score=best.get("trend_score", 50.0),
            source=best.get("source", ""),
            source_url=best.get("source_url", ""),
        )
        self.logger.info(f"Selected topic: {draft.topic.title}")
        return draft

    async def discover_batch(self, count: int) -> list[TopicData]:
        """
        Discover a batch of unique topics for Thanos to distribute
        across multiple drafts in a single pipeline run.
        """
        github, hn, devto = await asyncio.gather(
            _fetch_github_trending(),
            _fetch_hacker_news(),
            _fetch_dev_to(),
            return_exceptions=True,
        )
        raw_topics: list[dict] = []
        for source_result in [github, hn, devto]:
            if isinstance(source_result, list):
                raw_topics.extend(source_result)

        scored = self._deduplicate_and_score(raw_topics)
        topics: list[TopicData] = []
        for item in scored[:count]:
            topics.append(
                TopicData(
                    topic_id=str(uuid.uuid4()),
                    title=item["title"],
                    summary=item.get("summary", ""),
                    keywords=self._extract_keywords(item["title"]),
                    category=self._classify_category(item["title"]),
                    trend_score=item.get("trend_score", 50.0),
                    source=item.get("source", ""),
                    source_url=item.get("source_url", ""),
                )
            )
        return topics

    # ─── Helpers ───────────────────────────────────────────────────────────────

    def _deduplicate_and_score(self, raw: list[dict]) -> list[dict]:
        seen_titles: set[str] = set()
        unique: list[dict] = []
        for item in raw:
            normalized = item["title"].lower().strip()
            if normalized not in seen_titles and item.get("title"):
                seen_titles.add(normalized)
                unique.append(item)
        return sorted(unique, key=lambda x: x.get("trend_score", 0), reverse=True)

    def _classify_category(self, title: str) -> str:
        lower = title.lower()
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            if any(kw in lower for kw in keywords):
                return category
        return "개발 일반"

    def _extract_keywords(self, title: str) -> list[str]:
        stop_words = {"a", "an", "the", "and", "or", "in", "on", "at", "to", "for", "of", "with"}
        words = re.findall(r"\b[a-zA-Z가-힣]{2,}\b", title)
        return [w for w in words if w.lower() not in stop_words][:8]
