# news/models.py
# © Copyright 2026 Sam [Platinum]

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any
from uuid import uuid4


class NewsCategory(Enum):
    COMPANY = "company"
    FINANCE = "finance"
    REAL_ESTATE = "real_estate"
    BANKING = "banking"
    RESEARCH = "research"
    NPC = "npc"
    MARKET = "market"
    SAVE = "save"


@dataclass(frozen=True, slots=True)
class NewsItem:
    headline: str
    category: NewsCategory
    published_on: date
    news_id: str = field(default_factory=lambda: f"news_{uuid4().hex}")

    def __post_init__(self) -> None:
        if not self.headline.strip():
            raise ValueError("News headline cannot be empty.")
        if isinstance(self.category, str):
            object.__setattr__(self, "category", NewsCategory(self.category))
        if isinstance(self.published_on, str):
            object.__setattr__(self, "published_on", date.fromisoformat(self.published_on))

    def to_dict(self) -> dict[str, Any]:
        return {
            "news_id": self.news_id,
            "headline": self.headline,
            "category": self.category.value,
            "published_on": self.published_on.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NewsItem:
        return cls(
            news_id=str(data["news_id"]),
            headline=str(data["headline"]),
            category=NewsCategory(str(data["category"])),
            published_on=date.fromisoformat(str(data["published_on"])),
        )


@dataclass(slots=True)
class NewsFeed:
    items: list[NewsItem] = field(default_factory=list)
    max_items: int = 100

    def add(
        self,
        headline: str,
        category: NewsCategory,
        published_on: date,
    ) -> NewsItem:
        item = NewsItem(
            headline=self._headline(headline),
            category=category,
            published_on=published_on,
        )
        self.items.insert(0, item)
        del self.items[self.max_items :]
        return item

    def recent(self, limit: int = 10) -> tuple[NewsItem, ...]:
        if limit < 1:
            return ()

        return tuple(self.items[:limit])

    def to_dict(self) -> dict[str, Any]:
        return {
            "items": [item.to_dict() for item in self.items],
            "max_items": self.max_items,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> NewsFeed:
        if data is None:
            return cls()

        return cls(
            items=[NewsItem.from_dict(item) for item in data.get("items", [])],
            max_items=int(data.get("max_items", 100)),
        )

    def _headline(self, headline: str) -> str:
        clean = " ".join(headline.strip().split())
        if len(clean) <= 96:
            return clean

        return clean[:93].rstrip() + "..."
