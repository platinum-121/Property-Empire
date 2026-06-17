# tests/test_engine.py
# © Copyright 2026 Sam [Platinum]

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread

from core.clock import GameClock, GameSpeed
from core.engine import GameEngine
from core.events import Event, EventBus
from core.save_manager import SaveManager
from core.state import GameState


def test_game_clock_starts_paused() -> None:
    clock = GameClock()

    assert clock.is_paused
    assert clock.current_date.isoformat() == "2026-01-01"


def test_game_clock_supports_requested_speeds() -> None:
    clock = GameClock()

    clock.set_speed(GameSpeed.TWO_X)
    clock.advance_tick()
    assert clock.current_date.isoformat() == "2026-01-03"

    clock.set_speed(GameSpeed.FIVE_X)
    clock.advance_tick()
    assert clock.current_date.isoformat() == "2026-01-08"


def test_game_clock_rejects_zero_day_steps() -> None:
    clock = GameClock()

    try:
        clock.step(days=0)
    except ValueError:
        return

    raise AssertionError("Expected GameClock.step to reject zero-day steps.")


def test_event_bus_can_unsubscribe() -> None:
    bus = EventBus()
    received: list[Event] = []

    def collect(event: Event) -> None:
        received.append(event)

    bus.subscribe("test.event", collect)
    bus.publish(Event(name="test.event", payload={"value": 1}))
    bus.unsubscribe("test.event", collect)
    bus.publish(Event(name="test.event", payload={"value": 2}))

    assert [event.payload["value"] for event in received] == [1]


def test_event_bus_handles_concurrent_publishers() -> None:
    bus = EventBus()
    received: list[int] = []

    def collect(event: Event) -> None:
        received.append(int(event.payload["value"]))

    def publish_many(offset: int) -> None:
        for value in range(50):
            bus.publish(Event(name="test.concurrent", payload={"value": offset + value}))

    bus.subscribe("test.concurrent", collect)
    threads = [Thread(target=publish_many, args=(index * 100,)) for index in range(4)]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    assert len(received) == 200


def test_engine_tick_processes_property_game_without_extra_industries() -> None:
    state = GameState(world_id="engine", world_name="Engine")
    engine = GameEngine(state=state)
    engine.gameplay.ensure_starting_company(state)
    engine.gameplay.buy_property(state)

    engine.set_speed(GameSpeed.ONE_X)
    snapshot = engine.tick()
    for _ in range(30):
        snapshot = engine.tick()

    assert snapshot.tick_count == 31
    assert snapshot.registered_industries == ("property",)
    assert state.metadata["last_revenue"] > 0
    assert state.news_feed.recent(1)


def test_save_manager_round_trips_multiple_worlds() -> None:
    with TemporaryDirectory() as directory:
        manager = SaveManager(save_root=Path(directory))
        first = GameState(world_id="alpha", world_name="Alpha")
        second = GameState(world_id="beta", world_name="Beta")
        first.clock.set_speed(GameSpeed.ONE_X)
        first.advance_days(3)

        first_path = manager.save_world(first, slot_name="start")
        second_path = manager.save_world(second, slot_name="start")

        loaded = manager.load_world("alpha", slot_name="start")
        assert first_path.exists()
        assert second_path.exists()
        assert manager.list_worlds() == ("alpha", "beta")
        assert loaded.world_name == "Alpha"
        assert loaded.clock.current_date.isoformat() == "2026-01-04"
        assert loaded.save_version == 2
