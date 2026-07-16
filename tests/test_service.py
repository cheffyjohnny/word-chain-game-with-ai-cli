from __future__ import annotations

import pytest

from word_chain.ai_client import AiClient, AiMove
from word_chain.models import GameResult
from word_chain.repository import GameRepository
from word_chain.service import GameService

SMALL_WORD_SET = {"apple", "elephant", "tiger", "rat", "tomato", "orange"}


class InMemoryGameRepository(GameRepository):
    def __init__(self):
        self._results: list[GameResult] = []

    def save(self, result: GameResult) -> None:
        self._results.append(result)

    def list(self) -> list[GameResult]:
        return list(self._results)


class ScriptedAiClient(AiClient):
    """Returns pre-scripted moves in order, so AI-turn tests are deterministic."""

    def __init__(self, moves: list[AiMove]):
        self._moves = list(moves)

    def pick_word(self, last_letter: str, used_words: set[str]) -> AiMove:
        return self._moves.pop(0)


@pytest.fixture
def repo() -> InMemoryGameRepository:
    return InMemoryGameRepository()


@pytest.fixture
def service(repo: InMemoryGameRepository) -> GameService:
    ai_client = ScriptedAiClient([AiMove(word="elephant", source="offline")])
    return GameService(ai_client, repo, SMALL_WORD_SET)


def test_validate_accepts_valid_word(service: GameService):
    assert service.validate_human_word("apple", None, set()) is None


def test_validate_rejects_wrong_starting_letter(service: GameService):
    error = service.validate_human_word("tiger", "a", set())
    assert error is not None
    assert "start with" in error


def test_validate_rejects_reused_word(service: GameService):
    error = service.validate_human_word("apple", None, {"apple"})
    assert error is not None
    assert "already been used" in error


def test_validate_rejects_unknown_word(service: GameService):
    error = service.validate_human_word("xyzzy", None, set())
    assert error is not None
    assert "dictionary" in error


def test_ai_turn_returns_scripted_move(service: GameService):
    move = service.ai_turn("e", set())
    assert move.word == "elephant"
    assert move.source == "offline"


def test_record_game_saves_to_repository(service: GameService, repo: InMemoryGameRepository):
    service.record_game(["apple", "elephant"], winner="human", ai_mode="offline")
    results = repo.list()
    assert len(results) == 1
    assert results[0].winner == "human"
    assert results[0].chain == ["apple", "elephant"]
