"""The fast keyword matcher that runs immediately after every submission."""
import pytest

from main import _keyword_match_score, _keywords


def test_keywords_lowercases_and_strips_punctuation():
    assert _keywords("Black, LEATHER wallet!") == {"black", "leather", "wallet"}


def test_keywords_drops_stopwords_and_one_letter_words():
    words = _keywords("The lost item was found with a wallet")
    assert words == {"wallet"}


def test_keywords_empty_text():
    assert _keywords("") == set()


def test_exact_title_match_scores_092_regardless_of_case_and_spacing():
    a = {"title": "Black Wallet", "description": "x", "category": "wallet"}
    b = {"title": "  black wallet ", "description": "totally different", "category": "bag"}
    assert _keyword_match_score(a, b) == 0.92


def test_similar_items_score_high_but_capped_at_090():
    a = {
        "title": "Black leather wallet",
        "description": "tan stitching silver plate blue card",
        "category": "wallet",
    }
    b = {
        "title": "Black leather wallet found",
        "description": "tan stitching silver plate blue card near bus stand",
        "category": "wallet",
    }
    score = _keyword_match_score(a, b)
    assert 0.6 < score <= 0.90


def test_unrelated_items_score_low():
    a = {"title": "Red umbrella", "description": "folding umbrella", "category": "other"}
    b = {"title": "Silver ring", "description": "wedding band", "category": "jewelry"}
    assert _keyword_match_score(a, b) < 0.2


def test_same_category_adds_bonus():
    base = {"title": "Blue bag", "description": "canvas strap"}
    same = _keyword_match_score({**base, "category": "bag"}, {**base, "title": "Green bag", "category": "bag"})
    diff = _keyword_match_score({**base, "category": "bag"}, {**base, "title": "Green bag", "category": "keys"})
    assert same == pytest.approx(diff + 0.10)


def test_score_always_between_0_and_1():
    a = {"title": "x", "description": "", "category": "a"}
    b = {"title": "y", "description": "", "category": "b"}
    assert 0.0 <= _keyword_match_score(a, b) <= 1.0
