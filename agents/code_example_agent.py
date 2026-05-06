from __future__ import annotations

import asyncio
import re
import subprocess
import tempfile
import os
from typing import Optional

from agents.base_agent import BaseAgent
from core.models import PostDraft, CodeBlock
from utils.llm_client import llm_client

SUPPORTED_LANGUAGES = {"python", "javascript", "typescript", "java", "go", "rust", "bash", "sh"}

EXECUTION_TIMEOUT = 30  # seconds

# Language → (file extension, run command template)
LANGUAGE_RUNNERS: dict[str, tuple[str, list[str]]] = {
    "python": (".py", ["python", "{file}"]),
    "javascript": (".js", ["node", "{file}"]),
    "typescript": (".ts", ["npx", "ts-node", "{file}"]),
    "bash": (".sh", ["bash", "{file}"]),
    "sh": (".sh", ["bash", "{file}"]),
    "go": (".go", ["go", "run", "{file}"]),
}

FIX_SYSTEM_PROMPT = """당신은 코드 수정 전문가입니다.
주어진 코드와 에러 메시지를 분석하여 올바르게 동작하는 수정된 코드만 반환합니다.
수정된 코드만 출력하세요. 설명이나 마크다운 래퍼는 포함하지 마세요.
"""


class CodeExampleAgent(BaseAgent):
    """
    Reality Stone — validates and repairs code blocks embedded in the post.

    For each CodeBlock:
    1. Syntax-lint the code (language-dependent).
    2. Execute in a sandboxed subprocess (supported langs only).
    3. If execution fails, ask LLM to fix and retry (up to max_retries).
    4. Mark the block as valid/invalid with execution output.
    """

    def __init__(self) -> None:
        super().__init__(name="code_example", max_retries=5)

    async def execute(self, draft: PostDraft) -> PostDraft:
        if not draft.code_blocks:
            self.logger.info("No code blocks to validate.")
            return draft

        tasks = [self._process_block(block) for block in draft.code_blocks]
        processed = await asyncio.gather(*tasks, return_exceptions=True)

        updated_blocks: list[CodeBlock] = []
        for original, result in zip(draft.code_blocks, processed):
            if isinstance(result, Exception):
                self.logger.warning(f"Block {original.index} processing error: {result}")
                original.is_tested = True
                original.is_valid = False
                original.error_message = str(result)
                updated_blocks.append(original)
            else:
                updated_blocks.append(result)

        draft.code_blocks = updated_blocks

        # Patch the markdown with corrected code
        draft.content_markdown = self._patch_markdown(draft.content_markdown, draft.code_blocks)
        return draft

    # ─── Block Processing ──────────────────────────────────────────────────────

    async def _process_block(self, block: CodeBlock) -> CodeBlock:
        lang = block.language.lower()
        if lang not in LANGUAGE_RUNNERS:
            # Not runnable — mark as valid (trust it)
            block.is_valid = True
            block.is_tested = False
            return block

        code_to_test = block.code
        for attempt in range(1, self.max_retries + 1):
            success, output = await asyncio.get_event_loop().run_in_executor(
                None, self._run_code, lang, code_to_test
            )
            if success:
                block.is_valid = True
                block.is_tested = True
                block.execution_output = output
                if code_to_test != block.code:
                    block.fixed_code = code_to_test
                return block

            self.logger.warning(f"Block {block.index} attempt {attempt} failed: {output[:200]}")

            if attempt < self.max_retries:
                code_to_test = await self._fix_with_llm(lang, code_to_test, output)

        block.is_valid = False
        block.is_tested = True
        block.error_message = output
        return block

    def _run_code(self, lang: str, code: str) -> tuple[bool, str]:
        ext, cmd_template = LANGUAGE_RUNNERS[lang]
        with tempfile.NamedTemporaryFile(mode="w", suffix=ext, delete=False, encoding="utf-8") as f:
            f.write(code)
            tmp_path = f.name

        try:
            cmd = [c.replace("{file}", tmp_path) for c in cmd_template]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=EXECUTION_TIMEOUT,
            )
            if result.returncode == 0:
                return True, result.stdout
            return False, result.stderr or result.stdout
        except subprocess.TimeoutExpired:
            return False, "Execution timed out."
        except FileNotFoundError as e:
            # Runtime not installed — skip execution
            return True, f"Runtime not available ({e}), skipping execution."
        finally:
            os.unlink(tmp_path)

    async def _fix_with_llm(self, lang: str, code: str, error: str) -> str:
        user_prompt = (
            f"언어: {lang}\n\n"
            f"에러 메시지:\n{error[:500]}\n\n"
            f"원본 코드:\n{code}"
        )
        fixed = await llm_client.complete(
            system_prompt=FIX_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_tokens=2048,
            temperature=0.2,
        )
        # Strip any accidental markdown fences
        fixed = re.sub(r"^```\w*\n?", "", fixed.strip())
        fixed = re.sub(r"```$", "", fixed.strip())
        return fixed.strip()

    # ─── Markdown Patching ─────────────────────────────────────────────────────

    def _patch_markdown(self, markdown: str, blocks: list[CodeBlock]) -> str:
        """Replace original code blocks with fixed versions in the markdown."""
        pattern = re.compile(r"```(\w+)?\n(.*?)```", re.DOTALL)
        block_iter = iter(blocks)

        def replacer(match: re.Match) -> str:
            try:
                block = next(block_iter)
                if block.fixed_code:
                    return f"```{block.language}\n{block.fixed_code}\n```"
            except StopIteration:
                pass
            return match.group(0)

        return pattern.sub(replacer, markdown)
