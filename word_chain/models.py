from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class GameResult:
    id: str
    date: str
    winner: str
    chain: list[str] = field(default_factory=list)
    ai_mode: str = "offline"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "date": self.date,
            "winner": self.winner,
            "chain": self.chain,
            "ai_mode": self.ai_mode,
        }

    @staticmethod
    def from_dict(data: dict) -> "GameResult":
        return GameResult(
            id=data["id"],
            date=data["date"],
            winner=data["winner"],
            chain=data.get("chain", []),
            ai_mode=data.get("ai_mode", "offline"),
        )
