"""Pydantic v2 数据模型 —— 类型安全 + 自动校验 + JSON 序列化."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, computed_field, field_validator


# ================================================================
# Bangumi API 原始响应模型
# ================================================================

class RatingInfo(BaseModel):
    """评分信息."""
    score: float = 0.0
    total: int = 0
    rank: int = 0


class ImageInfo(BaseModel):
    """封面图."""
    large: str = ""
    common: str = ""
    medium: str = ""
    small: str = ""


class Subject(BaseModel):
    """条目（动画）基础信息."""

    id: int
    name: str = ""
    name_cn: str = ""
    summary: str = ""
    date: str = ""          # YYYY-MM-DD
    platform: str = ""
    eps: int = 0
    total_episodes: int = 0
    rating: RatingInfo | None = None
    rank: int = 0
    images: ImageInfo | None = None

    @field_validator("name", "name_cn", "summary", "date", "platform", mode="before")
    @classmethod
    def _none_to_str(cls, v: str | None) -> str:
        """API 可能返回 null."""
        return v or ""

    @computed_field
    @property
    def year(self) -> int | None:
        """从 date 提取年份."""
        if self.date and len(self.date) >= 4:
            try:
                return int(self.date[:4])
            except ValueError:
                pass
        return None

    @computed_field
    @property
    def cover_url(self) -> str:
        """封面 URL (优先 large)."""
        if self.images:
            return self.images.large or self.images.common or self.images.medium or ""
        return ""

    @computed_field
    @property
    def score(self) -> float:
        """Bangumi 均分."""
        return self.rating.score if self.rating else 0.0


# ================================================================
# 收藏条目
# ================================================================

COLLECTION_TYPE_MAP: dict[int, str] = {
    1: "想看",
    2: "看过",
    3: "在看",
    4: "搁置",
    5: "抛弃",
}


class CollectionItem(BaseModel):
    """用户收藏条目."""

    subject_id: int
    subject: Subject | None = None
    name: str = ""                             # 无 subject 详情时的后备名称
    type: int = 0                              # 1-5
    rate: int = Field(default=0, ge=0, le=10)  # 用户评分
    comment: str = ""
    tags: list[str] = Field(default_factory=list)
    ep_status: int = 0
    vol_status: int = 0
    updated_at: str = ""
    private: bool = False

    @field_validator("comment", "name", "updated_at", mode="before")
    @classmethod
    def _none_to_empty(cls, v: str | None) -> str:
        """API 可能返回 null，统一转为空字符串."""
        return v or ""
    updated_at: str = ""
    private: bool = False

    @computed_field
    @property
    def collection_type_name(self) -> str:
        """中文收藏类型."""
        return COLLECTION_TYPE_MAP.get(self.type, f"未知({self.type})")

    @computed_field
    @property
    def subject_name(self) -> str:
        """最佳显示名称: name_cn > name > 后备."""
        if self.subject:
            return self.subject.name_cn or self.subject.name or self.name
        return self.name or f"#{self.subject_id}"

    @computed_field
    @property
    def subject_year(self) -> int | None:
        """条目年份."""
        return self.subject.year if self.subject else None

    @computed_field
    @property
    def subject_score(self) -> float:
        """Bangumi 均分."""
        return self.subject.score if self.subject else 0.0

    @computed_field
    @property
    def subject_cover(self) -> str:
        """封面 URL."""
        return self.subject.cover_url if self.subject else ""


class UserCollection(BaseModel):
    """用户完整收藏."""

    username: str
    total: int = 0
    items: list[CollectionItem] = Field(default_factory=list)
    fetched_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# ================================================================
# 分析结果
# ================================================================

class YearStats(BaseModel):
    """单年份统计."""

    year: int
    total: int = 0
    watching: int = 0
    finished: int = 0
    wish: int = 0
    on_hold: int = 0
    dropped: int = 0
    avg_rating: float = 0.0


class YearTrendItem(BaseModel):
    """年度趋势数据点 (给前端)."""

    year: int
    total: int
    finished: int
    watching: int
    wish: int
    on_hold: int = 0
    dropped: int = 0
    avg_rating: float = 0.0


class TopRatedItem(BaseModel):
    """高分条目摘要."""

    subject_id: int
    name: str
    name_cn: str = ""
    rate: int
    year: int | None = None
    cover_url: str = ""
    bangumi_score: float = 0.0


class AnalysisReport(BaseModel):
    """完整分析报告 —— 可用于 JSON 序列化与模板渲染."""

    username: str
    total_items: int

    # 按年份
    by_year: dict[int, YearStats] = Field(default_factory=dict)

    # 按收藏类型
    type_counts: dict[str, int] = Field(default_factory=dict)

    # 评分分布 (评分 → 数量)
    rating_distribution: dict[int, int] = Field(default_factory=dict)

    # 高分排行
    top_rated: list[TopRatedItem] = Field(default_factory=list)

    # 年度趋势
    year_trend: list[YearTrendItem] = Field(default_factory=list)

    # 整体统计
    overall_avg_rating: float = 0.0
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
