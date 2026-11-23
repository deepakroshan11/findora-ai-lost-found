"""
Confidence scoring in ai/engine.py.

The engine object is created with __new__ so no model is loaded (no TensorFlow,
no sentence-transformers) and the feature extractors are replaced with stubs.
"""
import numpy as np
import pytest

from ai.engine import ProductionAIEngine


@pytest.fixture
def engine():
    eng = ProductionAIEngine.__new__(ProductionAIEngine)
    eng.extract_image_features = lambda path: None
    eng.extract_text_embedding = lambda text: None
    return eng


def item(**kw):
    base = {"category": "wallet", "title": "wallet", "description": "black"}
    base.update(kw)
    return base


# ── location_score ────────────────────────────────────────────────────────────

def test_location_score_missing_coordinates_is_neutral(engine):
    assert engine.location_score(None, None, 11.0, 76.9) == 0.5


def test_location_score_same_point_is_one(engine):
    assert engine.location_score(11.0183, 76.9725, 11.0183, 76.9725) == pytest.approx(1.0)


def test_location_score_beyond_max_distance_is_zero(engine):
    # Coimbatore -> Chennai is hundreds of km
    assert engine.location_score(11.0183, 76.9725, 13.0827, 80.2707) == 0.0


def test_location_score_decreases_with_distance(engine):
    near = engine.location_score(11.0183, 76.9725, 11.0283, 76.9725)
    far = engine.location_score(11.0183, 76.9725, 11.0883, 76.9725)
    assert 0.0 < far < near < 1.0


# ── match_items ───────────────────────────────────────────────────────────────

def test_identical_embeddings_and_features_score_high(engine):
    vec = [0.1, 0.9, 0.3, 0.5]
    a = item(image_features=vec, text_embedding=vec)
    b = item(image_features=vec, text_embedding=vec)
    result = engine.match_items(a, b)
    assert result["image_similarity"] == pytest.approx(1.0, abs=1e-3)
    assert result["text_similarity"] == pytest.approx(1.0, abs=1e-3)
    assert result["is_match"] is True
    assert result["confidence_score"] >= 0.8


def test_formula_weights(engine):
    """confidence = 0.40*image + 0.35*text + 0.15*location + 0.10*time + category.

    Text-only here (image similarity 0) so the result stays below the 0.95 cap.
    Missing coordinates give location 0.5, missing timestamps give time 0.7,
    and a matching category adds +0.10.
    """
    vec = [1.0, 0.0]
    a = item(text_embedding=vec)
    b = item(text_embedding=vec)
    r = engine.match_items(a, b)
    expected = 0.35 * 1.0 + 0.15 * 0.5 + 0.10 * 0.7 + 0.10
    assert r["confidence_score"] == pytest.approx(expected, abs=1e-3)


def test_confidence_is_capped_at_095(engine):
    vec = [1.0, 0.0]
    a = item(image_features=vec, text_embedding=vec, latitude=11.0, longitude=76.9)
    b = item(image_features=vec, text_embedding=vec, latitude=11.0, longitude=76.9,
             created_at=None)
    a["created_at"] = b["created_at"] = "2026-11-23T10:00:00"
    r = engine.match_items(a, b)
    assert r["confidence_score"] <= 0.95


def test_category_bonus_and_penalty(engine):
    """Same category adds +0.10, a different category subtracts 0.05 (a 0.15 swing)."""
    vec = [1.0, 0.0]
    same = engine.match_items(
        item(text_embedding=vec),
        item(text_embedding=vec),
    )
    diff = engine.match_items(
        item(text_embedding=vec),
        item(text_embedding=vec, category="keys"),
    )
    assert diff["confidence_score"] == pytest.approx(same["confidence_score"] - 0.15, abs=1e-3)


def test_no_features_gives_low_confidence_and_no_match(engine):
    r = engine.match_items(item(), item(category="keys"))
    assert r["image_similarity"] == 0.0
    assert r["text_similarity"] == 0.0
    assert r["is_match"] is False


def test_temporal_score_decays_with_days_apart(engine):
    vec = [1.0, 0.0]
    a = item(image_features=vec, text_embedding=vec, created_at="2026-11-01T00:00:00")
    same_day = item(image_features=vec, text_embedding=vec, created_at="2026-11-01T00:00:00")
    month_later = item(image_features=vec, text_embedding=vec, created_at="2026-12-01T00:00:00")
    assert engine.match_items(a, same_day)["temporal_score"] == pytest.approx(1.0)
    assert engine.match_items(a, month_later)["temporal_score"] == pytest.approx(np.exp(-1), abs=1e-3)


def test_threshold_controls_is_match(engine):
    vec = [1.0, 0.0]
    a = item(image_features=vec, text_embedding=vec)
    b = item(image_features=vec, text_embedding=vec)
    assert engine.match_items(a, b, threshold=0.5)["is_match"] is True
    assert engine.match_items(a, b, threshold=0.99)["is_match"] is False
