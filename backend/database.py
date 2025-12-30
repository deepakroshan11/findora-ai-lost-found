# backend/database.py
"""
SQLite Database for Findora (Local Development)
Replaces AWS DynamoDB - Works 100% offline!
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional
import os

# Database file location
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'findora.db')

class Database:
    """SQLite database manager"""

    def __init__(self):
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.create_tables()

    # =====================================================
    # TABLE CREATION
    # =====================================================
    def create_tables(self):
        cursor = self.conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS items (
                item_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                category TEXT NOT NULL,
                location TEXT NOT NULL,
                latitude REAL,
                longitude REAL,
                item_type TEXT NOT NULL,
                reward_amount REAL DEFAULT 0,
                contact_info TEXT NOT NULL,
                image_path TEXT,
                status TEXT DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                image_features TEXT,
                text_embedding TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS matches (
                match_id TEXT PRIMARY KEY,
                lost_item_id TEXT NOT NULL,
                found_item_id TEXT NOT NULL,
                confidence_score REAL NOT NULL,
                image_similarity REAL NOT NULL,
                text_similarity REAL NOT NULL,
                location_score REAL NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(lost_item_id, found_item_id),
                FOREIGN KEY (lost_item_id) REFERENCES items(item_id),
                FOREIGN KEY (found_item_id) REFERENCES items(item_id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                phone TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_item_type ON items(item_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_category ON items(category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON items(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON items(user_id)")

        self.conn.commit()
        print("✅ Database tables created successfully!")

    # =====================================================
    # ITEM OPERATIONS
    # =====================================================
    def insert_item(self, item: Dict) -> bool:
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO items VALUES (
                    ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?
                )
            """, (
                item['item_id'], item['user_id'], item['title'], item['description'],
                item['category'], item['location'], item.get('latitude'),
                item.get('longitude'), item['item_type'],
                item.get('reward_amount', 0),
                item['contact_info'], item.get('image_path'),
                item.get('status', 'active'),
                item['created_at'], item['updated_at'],
                json.dumps(item.get('image_features')) if item.get('image_features') else None,
                json.dumps(item.get('text_embedding')) if item.get('text_embedding') else None
            ))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error inserting item: {e}")
            return False

    def get_item(self, item_id: str) -> Optional[Dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM items WHERE item_id = ?", (item_id,))
        row = cursor.fetchone()
        if not row:
            return None
        item = dict(row)
        if item.get("image_features"):
            item["image_features"] = json.loads(item["image_features"])
        if item.get("text_embedding"):
            item["text_embedding"] = json.loads(item["text_embedding"])
        return item

    def get_all_items(self, item_type=None, status="active", limit=50) -> List[Dict]:
        cursor = self.conn.cursor()
        query = "SELECT * FROM items WHERE status = ?"
        params = [status]
        if item_type:
            query += " AND item_type = ?"
            params.append(item_type)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def update_item(self, item_id: str, updates: Dict) -> bool:
        cursor = self.conn.cursor()
        updates["updated_at"] = datetime.utcnow().isoformat()
        keys = ", ".join([f"{k}=?" for k in updates.keys()])
        values = list(updates.values()) + [item_id]
        cursor.execute(f"UPDATE items SET {keys} WHERE item_id = ?", values)
        self.conn.commit()
        return True

    # =====================================================
    # AI FEATURE PIPELINE SUPPORT (AGENT FIX)
    # =====================================================
    def get_items_without_features(self, limit: int = 10) -> List[Dict]:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM items
            WHERE status='active'
            AND (image_features IS NULL OR text_embedding IS NULL)
            ORDER BY created_at ASC
            LIMIT ?
        """, (limit,))
        items = []
        for row in cursor.fetchall():
            item = dict(row)
            if item.get("image_features"):
                item["image_features"] = json.loads(item["image_features"])
            if item.get("text_embedding"):
                item["text_embedding"] = json.loads(item["text_embedding"])
            items.append(item)
        return items

    def update_item_features(self, item_id: str, image_features, text_embedding) -> bool:
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE items
            SET image_features=?, text_embedding=?, updated_at=?
            WHERE item_id=?
        """, (
            json.dumps(image_features),
            json.dumps(text_embedding),
            datetime.utcnow().isoformat(),
            item_id
        ))
        self.conn.commit()
        return True

    # =====================================================
    # MATCHES (DUPLICATE-SAFE)
    # =====================================================
    def match_exists(self, lost_item_id: str, found_item_id: str) -> bool:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 1 FROM matches
            WHERE lost_item_id=? AND found_item_id=?
        """, (lost_item_id, found_item_id))
        return cursor.fetchone() is not None

    def insert_match(self, match: Dict) -> bool:
        if self.match_exists(match["lost_item_id"], match["found_item_id"]):
            return False
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO matches VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (
            match["match_id"],
            match["lost_item_id"],
            match["found_item_id"],
            match["confidence_score"],
            match["image_similarity"],
            match["text_similarity"],
            match["location_score"],
            match.get("status", "pending"),
            match["created_at"],
            match["updated_at"]
        ))
        self.conn.commit()
        return True

    def get_matches_for_item(self, item_id: str) -> List[Dict]:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM matches
            WHERE lost_item_id=? OR found_item_id=?
            ORDER BY confidence_score DESC
        """, (item_id, item_id))
        return [dict(row) for row in cursor.fetchall()]

    # =====================================================
    # USERS
    # =====================================================
    def insert_user(self, user: Dict) -> bool:
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO users VALUES (?,?,?,?,?,?)
        """, (
            user["user_id"],
            user["email"],
            user["name"],
            user.get("phone", ""),
            user["created_at"],
            user["updated_at"]
        ))
        self.conn.commit()
        return True

    def get_user(self, user_id: str) -> Optional[Dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def close(self):
        self.conn.close()


# Global DB instance
db = Database()
