# core/__init__.py
# © Copyright 2026 Sam [Platinum]

from core.clock import ClockSpeed, GameClock, GameSpeed, SimulationClock
from core.engine import GameEngine, GameSnapshot, SimulationEngine, SimulationSnapshot
from core.events import Event, EventBus
from core.save_manager import SaveInfo, SaveManager
from core.state import CURRENT_SAVE_VERSION, GameState

__all__ = [
    "ClockSpeed",
    "CURRENT_SAVE_VERSION",
    "Event",
    "EventBus",
    "GameClock",
    "GameEngine",
    "GameSnapshot",
    "GameSpeed",
    "GameState",
    "SaveInfo",
    "SaveManager",
    "SimulationClock",
    "SimulationEngine",
    "SimulationSnapshot",
]
