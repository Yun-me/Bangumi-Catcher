"""Pydantic v2 数据模型 —— 类型安全 + 自动校验."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, computed_field, field_validator


# ================================================================
# API 响应模型
# ================================================================

class RatingInfo(BaseModel):
    score: float = 0.0
    total: int = 0
    rank: int = 0


class ImageInfo(BaseModel):
    large: str = ""
    common: str = ""
    medium: str = ""
    small: str = ""


class Subject(BaseModel):
    id: int
    name: str = ""
    name_cn: str = ""
    summary: str = ""
    date: str = ""
    platform: str = ""
    eps: int = 0
    total_episodes: int = 0
    rating: RatingInfo | None = None
    rank: int = 0
    images: ImageInfo | None = None

    @field_validator("name", "name_cn", "summary", "date", "platform", mode="before")
    @classmethod
    def _none_str(cls, v: str | None) -> str:
        return v or ""

    @computed_field
    @property
    def year(self) -> int | None:
        if self.date and len(self.date) >= 4:
            try:
                return int(self.date[:4])
            except ValueError:
                pass
        return None

    @computed_field
    @property
    def cover_url(self) -> str:
        if self.images:
            return self.images.large or self.images.common or self.images.medium or ""
        return ""

    @computed_field
    @property
    def score(self) -> float:
        return self.rating.score if self.rating else 0.0

    @computed_field
    @property
    def season(self) -> str:
        """季度: Q1/Q2/Q3/Q4."""
        if self.date and len(self.date) >= 7:
            try:
                m = int(self.date[5:7])
                return f"Q{(m - 1) // 3 + 1}"
            except (ValueError, IndexError):
                pass
        return ""


# ================================================================
# 收藏条目
# ================================================================

COLLECTION_TYPE_MAP: dict[int, str] = {1: "想看", 2: "看过", 3: "在看", 4: "搁置", 5: "抛弃"}


class CollectionItem(BaseModel):
    subject_id: int
    subject: Subject | None = None
    name: str = ""
    type: int = 0
    rate: int = Field(default=0, ge=0, le=10)
    comment: str = ""
    tags: list[str] = Field(default_factory=list)
    ep_status: int = 0
    vol_status: int = 0
    updated_at: str = ""
    private: bool = False

    @field_validator("comment", "name", "updated_at", mode="before")
    @classmethod
    def _none_empty(cls, v: str | None) -> str:
        return v or ""

    @computed_field
    @property
    def collection_type_name(self) -> str:
        return COLLECTION_TYPE_MAP.get(self.type, f"未知({self.type})")

    @computed_field
    @property
    def subject_name(self) -> str:
        if self.subject:
            return self.subject.name_cn or self.subject.name or self.name
        return self.name or f"#{self.subject_id}"

    @computed_field
    @property
    def subject_year(self) -> int | None:
        return self.subject.year if self.subject else None

    @computed_field
    @property
    def subject_score(self) -> float:
        return self.subject.score if self.subject else 0.0

    @computed_field
    @property
    def subject_cover(self) -> str:
        return self.subject.cover_url if self.subject else ""

    @computed_field
    @property
    def completion_rate(self) -> float:
        """完成率 0-1."""
        if self.subject and self.subject.total_episodes:
            return min(self.ep_status / self.subject.total_episodes, 1.0)
        return 0.0


class UserCollection(BaseModel):
    username: str
    total: int = 0
    items: list[CollectionItem] = Field(default_factory=list)
    fetched_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# ================================================================
# 分析结果
# ================================================================

class YearStats(BaseModel):
    year: int
    total: int = 0
    watching: int = 0
    finished: int = 0
    wish: int = 0
    on_hold: int = 0
    dropped: int = 0
    avg_rating: float = 0.0


class YearTrendItem(BaseModel):
    year: int
    total: int
    finished: int
    watching: int
    wish: int
    on_hold: int = 0
    dropped: int = 0
    avg_rating: float = 0.0


class TopRatedItem(BaseModel):
    subject_id: int
    name: str
    name_cn: str = ""
    rate: int
    year: int | None = None
    cover_url: str = ""
    bangumi_score: float = 0.0


class SeasonStats(BaseModel):
    """季度统计."""
    season: str
    count: int


class TypeTrendItem(BaseModel):
    """收藏类型年度趋势."""
    year: int
    wish: int = 0
    watching: int = 0
    finished: int = 0
    on_hold: int = 0
    dropped: int = 0


class RatingCompareItem(BaseModel):
    """个人评分 vs Bangumi 均分."""
    name: str
    my_rate: int
    bgm_score: float


class AnalysisReport(BaseModel):
    username: str
    total_items: int
    by_year: dict[int, YearStats] = Field(default_factory=dict)
    type_counts: dict[str, int] = Field(default_factory=dict)
    rating_distribution: dict[int, int] = Field(default_factory=dict)
    top_rated: list[TopRatedItem] = Field(default_factory=list)
    year_trend: list[YearTrendItem] = Field(default_factory=list)
    type_trend: list[TypeTrendItem] = Field(default_factory=list)
    season_stats: list[SeasonStats] = Field(default_factory=list)
    rating_compare: list[RatingCompareItem] = Field(default_factory=list)
    avg_completion: float = 0.0
    overall_avg_rating: float = 0.0
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
