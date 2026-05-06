from __future__ import annotations

import httpx
from typing import Any, Optional
from utils.logger import get_logger
from core.config import settings

logger = get_logger("tistory_client")

TISTORY_API_BASE = "https://www.tistory.com/apis"


class TistoryClient:
    """
    Tistory Open API client — OAuth 2.0 based.
    Docs: https://tistory.github.io/document-tistory-apis/
    """

    def __init__(self) -> None:
        self._access_token = settings.tistory_access_token
        self._blog_name = settings.tistory_blog_name

    # ─── Blog Info ─────────────────────────────────────────────────────────────

    async def get_blog_info(self) -> dict:
        """Retrieve blog info including category list."""
        return await self._get("/blog/info", {})

    async def get_categories(self) -> list[dict]:
        """Return list of categories for the blog."""
        data = await self.get_blog_info()
        blogs = data.get("tistory", {}).get("item", {}).get("blogs", {}).get("blog", [])
        if isinstance(blogs, dict):
            blogs = [blogs]
        for blog in blogs:
            if blog.get("name") == self._blog_name:
                categories = blog.get("categories", {}).get("category", [])
                if isinstance(categories, dict):
                    categories = [categories]
                return categories
        return []

    # ─── Post ──────────────────────────────────────────────────────────────────

    async def write_post(
        self,
        title: str,
        content: str,
        category_id: int,
        tags: list[str],
        visibility: int = 3,
        accept_comment: int = 1,
    ) -> dict:
        """
        Create a new post.
        visibility: 0=비공개, 1=보호, 3=공개
        """
        params = {
            "blogName": self._blog_name,
            "title": title,
            "content": content,
            "visibility": str(visibility),
            "category": str(category_id),
            "tag": ",".join(tags),
            "acceptComment": str(accept_comment),
        }
        return await self._post("/post/write", params)

    async def modify_post(self, post_id: str, title: str, content: str, tags: list[str]) -> dict:
        """Update an existing post."""
        params = {
            "blogName": self._blog_name,
            "postId": post_id,
            "title": title,
            "content": content,
            "tag": ",".join(tags),
        }
        return await self._post("/post/modify", params)

    async def get_post_list(self, page: int = 1) -> list[dict]:
        """Fetch post list for the blog."""
        data = await self._get("/post/list", {"blogName": self._blog_name, "page": str(page)})
        items = data.get("tistory", {}).get("item", {}).get("posts", {}).get("post", [])
        if isinstance(items, dict):
            items = [items]
        return items

    # ─── File Attachment ───────────────────────────────────────────────────────

    async def attach_file(self, file_path: str) -> str:
        """
        Upload an image file to Tistory and return the hosted URL.
        """
        url = f"{TISTORY_API_BASE}/post/attach"
        async with httpx.AsyncClient(timeout=60) as client:
            with open(file_path, "rb") as f:
                response = await client.post(
                    url,
                    data={
                        "access_token": self._access_token,
                        "blogName": self._blog_name,
                        "output": "json",
                    },
                    files={"uploadedfile": f},
                )
        result = response.json()
        tistory = result.get("tistory", {})
        if tistory.get("status") != "200":
            raise RuntimeError(f"Tistory attach_file failed: {result}")
        return tistory.get("url", "")

    # ─── Internal HTTP helpers ─────────────────────────────────────────────────

    async def _get(self, endpoint: str, extra_params: dict) -> dict:
        url = f"{TISTORY_API_BASE}{endpoint}"
        params = {
            "access_token": self._access_token,
            "output": "json",
            **extra_params,
        }
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    async def _post(self, endpoint: str, extra_params: dict) -> dict:
        url = f"{TISTORY_API_BASE}{endpoint}"
        data = {
            "access_token": self._access_token,
            "output": "json",
            **extra_params,
        }
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, data=data)
        response.raise_for_status()
        result = response.json()
        tistory = result.get("tistory", {})
        if tistory.get("status") not in ("200", "201", 200, 201):
            raise RuntimeError(f"Tistory API error: {result}")
        return result


# ─── Singleton ────────────────────────────────────────────────────────────────

tistory_client = TistoryClient()
