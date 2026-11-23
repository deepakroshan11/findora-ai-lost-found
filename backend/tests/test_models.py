import pytest
from pydantic import ValidationError

from models import (
    ItemCreate,
    UserCreate,
    validate_category,
    validate_item_type,
    validate_status,
)


@pytest.mark.parametrize(
    "category",
    ["wallet", "phone", "keys", "bag", "jewelry", "documents",
     "electronics", "clothing", "accessories", "other"],
)
def test_all_ui_categories_are_valid(category):
    assert validate_category(category)


def test_category_validation_is_case_insensitive():
    assert validate_category("WALLET")
    assert validate_category("Phone")


@pytest.mark.parametrize("bad", ["", "laptop", "wallets", " wallet"])
def test_unknown_categories_are_rejected(bad):
    assert not validate_category(bad)


def test_item_type_only_lost_or_found():
    assert validate_item_type("lost")
    assert validate_item_type("FOUND")
    assert not validate_item_type("stolen")
    assert not validate_item_type("")


def test_status_values():
    for ok in ("active", "matched", "closed"):
        assert validate_status(ok)
    assert not validate_status("deleted")


def test_item_create_accepts_valid_payload():
    item = ItemCreate(
        title="Black wallet",
        description="Black leather wallet with a blue card",
        category="wallet",
        location="Bus stand",
        item_type="lost",
        contact_info="me@example.com",
    )
    assert item.reward_amount == 0.0
    assert item.latitude is None


def test_item_create_rejects_short_description():
    with pytest.raises(ValidationError):
        ItemCreate(
            title="Black wallet",
            description="too short",
            category="wallet",
            location="Bus stand",
            item_type="lost",
            contact_info="me@example.com",
        )


def test_user_create_requires_valid_email():
    with pytest.raises(ValidationError):
        UserCreate(email="not-an-email", name="Deepak")
    assert UserCreate(email="deepak@example.com", name="Deepak").name == "Deepak"
