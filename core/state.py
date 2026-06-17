# core/state.py
# © Copyright 2026 Sam [Platinum]

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from companies.models import Company, Player
from core.clock import GameClock
from finance.system import FinanceSystem
from industries.real_estate.industry import RealEstateIndustry
from industries.real_estate.economy import DevelopmentProject, LandParcel
from industries.real_estate.models import Property
from news.models import NewsFeed
from npcs.models import NPCSimulationSystem
from world.system import WorldSystem


CURRENT_SAVE_VERSION = 2


@dataclass(slots=True)
class GameState:
    world_id: str = field(default_factory=lambda: uuid4().hex)
    world_name: str = "New World"
    save_version: int = CURRENT_SAVE_VERSION
    clock: GameClock = field(default_factory=GameClock)
    world: WorldSystem = field(default_factory=WorldSystem.starter_world)
    player: Player = field(default_factory=Player.starter)
    npc_companies: list[Company] = field(default_factory=NPCSimulationSystem.starter_companies)
    player_properties: list[Property] = field(default_factory=list)
    player_land: list[LandParcel] = field(default_factory=list)
    development_projects: list[DevelopmentProject] = field(default_factory=list)
    financials: FinanceSystem = field(default_factory=FinanceSystem)
    news_feed: NewsFeed = field(default_factory=NewsFeed)
    tick_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def advance_days(self, days: int) -> None:
        self.clock.step(days=days)
        self.tick_count += 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "world_id": self.world_id,
            "world_name": self.world_name,
            "save_version": self.save_version,
            "clock": self.clock.to_dict(),
            "world": self.world.to_dict(),
            "player": self.player.to_dict(),
            "npc_companies": [company.to_dict() for company in self.npc_companies],
            "player_properties": [property_.to_dict() for property_ in self.player_properties],
            "player_land": [parcel.to_dict() for parcel in self.player_land],
            "development_projects": [project.to_dict() for project in self.development_projects],
            "financials": self.financials.to_dict(),
            "news_feed": self.news_feed.to_dict(),
            "tick_count": self.tick_count,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GameState:
        return cls(
            world_id=str(data["world_id"]),
            world_name=str(data.get("world_name", "New World")),
            save_version=int(data.get("save_version", CURRENT_SAVE_VERSION)),
            clock=GameClock.from_dict(data["clock"]),
            world=WorldSystem.from_dict(data.get("world", {"continents": []})),
            player=Player.from_dict(data.get("player", Player.starter().to_dict())),
            npc_companies=[
                Company.from_dict(company) for company in data.get("npc_companies", [])
            ],
            player_properties=[
                Property.from_dict(property_, RealEstateIndustry().building_types)
                for property_ in data.get("player_properties", [])
            ],
            player_land=[
                LandParcel.from_dict(parcel) for parcel in data.get("player_land", [])
            ],
            development_projects=[
                DevelopmentProject.from_dict(project)
                for project in data.get("development_projects", [])
            ],
            financials=FinanceSystem.from_dict(data.get("financials")),
            news_feed=NewsFeed.from_dict(data.get("news_feed")),
            tick_count=int(data.get("tick_count", 0)),
            metadata=dict(data.get("metadata", {})),
        )
