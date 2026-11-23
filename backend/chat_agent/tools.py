"""
Tools the Findora chat agent can call.

Design rules
  * Every tool is READ-ONLY except `draft_report`, which only returns a draft for
    the user to review — nothing is written to the database by the agent.
  * Contact details (email / phone) and ML vectors NEVER leave this module: results
    go through `public_item()`, a whitelist. Contact details are only shared by the
    existing email-alert flow.
  * Item titles/descriptions are written by other users, so the system prompt tells
    the model to treat them as data, not instructions.
"""
import logging
import re

from models import VALID_CATEGORIES, VALID_ITEM_TYPES, validate_category, validate_item_type

log = logging.getLogger("findora.chat_agent")

PUBLIC_FIELDS = (
    "item_id", "title", "description", "category", "location",
    "item_type", "reward_amount", "status", "created_at", "image_path",
)

STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "at", "my", "i", "is", "it",
    "was", "were", "with", "near", "for", "me", "have", "has", "had", "lost", "found",
}


MAX_CARDS = 6              # item cards shown under one assistant reply
GUEST_ERROR = {"error": "sign_in_required: the user is in demo mode and must sign in to use this"}


def public_item(item: dict, reported_by=None) -> dict:
    """Whitelist of fields that are safe to show in chat (no contact info, no user id)."""
    out = {key: item.get(key) for key in PUBLIC_FIELDS}
    out["description"] = (out["description"] or "")[:300]
    out["created_at"] = str(out["created_at"]) if out["created_at"] is not None else None
    if reported_by:
        out["reported_by"] = reported_by
    return out


def model_view(card: dict) -> dict:
    """Compact version of an item for the LLM (saves tokens; the UI gets the full card)."""
    out = {
        "item_id": card.get("item_id"),
        "type": card.get("item_type"),
        "title": card.get("title"),
        "description": (card.get("description") or "")[:160],
        "category": card.get("category"),
        "place": card.get("location"),
        "date": (card.get("created_at") or "")[:10],
        "status": card.get("status"),
    }
    if card.get("reported_by"):
        out["reported_by"] = card["reported_by"]
    if card.get("reward_amount"):
        out["reward"] = card["reward_amount"]
    return out


def short_name(full_name) -> str:
    """'Deepak Roshan A' -> 'Deepak R.' (first name + initial, nothing more)."""
    parts = str(full_name or "").split()
    if not parts:
        return ""
    first = parts[0][:30]
    return f"{first} {parts[1][0].upper()}." if len(parts) > 1 else first


def _stem(token: str) -> str:
    """Tiny plural folding so 'keys' finds 'key' and 'glasses' finds 'glass'."""
    if token.endswith("sses"):
        return token[:-2]
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def _tokens(text) -> list:
    return [_stem(t) for t in re.findall(r"[a-z0-9]+", (text or "").lower())
            if len(t) > 1 and t not in STOPWORDS]


def _score(query_tokens: list, item: dict) -> float:
    """Lexical relevance 0..1: a title hit counts double a description/location hit."""
    if not query_tokens:
        return 0.0
    title = set(_tokens(item.get("title")))
    rest = (set(_tokens(item.get("description"))) | set(_tokens(item.get("location")))
            | set(_tokens(item.get("category"))))
    hits = 0
    for token in query_tokens:
        if token in title:
            hits += 2
        elif token in rest:
            hits += 1
    return hits / (2 * len(query_tokens))


