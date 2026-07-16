from __future__ import annotations

import json

import pytest
from click.testing import CliRunner

from word_chain import service as service_module
from word_chain.ai_client import AiMove
from word_chain.cli import cli


@pytest.fixture(autouse=True)
def no_gemini_key(monkeypatch):
    # Keep tests hermetic regardless of a real GEMINI_API_KEY in the dev's .env.
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)


@pytest.fixture(autouse=True)
def fixed_start_word(monkeypatch):
    # "cat" -> required first letter is always 't', so test input is deterministic.
    monkeypatch.setattr(service_module.GameService, "start_word", lambda self: "cat")


def _history(data_file) -> list[dict]:
    return json.loads(data_file.read_text())


def test_quit_records_incomplete(tmp_path):
    data_file = tmp_path / "history.json"
    result = CliRunner().invoke(cli, ["--data-file", str(data_file), "play"], input="quit\n")

    assert "Game ended early" in result.output
    assert _history(data_file)[0]["winner"] == "incomplete"


def test_invalid_word_loses_game(tmp_path):
    data_file = tmp_path / "history.json"
    # "dog" doesn't start with 't', the required letter after "cat".
    result = CliRunner().invoke(cli, ["--data-file", str(data_file), "play"], input="dog\n")

    assert "you lose!" in result.output
    assert _history(data_file)[0]["winner"] == "ai"


def test_ai_stuck_wins_game(tmp_path, monkeypatch):
    data_file = tmp_path / "history.json"
    monkeypatch.setattr(
        "word_chain.cli.build_ai_client",
        lambda word_set, difficulty: _StuckAiClient(),
    )

    result = CliRunner().invoke(cli, ["--data-file", str(data_file), "play"], input="top\n")

    assert "you win!" in result.output
    assert _history(data_file)[0]["winner"] == "human"


class _StuckAiClient:
    """Always reports no valid move, so the human wins immediately."""

    def pick_word(self, last_letter: str, used_words: set[str]) -> AiMove:
        return AiMove(word=None, source="offline")
