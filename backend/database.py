"""
Findora Database — PostgreSQL (Supabase)
FIXED: Uses IPv4 pooler URL compatible with Render free tier
"""

import psycopg2
import psycopg2.extras
import json
import os
from datetime import datetime
from typing import List, Dict, Optional

DATABASE_URL = os.getenv("DATABASE_URL", "")


def _clean_url(url: str) -> str:
    """Strip sslmode/ssl query params from URL — psycopg2 takes them as kwargs."""
    for param in ("?sslmode", "&sslmode", "?ssl", "&ssl"):
        if param in url:
            url = url.split(param)[0]
    return url


def _connect() -> psycopg2.extensions.connection:
    """Open a new connection to Supabase via IPv4 pooler."""
    url = _clean_url(DATABASE_URL)
    try:
        conn = psycopg2.connect(url, sslmode="require")
    except psycopg2.OperationalError:
        # Some poolers terminate SSL at the proxy — try without
        conn = psycopg2.connect(url)
    conn.autocommit = False
    return conn


def _is_alive(conn) -> bool:
    """Return True if the connection is open and responsive."""
    if conn is None or conn.closed:
        return False
    try:
        conn.cursor().execute("SELECT 1")
        return True
    except Exception:
        return False


class Database:

    def __init__(self):
        if not DATABASE_URL:
            raise ValueError("DATABASE_URL environment variable not set")
        print("🔌 Connecting to database...")
        self.conn = _connect()
        self.create_tables()
        print("✅ PostgreSQL connected (Supabase)")

    def _cursor(self) -> psycopg2.extras.RealDictCursor:
        """Return a RealDictCursor, reconnecting if the connection has dropped."""
        if not _is_alive(self.conn):
            print("🔄 Reconnecting to database...")
            try:
                self.conn.close()
            except Exception:
                pass
            self.conn = _connect()
        return self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # ── Schema ────────────────────────────────────────────────────────────────

    def create_tables(self):
        cur = self._cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS items (
                item_id        TEXT PRIMARY KEY,
                user_id        TEXT NOT NULL,
                title          TEXT NOT NULL,
                description    TEXT NOT NULL,
                category       TEXT NOT NULL,
                location       TEXT NOT NULL,
                latitude       REAL,
                longitude      REAL,
                item_type      TEXT NOT NULL,
                reward_amount  REAL DEFAULT 0,
                contact_info   TEXT NOT NULL,
                image_path     TEXT,
                status         TEXT DEFAULT 'active',
                created_at     TEXT NOT NULL,
                updated_at     TEXT NOT NULL,
                image_features TEXT,
                text_embedding TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS matches (
                match_id         TEXT PRIMARY KEY,
                lost_item_id     TEXT NOT NULL,
                found_item_id    TEXT NOT NULL,
                confidence_score REAL NOT NULL,
                image_similarity REAL NOT NULL,
                text_similarity  REAL NOT NULL,
                location_score   REAL NOT NULL,
                status           TEXT DEFAULT 'pending',
                created_at       TEXT NOT NULL,
                updated_at       TEXT NOT NULL,
                UNIQUE(lost_item_id, found_item_id)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id    TEXT PRIMARY KEY,
                email      TEXT UNIQUE NOT NULL,
                name       TEXT NOT NULL,
                phone      TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_item_type ON items(item_type)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_status    ON items(status)")
        self.conn.commit()
        print("✅ Database tables ready")

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_json_fields(item: Dict) -> Dict:
        for field in ("image_features", "text_embedding"):
            if item.get(field):
                try:
                    item[field] = json.loads(item[field])
                except Exception:
                    item[field] = None
        return item

    # ── Items ─────────────────────────────────────────────────────────────────

    def insert_item(self, item: Dict) -> bool:
        try:
            cur = self._cursor()
            cur.execute("""
                INSERT INTO items (
                    item_id, user_id, title, description, category,
                    location, latitude, longitude, item_type, reward_amount,
                    contact_info, image_path, status, created_at, updated_at,
                    image_features, text_embedding
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                item["item_id"],   item["user_id"],    item["title"],
                item["description"], item["category"], item["location"],
                item.get("latitude"), item.get("longitude"),
                item["item_type"],    item.get("reward_amount", 0),
                item["contact_info"], item.get("image_path"),
                item.get("status", "active"),
                item["created_at"],   item["updated_at"],
                json.dumps(item["image_features"]) if item.get("image_features") else None,
                json.dumps(item["text_embedding"]) if item.get("text_embedding") else None,
            ))
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"❌ Error inserting item: {e}")
            return False

    def get_item(self, item_id: str) -> Optional[Dict]:
        cur = self._cursor()
        cur.execute("SELECT * FROM items WHERE item_id = %s", (item_id,))
        row = cur.fetchone()
        return self._parse_json_fields(dict(row)) if row else None

    def get_all_items(self, item_type=None, status="active", limit=50) -> List[Dict]:
        """status=None → all items; status='active' → only active; etc."""
        cur = self._cursor()
        if status is None:
            query, params = "SELECT * FROM items WHERE 1=1", []
        else:
            query, params = "SELECT * FROM items WHERE status = %s", [status]

        if item_type:
            query += " AND item_type = %s"
            params.append(item_type)

        query += " ORDER BY created_at DESC LIMIT %s"
        params.append(limit)
        cur.execute(query, params)
        return [self._parse_json_fields(dict(row)) for row in cur.fetchall()]

    def update_item(self, item_id: str, updates: Dict) -> bool:
        try:
            updates["updated_at"] = datetime.utcnow().isoformat()
            cur    = self._cursor()
            keys   = ", ".join(f"{k}=%s" for k in updates)
            values = list(updates.values()) + [item_id]
            cur.execute(f"UPDATE items SET {keys} WHERE item_id = %s", values)
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"❌ Error updating item: {e}")
            return False

    def get_items_without_features(self, limit: int = 10) -> List[Dict]:
        cur = self._cursor()
        cur.execute("""
            SELECT * FROM items
            WHERE status = 'active'
              AND (image_features IS NULL OR text_embedding IS NULL)
            ORDER BY created_at ASC LIMIT %s
        """, (limit,))
        return [self._parse_json_fields(dict(row)) for row in cur.fetchall()]

    def update_item_features(self, item_id: str, image_features, text_embedding) -> bool:
        try:
            cur = self._cursor()
            cur.execute("""
                UPDATE items
                SET image_features=%s, text_embedding=%s, updated_at=%s
                WHERE item_id=%s
            """, (
                json.dumps(image_features), json.dumps(text_embedding),
                datetime.utcnow().isoformat(), item_id,
            ))
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"❌ Error updating features: {e}")
            return False

    # ── Matches ───────────────────────────────────────────────────────────────

    def match_exists(self, lost_item_id: str, found_item_id: str) -> bool:
        cur = self._cursor()
        cur.execute("""
            SELECT 1 FROM matches WHERE lost_item_id=%s AND found_item_id=%s
        """, (lost_item_id, found_item_id))
        return cur.fetchone() is not None

    def insert_match(self, match: Dict) -> bool:
        if self.match_exists(match["lost_item_id"], match["found_item_id"]):
            return False
        try:
            cur = self._cursor()
            cur.execute("""
                INSERT INTO matches
                    (match_id, lost_item_id, found_item_id,
                     confidence_score, image_similarity, text_similarity,
                     location_score, status, created_at, updated_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                match["match_id"],         match["lost_item_id"],
                match["found_item_id"],    match["confidence_score"],
                match["image_similarity"], match["text_similarity"],
                match["location_score"],   match.get("status", "pending"),
                match["created_at"],       match["updated_at"],
            ))
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"❌ Error inserting match: {e}")
            return False

    def get_matches_for_item(self, item_id: str) -> List[Dict]:
        cur = self._cursor()
        cur.execute("""
            SELECT * FROM matches
            WHERE lost_item_id=%s OR found_item_id=%s
            ORDER BY confidence_score DESC
        """, (item_id, item_id))
        return [dict(row) for row in cur.fetchall()]

    # ── Users ─────────────────────────────────────────────────────────────────

    def insert_user(self, user: Dict) -> bool:
        try:
            cur = self._cursor()
            cur.execute("""
                INSERT INTO users (user_id, email, name, phone, created_at, updated_at)
                VALUES (%s,%s,%s,%s,%s,%s)
            """, (
                user["user_id"], user["email"], user["name"],
                user.get("phone", ""), user["created_at"], user["updated_at"],
            ))
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"❌ Error inserting user: {e}")
            return False

    def get_user(self, user_id: str) -> Optional[Dict]:
        cur = self._cursor()
        cur.execute("SELECT * FROM users WHERE user_id=%s", (user_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass


db = Database()