class ToolBox:
    """Holds the database handle + the current user and executes tool calls."""

    def __init__(self, db, user_id=None):
        self.db = db
        self.user_id = user_id or None
        self.actions = []          # UI actions for the frontend (e.g. prefill the report form)
        self.cards = []            # items to show as cards (photo, place, date, reporter)
        self._tools = {
            "search_items": self.search_items,
            "get_my_items": self.get_my_items,
            "get_item_matches": self.get_item_matches,
            "get_stats": self.get_stats,
            "draft_report": self.draft_report,
        }

    # ── dispatcher ────────────────────────────────────────────────────────────
    def run(self, name: str, args) -> dict:
        tool = self._tools.get(name)
        if tool is None:
            return {"error": f"unknown tool '{name}'"}
        if not isinstance(args, dict):
            return {"error": "tool arguments must be a JSON object"}
        if not self.user_id:               # demo mode: no database access at all
            return dict(GUEST_ERROR)
        # Some models (e.g. gpt-oss) send {"": {}} for tools with no parameters
        args = {k: v for k, v in args.items() if k.strip()}
        try:
            return tool(**args)
        except TypeError as exc:
            return {"error": f"bad arguments: {exc}"}
        except Exception:                       # never let a tool crash the agent loop
            log.exception("tool %s failed", name)
            return {"error": "the tool failed unexpectedly"}

    # ── helpers ───────────────────────────────────────────────────────────────
    def _reporters(self, items) -> dict:
        """{user_id: 'First L.'} for the owners of these items; 'You' for the current user."""
        ids = {i.get("user_id") for i in items if i.get("user_id")}
        try:
            names = self.db.get_reporter_names(sorted(ids)) if ids else {}
        except Exception:
            log.exception("reporter lookup failed")
            names = {}
        if not isinstance(names, dict):
            names = {}
        out = {}
        for uid in ids:
            if uid == self.user_id:
                out[uid] = "You"
            else:
                out[uid] = short_name(names.get(uid)) or "A Findora user"
        return out

    def _show(self, item: dict, **extra):
        """Queue an item card for the UI (deduplicated, capped)."""
        if any(c["item_id"] == item["item_id"] for c in self.cards) or len(self.cards) >= MAX_CARDS:
            return
        self.cards.append({**item, **extra})

    # ── tools ─────────────────────────────────────────────────────────────────
    def search_items(self, query: str = "", item_type=None, category=None, limit=5) -> dict:
        """Keyword search; an empty query lists the most recent reports."""
        if item_type and not validate_item_type(item_type):
            return {"error": "item_type must be 'lost' or 'found'"}
        if category and not validate_category(category):
            return {"error": f"category must be one of {VALID_CATEGORIES}"}
        try:
            limit = max(1, min(int(limit), 10))
        except (TypeError, ValueError):
            limit = 5

        browse = not (query or "").strip()
        tokens = _tokens(query)
        if not tokens and not browse:
            return {"error": "query has no searchable words"}

        items = self.db.get_all_items(
            item_type=item_type.lower() if item_type else None, status="active", limit=300
        )
        if category:
            items = [i for i in items if i.get("category") == category.lower()]

        if browse:                         # newest first (the database already sorts)
            scored = [(1.0, i) for i in items]
        else:
            scored = [(_score(tokens, i), i) for i in items]
            scored = [(s, i) for s, i in scored if s > 0]
        scored.sort(key=lambda pair: pair[0], reverse=True)
        if scored:                         # drop weak hits far below the best one
            floor = max(0.25, scored[0][0] * 0.5)
            scored = [(s, i) for s, i in scored if s >= floor]

        top = [i for _, i in scored[:limit]]
        who = self._reporters(top)
        cards = [public_item(i, who.get(i.get("user_id"))) for i in top]
        for c in cards:
            self._show(c)
        return {"count": len(cards), "results": [model_view(c) for c in cards],
                "note": "Keyword search results (not AI matches). The user sees them as cards with photos."}

    def get_my_items(self) -> dict:
        if not self.user_id:
            return {"error": "the user is not signed in, so their reports can't be listed"}
        items = self.db.get_all_items(status=None, limit=1000)
        mine = [i for i in items if i.get("user_id") == self.user_id]
        mine.sort(key=lambda i: str(i.get("created_at")), reverse=True)
        cards = [public_item(i, "You") for i in mine[:10]]
        for c in cards:
            self._show(c)
        return {"count": len(mine), "items": [model_view(c) for c in cards]}

    def get_item_matches(self, item_id: str) -> dict:
        if not self.user_id:
            return {"error": "the user is not signed in, so matches can't be shown"}
        item = self.db.get_item(item_id)
        if not item:
            return {"error": "item not found"}
        if item.get("user_id") != self.user_id:
            return {"error": "that item does not belong to the current user"}

        matches = sorted(self.db.get_matches_for_item(item_id),
                         key=lambda m: m["confidence_score"], reverse=True)
        other_key = "found_item_id" if item.get("item_type") == "lost" else "lost_item_id"
        pairs = []
        for match in matches[:5]:
            other = self.db.get_item(match[other_key])
            if other:
                pairs.append((round(match["confidence_score"] * 100), other))
        who = self._reporters([o for _, o in pairs])
        results = []
        for pct, other in pairs:
            card = public_item(other, who.get(other.get("user_id")))
            results.append({"confidence_percent": pct, "matched_item": model_view(card)})
            self._show(card, confidence_percent=pct)
        return {"item": model_view(public_item(item, "You")), "count": len(results), "matches": results}

    def get_stats(self) -> dict:
        items = self.db.get_all_items(status=None, limit=1000)
        return {
            "total_items": len(items),
            "lost_items": sum(1 for i in items if i.get("item_type") == "lost"),
            "found_items": sum(1 for i in items if i.get("item_type") == "found"),
            "matched_items": sum(1 for i in items if i.get("status") == "matched"),
        }

    def draft_report(self, item_type: str, title: str, category: str,
                     description: str, location: str, reward_amount=0) -> dict:
        """Validate details and hand a draft to the UI. Nothing is saved."""
        errors = []
        item_type = (item_type or "").strip().lower()
        category = (category or "").strip().lower()
        title = (title or "").strip()
        description = (description or "").strip()
        location = (location or "").strip()

        if not validate_item_type(item_type):
            errors.append(f"item_type must be one of {VALID_ITEM_TYPES}")
        if not validate_category(category):
            errors.append(f"category must be one of {VALID_CATEGORIES}")
        if not 3 <= len(title) <= 100:
            errors.append("title must be 3-100 characters")
        if not 10 <= len(description) <= 1000:
            errors.append("description must be 10-1000 characters (add colour, brand, marks)")
        if not 3 <= len(location) <= 200:
            errors.append("location must be 3-200 characters")
        try:
            reward = max(0.0, float(reward_amount or 0))
        except (TypeError, ValueError):
            reward = 0.0
        if errors:
            return {"ok": False, "errors": errors}

        draft = {
            "item_type": item_type, "title": title, "category": category,
            "description": description, "location": location,
            "reward_amount": reward if item_type == "lost" else 0.0,
        }
        self.actions.append({"type": "prefill_report", "draft": draft})
        return {
            "ok": True,
            "draft": draft,
            "next_step": ("Tell the user a draft is ready. They must open it, add a photo "
                          "(required) and press Submit themselves."),
        }


