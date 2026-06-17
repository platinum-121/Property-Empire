# core/engine.py
# © Copyright 2026 Sam [Platinum]

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from core.clock import GameClock, GameSpeed
from core.events import Event, EventBus
from core.state import GameState
from gameplay.service import GameplayService
from news.models import NewsCategory
from npcs.models import NPCSimulationSystem


@dataclass(frozen=True, slots=True)
class GameSnapshot:
    current_date: date
    speed: GameSpeed
    tick_count: int
    registered_industries: tuple[str, ...]
    world_id: str
    world_name: str


class GameEngine:
    def __init__(
        self,
        event_bus: EventBus | None = None,
        state: GameState | None = None,
    ) -> None:
        self.event_bus = event_bus or EventBus()
        self.state = state or GameState()
        self.npc_simulation = NPCSimulationSystem()
        self.gameplay = GameplayService()

    @property
    def clock(self) -> GameClock:
        return self.state.clock

    def set_speed(self, speed: GameSpeed) -> None:
        self.clock.set_speed(speed)
        self.event_bus.publish(Event(name="clock.speed_changed", payload={"speed": speed.name}))

    def pause(self) -> None:
        self.clock.pause()
        self.event_bus.publish(Event(name="clock.paused"))

    def step(self) -> GameSnapshot:
        return self._advance(days=1)

    def tick(self) -> GameSnapshot:
        if self.clock.is_paused:
            return self.snapshot()

        return self._advance(days=self.clock.speed.days_per_tick)

    def snapshot(self) -> GameSnapshot:
        return GameSnapshot(
            current_date=self.clock.current_date,
            speed=self.clock.speed,
            tick_count=self.state.tick_count,
            registered_industries=("property",),
            world_id=self.state.world_id,
            world_name=self.state.world_name,
        )

    def _advance(self, days: int) -> GameSnapshot:
        for _ in range(days):
            self.gameplay.process_player_days(state=self.state, days=1)
            npc_report = self.npc_simulation.process_days(
                companies=self.state.npc_companies,
                days=1,
                world=self.state.world,
            )
            self._publish_npc_news(npc_report)
            self.state.advance_days(days=1)
        self.event_bus.publish(Event(name="game.tick", payload={"days": days}))
        return self.snapshot()

    def _publish_npc_news(self, report: object) -> None:
        portfolios = int(getattr(report, "assets_collected", 0))
        offices = int(getattr(report, "branches_opened", 0))
        loans = int(getattr(report, "loans_taken", 0))

        if portfolios:
            self.state.news_feed.add(
                f"Competitors Purchase {portfolios} Property Portfolio",
                NewsCategory.NPC,
                self.clock.current_date,
            )
        if offices:
            self.state.news_feed.add(
                f"Competitors Expand Into {offices} City",
                NewsCategory.NPC,
                self.clock.current_date,
            )
        if loans:
            self.state.news_feed.add(
                f"Competitors Secure {loans} Property Loan",
                NewsCategory.NPC,
                self.clock.current_date,
            )


SimulationEngine = GameEngine
SimulationSnapshot = GameSnapshot
