from __future__ import annotations

import random
import uuid
from datetime import datetime

from .ai_client import AiClient, AiMove
from .models import GameResult
from .repository import GameRepository
from .words import is_valid_word

# How many correct answers the human needs to win outright, by difficulty.
WIN_TARGETS = {"easy": 20, "normal": 50, "hard": 100}


class GameService:
    def __init__(self, ai_client: AiClient, repo: GameRepository, word_set: set[str]):
        self.ai_client = ai_client
        self.repo = repo
        self.word_set = word_set

    def start_word(self) -> str:
        return random.choice(list(self.word_set))

    def validate_human_word(self, word: str, last_letter: str | None, used: set[str]) -> str | None:
        w = word.strip().lower()
        if not w.isalpha():
            return "Word must contain only letters."
        if last_letter and (not w or w[0] != last_letter.lower()):
            return f"Word must start with '{last_letter.upper()}'."
        if w in used:
            return "That word has already been used."
        if not is_valid_word(w, self.word_set):
            return f"'{w}' isn't in the dictionary."
        return None

    def ai_turn(self, last_letter: str, used: set[str]) -> AiMove:
        return self.ai_client.pick_word(last_letter, used)

    def record_game(self, chain: list[str], winner: str, ai_mode: str) -> GameResult:
        result = GameResult(
            id=str(uuid.uuid4()),
            date=datetime.now().isoformat(timespec="seconds"),
            winner=winner,
            chain=chain,
            ai_mode=ai_mode,
        )
        self.repo.save(result)
        return result

    def list_history(self) -> list[GameResult]:
        return self.repo.list()
