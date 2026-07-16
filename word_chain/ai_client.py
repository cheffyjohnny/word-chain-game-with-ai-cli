from __future__ import annotations

import json
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass

import requests

from .words import build_letter_start_counts, is_valid_word, random_next_word

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

# Primary -> fallback order. 2.5-flash is high-demand; 2.0-flash / 1.5-flash are stable.
MODELS = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-2.5-flash"]

DIFFICULTY_PROMPTS = {
    "easy": (
        " Play cooperatively: prefer a word ending in a common letter "
        "(a vowel, or n/r/s/t) so your opponent has an easy follow-up."
    ),
    "normal": "",
    "hard": (
        " Play strategically to win: prefer a word ending in an uncommon "
        "letter (like x, q, z, u, v, or j) to make your opponent's next "
        "move as hard as possible."
    ),
}


@dataclass
class AiMove:
    word: str | None
    source: str  # "gemini" | "offline"


class AiClient(ABC):
    """Abstraction so the AI opponent's brain (Gemini today, offline word-list
    fallback, or a scripted stub for tests) can be swapped without touching
    game logic."""

    @abstractmethod
    def pick_word(self, last_letter: str, used_words: set[str]) -> AiMove: ...


class OfflineAiClient(AiClient):
    def __init__(self, word_set: set[str], difficulty: str = "normal"):
        self.word_set = word_set
        self.difficulty = difficulty
        self.letter_counts = build_letter_start_counts(word_set)

    def pick_word(self, last_letter: str, used_words: set[str]) -> AiMove:
        word = random_next_word(last_letter, self.word_set, used_words, self.difficulty, self.letter_counts)
        return AiMove(word=word, source="offline")


class GeminiAiClient(AiClient):
    """Real AI opponent. Falls back to the offline word list if every model
    attempt fails, so a network hiccup doesn't end the game outright."""

    def __init__(self, api_key: str, word_set: set[str], difficulty: str = "normal"):
        self.api_key = api_key
        self.word_set = word_set
        self.difficulty = difficulty
        self._offline = OfflineAiClient(word_set, difficulty)

    def pick_word(self, last_letter: str, used_words: set[str]) -> AiMove:
        word = self._call_gemini(last_letter, used_words)
        if word:
            return AiMove(word=word, source="gemini")
        return self._offline.pick_word(last_letter, used_words)

    def _call_gemini(self, last_letter: str, used_words: set[str]) -> str | None:
        strategy_hint = DIFFICULTY_PROMPTS.get(self.difficulty, "")
        prompt = (
            "We are playing a word chain game. Reply with a single common English "
            f'word that starts with the letter "{last_letter}" and is NOT one of '
            f"these already-used words: {', '.join(sorted(used_words)) or '(none yet)'}."
            f"{strategy_hint} "
            'Respond with JSON only, no other text: {"word": "yourword"}'
        )

        for model in MODELS:
            for attempt in range(2):
                try:
                    res = requests.post(
                        f"{GEMINI_BASE}/{model}:generateContent",
                        params={"key": self.api_key},
                        json={
                            "contents": [{"parts": [{"text": prompt}]}],
                            "generationConfig": {
                                "temperature": 0.7,
                                "responseMimeType": "application/json",
                            },
                        },
                        timeout=10,
                    )
                except requests.RequestException:
                    return None

                if res.status_code == 503:
                    if attempt == 0:
                        time.sleep(1.5)
                        continue
                    break

                if not res.ok:
                    break

                try:
                    data = res.json()
                    raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                    word = json.loads(raw_text).get("word", "").strip().lower()
                except (KeyError, IndexError, ValueError):
                    break

                if (
                    word
                    and word[0] == last_letter.lower()
                    and word not in used_words
                    and is_valid_word(word, self.word_set)
                ):
                    return word
                break  # model returned an invalid word, try the next model

        return None


def build_ai_client(word_set: set[str], difficulty: str = "normal") -> AiClient:
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        return GeminiAiClient(api_key, word_set, difficulty)
    return OfflineAiClient(word_set, difficulty)
