from __future__ import annotations

from word_chain.words import random_next_word


def test_random_next_word_hard_prefers_fewest_followups():
    word_set = {"bat", "bee"}
    counts = {"t": 1, "e": 100}  # 'bat' ends in a rare letter, 'bee' in a common one
    word = random_next_word("b", word_set, set(), difficulty="hard", letter_counts=counts)
    assert word == "bat"


def test_random_next_word_easy_prefers_most_followups():
    word_set = {"bat", "bee"}
    counts = {"t": 1, "e": 100}
    word = random_next_word("b", word_set, set(), difficulty="easy", letter_counts=counts)
    assert word == "bee"


def test_random_next_word_returns_none_when_no_candidates():
    word_set = {"bat", "bee"}
    assert random_next_word("z", word_set, set()) is None
