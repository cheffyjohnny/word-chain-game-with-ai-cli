from __future__ import annotations

import json
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass

import requests

from .words import random_next_word

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

# Primary -> fallback order. 2.5-flash is high-demand; 2.0-flash / 1.5-flash are stable.
MODELS = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-2.5-flash"]


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
    def __init__(self, word_set: set[str]):
        self.word_set = word_set

    def pick_word(self, last_letter: str, used_words: set[str]) -> AiMove:
        word = random_next_word(last_letter, self.word_set, used_words)
        return AiMove(word=word, source="offline")


class GeminiAiClient(AiClient):
    """Real AI opponent. Falls back to the offline word list if every model
    attempt fails, so a network hiccup doesn't end the game outright."""

    def __init__(self, api_key: str, word_set: set[str]):
        self.api_key = api_key
        self._offline = OfflineAiClient(word_set)

    def pick_word(self, last_letter: str, used_words: set[str]) -> AiMove:
        word = self._call_gemini(last_letter, used_words)
        if word:
            return AiMove(word=word, source="gemini")
        return self._offline.pick_word(last_letter, used_words)

    def _call_gemini(self, last_letter: str, used_words: set[str]) -> str | None:
        prompt = (
            "We are playing a word chain game. Reply with a single common English "
            f'word that starts with the letter "{last_letter}" and is NOT one of '
            f"these already-used words: {', '.join(sorted(used_words)) or '(none yet)'}. "
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

                if word and word[0] == last_letter.lower() and word not in used_words:
                    return word
                break  # model returned an invalid word, try the next model

        return None


def build_ai_client(word_set: set[str]) -> AiClient:
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        return GeminiAiClient(api_key, word_set)
    return OfflineAiClient(word_set)
