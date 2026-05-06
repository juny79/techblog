from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime
import uuid


# ─── Pipeline & Agent Status Enums ─────────────────────────────────────────────


class PipelineStatus(str, Enum):
    IDLE = "idle"
    TOPIC_DISCOVERY = "topic_discovery"
    CONTENT_GENERATION = "content_generation"
    CODE_REVIEW = "code_review"
    IMAGE_GENERATION = "image_generation"
    SEO_OPTIMIZATION = "seo_optimization"
    QUALITY_CHECK = "quality_check"
    HUMAN_REVIEW = "human_review"
    PUBLISHING = "publishing"
    ANALYTICS = "analytics"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


# ─── Agent Result ───────────────────────────────────────────────────────────────


class AgentResult(BaseModel):
    agent_name: str
    status: AgentStatus
    data: Dict[str, Any] = {}
    error: Optional[str] = None
    duration_seconds: float = 0.0
    attempt: int = 1
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ─── Topic ─────────────────────────────────────────────────────────────────────


class TopicData(BaseModel):
    topic_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    summary: str = ""
    keywords: List[str] = []
    category: str = ""
    subcategory: str = ""
    trend_score: float = 0.0
    estimated_search_volume: int = 0
    priority: str = "medium"   # low | medium | high
    source: str = ""
    source_url: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ─── Code Block ────────────────────────────────────────────────────────────────


class CodeBlock(BaseModel):
    index: int = 0
    language: str
    code: str
    description: str = ""
    is_valid: bool = False
    is_tested: bool = False
    error_message: Optional[str] = None
    execution_output: Optional[str] = None
    fixed_code: Optional[str] = None

    def effective_code(self) -> str:
        """Return fixed code if available, otherwise original."""
        return self.fixed_code if self.fixed_code else self.code


# ─── SEO ───────────────────────────────────────────────────────────────────────


class SEOMetadata(BaseModel):
    seo_title: str = ""
    meta_description: str = ""
    tags: List[str] = []
    category: str = ""
    tistory_category_id: int = 0
    readability_score: float = 0.0
    keyword_density: Dict[str, float] = {}
    internal_links: List[str] = []
    external_links: List[str] = []


# ─── Image Asset ───────────────────────────────────────────────────────────────


class ImageAsset(BaseModel):
    image_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    image_type: str        # thumbnail | content | diagram
    local_path: str = ""
    tistory_url: str = ""
    alt_text: str = ""
    width: int = 0
    height: int = 0
    prompt_used: str = ""


# ─── Quality Report ────────────────────────────────────────────────────────────


class QualityReport(BaseModel):
    word_count: int = 0
    word_count_pass: bool = False

    code_valid_pass: bool = False

    plagiarism_ratio: float = 0.0
    plagiarism_pass: bool = False

    seo_score: float = 0.0
    seo_score_pass: bool = False

    image_count: int = 0
    image_pass: bool = False

    spelling_errors: List[str] = []
    spelling_pass: bool = False

    overall_pass: bool = False
    issues: List[str] = []
    score: float = 0.0
    reviewed_at: datetime = Field(default_factory=datetime.utcnow)


# ─── Post Draft ────────────────────────────────────────────────────────────────


class PostDraft(BaseModel):
    post_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    topic: Optional[TopicData] = None
    title: str = ""
    content_markdown: str = ""
    content_html: str = ""
    code_blocks: List[CodeBlock] = []
    seo: SEOMetadata = Field(default_factory=SEOMetadata)
    images: List[ImageAsset] = []
    quality_report: Optional[QualityReport] = None
    pipeline_status: PipelineStatus = PipelineStatus.IDLE
    retry_counts: Dict[str, int] = {}
    agent_results: List[AgentResult] = []
    published_url: str = ""
    tistory_post_id: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def increment_retry(self, agent_name: str) -> int:
        self.retry_counts[agent_name] = self.retry_counts.get(agent_name, 0) + 1
        return self.retry_counts[agent_name]

    def get_retry_count(self, agent_name: str) -> int:
        return self.retry_counts.get(agent_name, 0)

    def record_result(self, result: AgentResult) -> None:
        self.agent_results.append(result)
        self.updated_at = datetime.utcnow()

    def thumbnail(self) -> Optional[ImageAsset]:
        for img in self.images:
            if img.image_type == "thumbnail":
                return img
        return None


# ─── Analytics ─────────────────────────────────────────────────────────────────


class AnalyticsSnapshot(BaseModel):
    post_id: str
    tistory_post_id: str
    views: int = 0
    likes: int = 0
    comments: int = 0
    search_impressions: int = 0
    search_clicks: int = 0
    average_position: float = 0.0
    collected_at: datetime = Field(default_factory=datetime.utcnow)


# ─── Pipeline Run ──────────────────────────────────────────────────────────────


class PipelineRun(BaseModel):
    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    posts: List[PostDraft] = []
    status: PipelineStatus = PipelineStatus.IDLE
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_posts_published: int = 0
    total_posts_failed: int = 0
    total_posts_human_review: int = 0
    error_log: List[str] = []
