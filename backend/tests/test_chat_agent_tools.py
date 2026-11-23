import pytest

from chat_agent.tools import ToolBox, public_item
from conftest import make_item


@pytest.fixture
def box(db):
    return ToolBox(db, user_id="user-1")


# ── public_item: the privacy whitelist ────────────────────────────────────────

def test_public_item_never_exposes_contact_or_internal_fields():
    item = make_item(image_features=[0.1], text_embedding=[0.2])
    safe = public_item(item)
    for secret in ("contact_info", "user_id", "image_features", "text_embedding", "latitude"):
        assert secret not in safe
    assert safe["title"] == "Black leather wallet"


def test_public_item_truncates_long_descriptions():
    assert len(public_item(make_item(description="x" * 900))["description"]) == 300


# ── search_items ──────────────────────────────────────────────────────────────

def test_search_ranks_relevant_items_first_and_skips_irrelevant(box, db):
    db.get_all_items.return_value = [
        make_item(item_id="umbrella", title="Red umbrella", description="folding umbrella",
                  category="other", location="Station"),
        make_item(item_id="wallet", title="Black leather wallet", item_type="found"),
        make_item(item_id="blue", title="Blue wallet", description="cloth", item_type="found"),
    ]
    out = box.search_items("black wallet", item_type="found")
    ids = [r["item_id"] for r in out["results"]]
    assert ids[0] == "wallet"
    assert "umbrella" not in ids
    assert out["results"][0]["relevance"] > out["results"][-1]["relevance"]


def test_search_passes_filters_to_the_database(box, db):
    db.get_all_items.return_value = []
    box.search_items("black wallet", item_type="FOUND")
    db.get_all_items.assert_called_once_with(item_type="found", status="active", limit=300)


def test_search_filters_by_category(box, db):
    db.get_all_items.return_value = [
        make_item(item_id="a", category="wallet"),
        make_item(item_id="b", category="bag", title="Black leather bag"),
    ]
    out = box.search_items("black leather", category="bag")
    assert [r["item_id"] for r in out["results"]] == ["b"]


def test_search_results_contain_no_contact_info(box, db):
    db.get_all_items.return_value = [make_item()]
    out = box.search_items("black wallet")
    assert "owner@example.com" not in str(out)
    assert "98450" not in str(out)


@pytest.mark.parametrize("kwargs", [
    {"query": "wallet", "item_type": "stolen"},
    {"query": "wallet", "category": "spaceship"},
    {"query": "the a an"},          # only stopwords -> nothing to search
])
def test_search_rejects_bad_input(box, db, kwargs):
    assert "error" in box.search_items(**kwargs)
    db.get_all_items.assert_not_called()


def test_search_limit_is_clamped(box, db):
    db.get_all_items.return_value = [make_item(item_id=str(n)) for n in range(30)]
    assert box.search_items("black wallet", limit=999)["count"] == 10
    assert box.search_items("black wallet", limit=0)["count"] == 1
    assert box.search_items("black wallet", limit="abc")["count"] == 5


# ── get_my_items ──────────────────────────────────────────────────────────────

def test_get_my_items_requires_sign_in(db):
    assert "error" in ToolBox(db, user_id=None).get_my_items()


def test_get_my_items_returns_only_the_users_items(box, db):
    db.get_all_items.return_value = [
        make_item(item_id="mine", user_id="user-1"),
        make_item(item_id="theirs", user_id="user-2"),
    ]
    out = box.get_my_items()
    assert [i["item_id"] for i in out["items"]] == ["mine"]
    assert "owner@example.com" not in str(out)


# ── get_item_matches ──────────────────────────────────────────────────────────

def _match(found_id, score):
    return {"match_id": f"m-{found_id}", "lost_item_id": "item-1", "found_item_id": found_id,
            "confidence_score": score}


def test_matches_require_sign_in(db):
    assert "error" in ToolBox(db).get_item_matches("item-1")


def test_matches_refuse_other_users_items(box, db):
    db.get_item.return_value = make_item(user_id="someone-else")
    out = box.get_item_matches("item-1")
    assert "does not belong" in out["error"]
    db.get_matches_for_item.assert_not_called()


def test_matches_for_unknown_item(box, db):
    db.get_item.return_value = None
    assert box.get_item_matches("nope")["error"] == "item not found"


