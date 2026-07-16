from __future__ import annotations

import random
from collections import Counter
from pathlib import Path

DEFAULT_WORDLIST_PATH = Path(__file__).resolve().parent / "data" / "words.txt"

DIFFICULTIES = ("easy", "normal", "hard")


def load_word_set(path: Path = DEFAULT_WORDLIST_PATH) -> set[str]:
    return set(path.read_text().split())


def is_valid_word(word: str, word_set: set[str]) -> bool:
    return word.lower() in word_set


def build_letter_start_counts(word_set: set[str]) -> dict[str, int]:
    """How many words in the set start with each letter — used as a rough
    stand-in for "how many words could follow if the chain ended here"."""
    return dict(Counter(w[0] for w in word_set))


def random_next_word(
    letter: str,
    word_set: set[str],
    used: set[str],
    difficulty: str = "normal",
    letter_counts: dict[str, int] | None = None,
) -> str | None:
    letter = letter.lower()
    candidates = [w for w in word_set if w[0] == letter and w not in used]
    if not candidates:
        return None

    if difficulty == "normal" or not letter_counts:
        return random.choice(candidates)

    scored = [(w, letter_counts.get(w[-1], 0)) for w in candidates]
    target_score = min(s for _, s in scored) if difficulty == "hard" else max(s for _, s in scored)
    best = [w for w, s in scored if s == target_score]
    return random.choice(best)
