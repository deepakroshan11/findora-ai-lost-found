"""
Shared test setup for the Findora backend.

Tests run fully offline:
  * `database` is replaced by a stub so no Supabase/PostgreSQL connection is made
    (the real module connects at import time and raises without DATABASE_URL).
  * No email provider key is set, so nothing is ever sent.
  * The AI engine is never instantiated, so TensorFlow / sentence-transformers
    are not needed to run the tests.
"""
import os
import sys
import types
from unittest.mock import MagicMock

import pytest

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

os.environ.pop("BREVO_API_KEY", None)
os.environ.pop("DATABASE_URL", None)

_fake_database = types.ModuleType("database")
_fake_database.db = MagicMock(name="db")
sys.modules["database"] = _fake_database


@pytest.fixture
def db():
    """The stubbed database object, reset between tests."""
    mock = sys.modules["database"].db
    mock.reset_mock(return_value=True, side_effect=True)
    return mock


def make_item(**overrides):
    """A complete, valid item row as the API/DB layer returns it."""
    item = {
        "item_id": "item-1",
        "user_id": "user-1",
        "title": "Black leather wallet",
        "description": "Black leather wallet with tan stitching and a silver plate",
        "category": "wallet",
        "location": "Gandhipuram Bus Stand, Coimbatore",
        "latitude": None,
        "longitude": None,
        "item_type": "lost",
        "reward_amount": 0.0,
        "contact_info": "owner@example.com | +91 98450 12367",
        "image_path": "https://res.cloudinary.com/demo/image/upload/wallet.jpg",
        "status": "active",
        "created_at": "2026-11-23T10:00:00",
        "updated_at": "2026-11-23T10:00:00",
    }
    item.update(overrides)
    return item
