# core/clock.py
# © Copyright 2026 Sam [Platinum]

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum


class GameSpeed(Enum):
    PAUSED = 0
    ONE_X = 1
    TWO_X = 2
    FIVE_X = 5

    @property
    def days_per_tick(self) -> int:
        return self.value

    @property
    def label(self) -> str:
        labels: dict[GameSpeed, str] = {
            GameSpeed.PAUSED: "Paused",
            GameSpeed.ONE_X: "1x",
            GameSpeed.TWO_X: "2x",
            GameSpeed.FIVE_X: "5x",
        }
        return labels[self]


@dataclass(slots=True)
class GameClock:
    current_date: date = field(default_factory=lambda: date(2026, 1, 1))
    speed: GameSpeed = GameSpeed.PAUSED

    @property
    def is_paused(self) -> bool:
        return self.speed is GameSpeed.PAUSED

    def set_speed(self, speed: GameSpeed) -> None:
        self.speed = speed

    def pause(self) -> None:
        self.set_speed(GameSpeed.PAUSED)

    def step(self, days: int = 1) -> date:
        if days < 1:
            raise ValueError("GameClock.step requires at least one day.")

        self.current_date += timedelta(days=days)
        return self.current_date

    def advance_tick(self) -> date:
        if self.is_paused:
            return self.current_date

        return self.step(days=self.speed.days_per_tick)

    def to_dict(self) -> dict[str, str]:
        return {
            "current_date": self.current_date.isoformat(),
            "speed": self.speed.name,
        }

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> GameClock:
        return cls(
            current_date=date.fromisoformat(data["current_date"]),
            speed=GameSpeed[data["speed"]],
        )


ClockSpeed = GameSpeed
SimulationClock = GameClock
