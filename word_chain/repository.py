from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path

from .models import GameResult


class GameRepository(ABC):
    """Storage abstraction so the backend (JSON file today, a real DB later)
    can be swapped without touching service/business logic."""

    @abstractmethod
    def save(self, result: GameResult) -> None: ...

    @abstractmethod
    def list(self) -> list[GameResult]: ...


class JsonGameRepository(GameRepository):
    def __init__(self, file_path: Path):
        self.file_path = file_path

    def save(self, result: GameResult) -> None:
        results = self.list()
        results.append(result)
        self._save(results)

    def list(self) -> list[GameResult]:
        if not self.file_path.exists():
            return []
        raw = json.loads(self.file_path.read_text())
        return [GameResult.from_dict(item) for item in raw]

    def _save(self, results: list[GameResult]) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.file_path.write_text(json.dumps([r.to_dict() for r in results], indent=2))
