from __future__ import annotations

import asyncio
from typing import Any, Optional
import openai
import anthropic
from utils.logger import get_logger
from core.config import settings

logger = get_logger("llm_client")


class LLMClient:
    """
    Unified LLM client with automatic fallback.
    Priority order: OpenAI → Anthropic
    """

    def __init__(self) -> None:
        self._openai: Optional[openai.AsyncOpenAI] = None
        self._anthropic: Optional[anthropic.AsyncAnthropic] = None

        if settings.openai_api_key:
            self._openai = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        if settings.anthropic_api_key:
            self._anthropic = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        preferred: str = "openai",
    ) -> str:
        """
        Generate text completion with automatic fallback between providers.
        """
        providers = (
            ["openai", "anthropic"]
            if preferred == "openai"
            else ["anthropic", "openai"]
        )

        last_error: Optional[Exception] = None
        for provider in providers:
            try:
                if provider == "openai" and self._openai:
                    return await self._call_openai(system_prompt, user_prompt, max_tokens, temperature)
                elif provider == "anthropic" and self._anthropic:
                    return await self._call_anthropic(system_prompt, user_prompt, max_tokens, temperature)
            except Exception as exc:
                logger.warning(f"LLM provider {provider} failed: {exc}. Trying fallback.")
                last_error = exc

        raise RuntimeError(f"All LLM providers failed. Last error: {last_error}")

    async def _call_openai(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        temperature: float,
    ) -> str:
        response = await self._openai.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content or ""

    async def _call_anthropic(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        temperature: float,
    ) -> str:
        response = await self._anthropic.messages.create(
            model=settings.anthropic_model,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.content[0].text if response.content else ""


# ─── Singleton ────────────────────────────────────────────────────────────────

llm_client = LLMClient()
