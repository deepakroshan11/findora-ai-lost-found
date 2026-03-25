"""
Findora Database — PostgreSQL (Supabase)
Replaces SQLite so data persists across Render restarts.
All queries use %s placeholders (psycopg2 style).
"""

import psycopg2
import psycopg2.extras
import json
import os
from datetime import datetime
from typing import List, Dict, Optional

DATABASE_URL = os.getenv("DATABASE_URL")


class Database:

    def __init__(self):
        self.conn = psycopg2.connect(DATABASE_URL, sslmode="require")
        self.conn.autocommit = False
        self.create_tables()
        print("✅ PostgreSQL connected (Supabase)")

    def _cursor(self):
        """Return a RealDictCursor, reconnecting if the connection dropped."""
        try:
            self.conn.isolation_level  # raises if dead
        except Exception:
            self.conn = psycopg2.connect(DATABASE_URL, sslmode="require")
        return self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    def create_tables(self):
        cur = self._cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS items (
                item_id       TEXT PRIMARY KEY,
                user_id       TEXT NOT NULL,
                title         TEXT NOT NULL,
                description   TEXT NOT NULL,
                category      TEXT NOT NULL,
                location      TEXT NOT NULL,
                latitude      REAL,
                longitude     REAL,
                item_type     TEXT NOT NULL,
                reward_amount REAL DEFAULT 0,
                contact_info  TEXT NOT NULL,
                image_path    TEXT,
                status        TEXT DEFAULT 'active',
                created_at    TEXT NOT NULL,
                updated_at    TEXT NOT NULL,
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
                item['item_id'], item['user_id'], item['title'],
                item['description'], item['category'], item['location'],
                item.get('latitude'), item.get('longitude'),
                item['item_type'], item.get('reward_amount', 0),
                item['contact_info'], item.get('image_path'),
                item.get('status', 'active'),
                item['created_at'], item['updated_at'],
                json.dumps(item['image_features']) if item.get('image_features') else None,
                json.dumps(item['text_embedding']) if item.get('text_embedding') else None,
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
        if not row:
            return None
        item = dict(row)
        for f in ("image_features", "text_embedding"):
            if item.get(f):
                try:
                    item[f] = json.loads(item[f])
                except Exception:
                    item[f] = None
        return item

    def get_all_items(self, item_type=None, status="active", limit=50) -> List[Dict]:
        """
        status=None    → return ALL items (active + matched + any other)
        status="active"  → only active
        status="matched" → only matched
        """
        cur = self._cursor()
        if status is None:
            query: str  = "SELECT * FROM items WHERE 1=1"
            params: list = []
        else:
            query  = "SELECT * FROM items WHERE status = %s"
            params = [status]

        if item_type:
            query += " AND item_type = %s"
            params.append(item_type)

        query += " ORDER BY created_at DESC LIMIT %s"
        params.append(limit)
        cur.execute(query, params)

        result = []
        for row in cur.fetchall():
            item = dict(row)
            for f in ("image_features", "text_embedding"):
                if item.get(f):
                    try:
                        item[f] = json.loads(item[f])
                    except Exception:
                        item[f] = None
            result.append(item)
        return result

    def update_item(self, item_id: str, updates: Dict) -> bool:
        updates["updated_at"] = datetime.utcnow().isoformat()
        cur    = self._cursor()
        keys   = ", ".join([f"{k}=%s" for k in updates.keys()])
        values = list(updates.values()) + [item_id]
        cur.execute(f"UPDATE items SET {keys} WHERE item_id = %s", values)
        self.conn.commit()
        return True

    def get_items_without_features(self, limit: int = 10) -> List[Dict]:
        """Used by the AI agent to find items needing feature extraction."""
        cur = self._cursor()
        cur.execute("""
            SELECT * FROM items
            WHERE status = 'active'
              AND (image_features IS NULL OR text_embedding IS NULL)
            ORDER BY created_at ASC
            LIMIT %s
        """, (limit,))
        items = []
        for row in cur.fetchall():
            item = dict(row)
            for f in ("image_features", "text_embedding"):
                if item.get(f):
                    try:
                        item[f] = json.loads(item[f])
                    except Exception:
                        item[f] = None
            items.append(item)
        return items

    def update_item_features(self, item_id: str, image_features, text_embedding) -> bool:
        cur = self._cursor()
        cur.execute("""
            UPDATE items
               SET image_features = %s,
                   text_embedding  = %s,
                   updated_at      = %s
             WHERE item_id = %s
        """, (
            json.dumps(image_features),
            json.dumps(text_embedding),
            datetime.utcnow().isoformat(),
            item_id,
        ))
        self.conn.commit()
        return True

    # ── Matches ───────────────────────────────────────────────────────────────

    def match_exists(self, lost_item_id: str, found_item_id: str) -> bool:
        cur = self._cursor()
        cur.execute("""
            SELECT 1 FROM matches
             WHERE lost_item_id = %s AND found_item_id = %s
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
             WHERE lost_item_id = %s OR found_item_id = %s
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
        cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def close(self):
        self.conn.close()


db = Database()