def test_matches_sorted_best_first_with_the_other_item(box, db):
    items = {
        "item-1": make_item(item_id="item-1", user_id="user-1", item_type="lost"),
        "f-low": make_item(item_id="f-low", user_id="u9", item_type="found", title="Brown wallet"),
        "f-high": make_item(item_id="f-high", user_id="u8", item_type="found", title="Black wallet"),
    }
    db.get_item.side_effect = lambda item_id: items.get(item_id)
    db.get_matches_for_item.return_value = [_match("f-low", 0.62), _match("f-high", 0.91)]

    out = box.get_item_matches("item-1")

    assert [m["confidence_percent"] for m in out["matches"]] == [91, 62]
    assert out["matches"][0]["matched_item"]["title"] == "Black wallet"
    assert "owner@example.com" not in str(out)


def test_matches_for_a_found_item_look_up_the_lost_side(box, db):
    items = {
        "item-9": make_item(item_id="item-9", user_id="user-1", item_type="found"),
        "lost-1": make_item(item_id="lost-1", item_type="lost", title="Lost wallet"),
    }
    db.get_item.side_effect = lambda item_id: items.get(item_id)
    db.get_matches_for_item.return_value = [
        {"match_id": "m", "lost_item_id": "lost-1", "found_item_id": "item-9", "confidence_score": 0.8}
    ]
    out = box.get_item_matches("item-9")
    assert out["matches"][0]["matched_item"]["title"] == "Lost wallet"


# ── get_stats ─────────────────────────────────────────────────────────────────

def test_get_stats(box, db):
    db.get_all_items.return_value = [
        make_item(item_type="lost", status="matched"),
        make_item(item_type="found", status="active"),
        make_item(item_type="lost", status="active"),
    ]
    assert box.get_stats() == {"total_items": 3, "lost_items": 2, "found_items": 1, "matched_items": 1}


# ── draft_report ──────────────────────────────────────────────────────────────

GOOD = dict(item_type="Lost", title="Black wallet", category="WALLET",
            description="Black leather wallet with a blue card", location="Gandhipuram")


def test_draft_report_normalises_and_queues_a_ui_action(box):
    out = box.draft_report(**GOOD, reward_amount=500)
    assert out["ok"] is True
    assert out["draft"]["item_type"] == "lost"
    assert out["draft"]["category"] == "wallet"
    assert out["draft"]["reward_amount"] == 500.0
    assert box.actions == [{"type": "prefill_report", "draft": out["draft"]}]


def test_draft_report_ignores_reward_for_found_items(box):
    out = box.draft_report(**{**GOOD, "item_type": "found"}, reward_amount=500)
    assert out["draft"]["reward_amount"] == 0.0


def test_draft_report_never_saves_anything(box, db):
    box.draft_report(**GOOD)
    db.insert_item.assert_not_called()


@pytest.mark.parametrize("override", [
    {"item_type": "stolen"},
    {"category": "spaceship"},
    {"title": "ab"},
    {"description": "too short"},
    {"location": "x"},
])
def test_draft_report_rejects_invalid_details(box, override):
    out = box.draft_report(**{**GOOD, **override})
    assert out["ok"] is False and out["errors"]
    assert box.actions == []


def test_draft_report_bad_reward_defaults_to_zero(box):
    assert box.draft_report(**GOOD, reward_amount="lots")["draft"]["reward_amount"] == 0.0
    assert box.draft_report(**GOOD, reward_amount=-50)["draft"]["reward_amount"] == 0.0


# ── dispatcher ────────────────────────────────────────────────────────────────

def test_run_unknown_tool(box):
    assert "unknown tool" in box.run("delete_everything", {})["error"]


def test_run_rejects_non_object_arguments(box):
    assert "error" in box.run("get_stats", ["not", "a", "dict"])


def test_run_reports_bad_arguments_instead_of_crashing(box):
    assert "bad arguments" in box.run("search_items", {"nonsense": 1})["error"]


def test_run_swallows_unexpected_tool_errors(box, db):
    db.get_all_items.side_effect = RuntimeError("db exploded: secret-connection-string")
    out = box.run("get_stats", {})
    assert out == {"error": "the tool failed unexpectedly"}
