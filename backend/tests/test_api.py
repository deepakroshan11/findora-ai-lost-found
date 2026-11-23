"""HTTP-level tests with FastAPI's TestClient and a stubbed database."""
import pytest
from fastapi.testclient import TestClient

import main
from conftest import make_item

client = TestClient(main.app)

FORM = {
    "title": "Black leather wallet",
    "description": "Black leather wallet with tan stitching",
    "category": "wallet",
    "location": "Gandhipuram Bus Stand",
    "item_type": "lost",
    "contact_info": "owner@example.com",
    "user_id": "user-1",
}
IMAGE = {"image": ("wallet.jpg", b"\xff\xd8\xff\xe0fakejpeg", "image/jpeg")}


def test_ping():
    r = client.get("/ping")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


def test_report_rejects_unknown_category(db):
    r = client.post("/api/items/report", data={**FORM, "category": "spaceship"}, files=IMAGE)
    assert r.status_code == 400
    assert r.json()["detail"] == "Invalid category"
    db.insert_item.assert_not_called()


def test_report_rejects_unknown_item_type(db):
    r = client.post("/api/items/report", data={**FORM, "item_type": "stolen"}, files=IMAGE)
    assert r.status_code == 400
    assert r.json()["detail"] == "Invalid item type"
    db.insert_item.assert_not_called()


def test_report_requires_a_photo(db):
    r = client.post("/api/items/report", data=FORM)
    assert r.status_code == 422
    db.insert_item.assert_not_called()


def test_report_success_stores_item_and_queues_matching(db, monkeypatch):
    monkeypatch.setattr(main, "save_image", lambda file, item_id: "https://cdn.example/w.jpg")
    queued = []

    async def fake_fast(item_id):
        queued.append(("fast", item_id))

    async def fake_ai(item_id):
        queued.append(("ai", item_id))

    monkeypatch.setattr(main, "trigger_fast_matching", fake_fast)
    monkeypatch.setattr(main, "trigger_ai_processing", fake_ai)
    db.insert_item.return_value = True

    r = client.post("/api/items/report", data=FORM, files=IMAGE)

    assert r.status_code == 200
    body = r.json()
    assert body["title"] == "Black leather wallet"
    assert body["image_path"] == "https://cdn.example/w.jpg"
    assert body["status"] == "active"
    db.insert_item.assert_called_once()
    assert {kind for kind, _ in queued} == {"fast", "ai"}


def test_report_returns_500_when_db_insert_fails(db, monkeypatch):
    monkeypatch.setattr(main, "save_image", lambda file, item_id: "https://cdn.example/w.jpg")
    db.insert_item.return_value = False
    r = client.post("/api/items/report", data=FORM, files=IMAGE)
    assert r.status_code == 500


def test_list_items_filters_by_category(db):
    db.get_all_items.return_value = [
        make_item(item_id="1", category="wallet"),
        make_item(item_id="2", category="bag"),
    ]
    r = client.get("/api/items", params={"category": "bag"})
    assert r.status_code == 200
    assert [i["item_id"] for i in r.json()] == ["2"]


def test_list_items_strips_ml_fields(db):
    db.get_all_items.return_value = [
        make_item(image_features=[0.1, 0.2], text_embedding=[0.3, 0.4])
    ]
    body = client.get("/api/items").json()[0]
    assert "image_features" not in body
    assert "text_embedding" not in body


def test_get_item_404(db):
    db.get_item.return_value = None
    assert client.get("/api/items/nope").status_code == 404


def test_get_item_found(db):
    db.get_item.return_value = make_item(item_id="abc")
    r = client.get("/api/items/abc")
    assert r.status_code == 200
    assert r.json()["item_id"] == "abc"


def test_matches_sorted_by_confidence_desc(db):
    def match(mid, score):
        return {
            "match_id": mid, "lost_item_id": "l", "found_item_id": "f",
            "confidence_score": score, "image_similarity": 0.5,
            "text_similarity": 0.5, "location_score": 0.5, "status": "pending",
            "created_at": "2026-11-23T10:00:00", "updated_at": "2026-11-23T10:00:00",
        }
    db.get_matches_for_item.return_value = [match("a", 0.62), match("b", 0.91), match("c", 0.75)]
    r = client.get("/api/matches/l")
    assert [m["match_id"] for m in r.json()] == ["b", "c", "a"]


def test_stats_counts(db):
    db.get_all_items.return_value = [
        make_item(item_type="lost", status="active"),
        make_item(item_type="lost", status="matched"),
        make_item(item_type="found", status="matched"),
    ]
    assert client.get("/api/stats").json() == {
        "total_items": 3, "lost_items": 2, "found_items": 1, "matched_items": 2,
    }


def test_stats_returns_500_on_db_error(db):
    db.get_all_items.side_effect = RuntimeError("db down")
    assert client.get("/api/stats").status_code == 500
