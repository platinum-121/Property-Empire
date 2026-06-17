# core/events.py
# © Copyright 2026 Sam [Platinum]

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from threading import RLock
from typing import Any


@dataclass(frozen=True, slots=True)
class Event:
    name: str
    payload: dict[str, Any] = field(default_factory=dict)


EventCallback = Callable[[Event], None]


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[EventCallback]] = defaultdict(list)
        self._lock = RLock()

    def subscribe(self, event_name: str, callback: EventCallback) -> None:
        with self._lock:
            if callback not in self._subscribers[event_name]:
                self._subscribers[event_name].append(callback)

    def unsubscribe(self, event_name: str, callback: EventCallback) -> None:
        with self._lock:
            callbacks = self._subscribers.get(event_name)
            if callbacks is None:
                return

            if callback in callbacks:
                callbacks.remove(callback)

            if not callbacks:
                self._subscribers.pop(event_name, None)

    def publish(self, event: Event) -> None:
        with self._lock:
            callbacks = tuple(self._subscribers.get(event.name, ()))

        for callback in callbacks:
            callback(event)
