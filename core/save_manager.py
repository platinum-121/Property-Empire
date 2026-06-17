# core/save_manager.py
# © Copyright 2026 Sam [Platinum]

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.state import CURRENT_SAVE_VERSION, GameState


@dataclass(frozen=True, slots=True)
class SaveInfo:
    world_id: str
    slot_name: str
    path: Path
    save_version: int
    saved_at: str


class SaveManager:
    def __init__(self, save_root: Path | str = "saves") -> None:
        self.save_root = Path(save_root)

    def save_world(self, state: GameState, slot_name: str = "autosave") -> Path:
        world_dir = self._world_directory(state.world_id)
        world_dir.mkdir(parents=True, exist_ok=True)

        path = world_dir / f"{self._safe_name(slot_name)}.json"
        payload = {
            "schema": "corp-sim-save",
            "save_version": CURRENT_SAVE_VERSION,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "game_state": state.to_dict(),
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path

    def load_world(self, world_id: str, slot_name: str = "autosave") -> GameState:
        path = self._world_directory(world_id) / f"{self._safe_name(slot_name)}.json"
        payload = self._read_payload(path)
        return self._state_from_payload(payload)

    def list_worlds(self) -> tuple[str, ...]:
        if not self.save_root.exists():
            return ()

        return tuple(
            path.name
            for path in sorted(self.save_root.iterdir())
            if path.is_dir()
        )

    def list_saves(self, world_id: str) -> tuple[SaveInfo, ...]:
        world_dir = self._world_directory(world_id)
        if not world_dir.exists():
            return ()

        saves: list[SaveInfo] = []
        for path in sorted(world_dir.glob("*.json")):
            payload = self._read_payload(path)
            saves.append(
                SaveInfo(
                    world_id=world_id,
                    slot_name=path.stem,
                    path=path,
                    save_version=int(payload["save_version"]),
                    saved_at=str(payload["saved_at"]),
                )
            )
        return tuple(saves)

    def _state_from_payload(self, payload: dict[str, Any]) -> GameState:
        version = int(payload["save_version"])
        if version > CURRENT_SAVE_VERSION:
            raise ValueError(f"Unsupported save version: {version}")

        return GameState.from_dict(payload["game_state"])

    def _read_payload(self, path: Path) -> dict[str, Any]:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)

        if payload.get("schema") != "corp-sim-save":
            raise ValueError(f"Not a Corp Sim save file: {path}")

        return dict(payload)

    def _world_directory(self, world_id: str) -> Path:
        return self.save_root / self._safe_name(world_id)

    def _safe_name(self, value: str) -> str:
        allowed = ("-", "_")
        safe = "".join(character for character in value if character.isalnum() or character in allowed)
        if not safe:
            raise ValueError("Save names must contain at least one letter or number.")

        return safe
