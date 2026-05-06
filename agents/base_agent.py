from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from typing import Any, Optional
from datetime import datetime

from core.models import AgentResult, AgentStatus, PostDraft
from core.config import settings
from utils.logger import get_logger


class BaseAgent(ABC):
    """
    Abstract base class for all pipeline agents.

    Provides:
    - Structured logging with agent name context
    - Automatic retry with exponential back-off
    - AgentResult tracking attached to the PostDraft
    """

    def __init__(self, name: str, max_retries: Optional[int] = None) -> None:
        self.name = name
        self.max_retries = max_retries if max_retries is not None else settings.max_retry_count
        self.logger = get_logger(f"agent.{name}")

    # ─── Public API ────────────────────────────────────────────────────────────

    async def run(self, draft: PostDraft) -> PostDraft:
        """
        Execute the agent with retry logic.
        Records an AgentResult on the draft regardless of success/failure.
        """
        start = time.monotonic()
        last_error: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 1):
            try:
                self.logger.info(
                    "agent_start",
                    attempt=attempt,
                    max_retries=self.max_retries,
                    post_id=draft.post_id,
                )
                draft = await self.execute(draft)
                duration = time.monotonic() - start
                draft.record_result(
                    AgentResult(
                        agent_name=self.name,
                        status=AgentStatus.SUCCESS,
                        duration_seconds=round(duration, 2),
                        attempt=attempt,
                    )
                )
                self.logger.info("agent_success", duration=round(duration, 2), post_id=draft.post_id)
                return draft

            except Exception as exc:
                last_error = exc
                self.logger.warning(
                    "agent_retry",
                    attempt=attempt,
                    error=str(exc),
                    post_id=draft.post_id,
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(2 ** attempt)   # exponential back-off

        # All retries exhausted
        duration = time.monotonic() - start
        draft.increment_retry(self.name)
        draft.record_result(
            AgentResult(
                agent_name=self.name,
                status=AgentStatus.FAILED,
                error=str(last_error),
                duration_seconds=round(duration, 2),
                attempt=self.max_retries,
            )
        )
        self.logger.error(
            "agent_failed",
            error=str(last_error),
            post_id=draft.post_id,
        )
        raise RuntimeError(f"[{self.name}] failed after {self.max_retries} attempts: {last_error}")

    # ─── Abstract ──────────────────────────────────────────────────────────────

    @abstractmethod
    async def execute(self, draft: PostDraft) -> PostDraft:
        """
        Core agent logic. Receives the current PostDraft, performs work,
        and returns the updated PostDraft.
        """
        ...