# ── JSON schemas shown to the model (OpenAI tool format) ──────────────────────
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "search_items",
            "description": ("Search active lost/found reports by keywords. To help someone who "
                            "LOST something, search item_type='found' (and vice versa)."),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": ("Keywords: colour, brand, object, place. "
                                                                 "Empty string lists the most recent reports.")},
                    "item_type": {"type": "string", "enum": VALID_ITEM_TYPES},
                    "category": {"type": "string", "enum": VALID_CATEGORIES},
                    "limit": {"type": "integer", "description": "Max results, 1-10 (default 5)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_my_items",
            "description": "List the signed-in user's own reports (needs sign-in).",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_item_matches",
            "description": "AI matches for one of the signed-in user's own reports, best first.",
            "parameters": {
                "type": "object",
                "properties": {"item_id": {"type": "string", "description": "item_id from get_my_items"}},
                "required": ["item_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_stats",
            "description": "Platform totals: lost, found and matched items.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "draft_report",
            "description": ("Prepare a lost/found report for the user to review. Call it only once "
                            "you know item type, what the item is, key details and the place."),
            "parameters": {
                "type": "object",
                "properties": {
                    "item_type": {"type": "string", "enum": VALID_ITEM_TYPES},
                    "title": {"type": "string", "description": "Short title, e.g. 'Black leather wallet'"},
                    "category": {"type": "string", "enum": VALID_CATEGORIES},
                    "description": {"type": "string", "description": "Colour, brand, marks, contents"},
                    "location": {"type": "string", "description": "Where it was lost/found"},
                    "reward_amount": {"type": "number", "description": "Optional reward (lost items only)"},
                },
                "required": ["item_type", "title", "category", "description", "location"],
            },
        },
    },
]
