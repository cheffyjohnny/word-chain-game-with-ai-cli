from __future__ import annotations

import random
from pathlib import Path

DEFAULT_WORDLIST_PATH = Path(__file__).resolve().parent / "data" / "words.txt"


def load_word_set(path: Path = DEFAULT_WORDLIST_PATH) -> set[str]:
    return set(path.read_text().split())


def is_valid_word(word: str, word_set: set[str]) -> bool:
    return word.lower() in word_set


def random_next_word(letter: str, word_set: set[str], used: set[str]) -> str | None:
    letter = letter.lower()
    candidates = [w for w in word_set if w[0] == letter and w not in used]
    return random.choice(candidates) if candidates else None
