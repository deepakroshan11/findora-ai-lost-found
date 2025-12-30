"""
FINDORA - Autonomous AI Agent
Continuously monitors and matches items automatically
"""

import asyncio
import sys
import os
from datetime import datetime
from typing import List, Dict
import uuid

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from database import db
from ai.engine import get_ai_engine


# ================= CONFIG =================
EMAIL_CONFIDENCE_THRESHOLD = 0.80  # 80%
# ==========================================


class FindoraAgent:
    """
    Autonomous AI Agent for Findora
    - Monitors new items
    - Extracts features
    - Finds matches
    - Stores matches
    - Sends notifications (confidence-aware)
    """

    def __init__(self, match_threshold: float = 0.6, check_interval: int = 30):
        self.ai_engine = get_ai_engine()
        self.match_threshold = match_threshold
        self.check_interval = check_interval
        self.is_running = False

        print("=" * 60)
        print("🤖 FINDORA AUTONOMOUS AI AGENT")
        print("=" * 60)
        print(f"   Match Threshold: {match_threshold}")
        print(f"   Email Threshold: {EMAIL_CONFIDENCE_THRESHOLD}")
        print(f"   Check Interval: {check_interval}s")
        print("=" * 60)

    # --------------------------------------------------
    async def observe_new_items(self) -> List[Dict]:
        """Get items that need feature extraction"""
        try:
            return db.get_items_without_features(limit=50)
        except Exception as e:
            print(f"Error observing items: {e}")
            return []

    # --------------------------------------------------
    async def extract_features(self, item: Dict) -> bool:
        """Extract and store AI features"""
        try:
            item_id = item["item_id"]
            print(f"🔍 Extracting features: {item['title']} ({item_id})")

            image_features = None
            if item.get("image_path"):
                img = self.ai_engine.extract_image_features(item["image_path"])
                if img is not None:
                    image_features = img.tolist()

            text_embedding = None
            text = f"{item.get('title','')} {item.get('description','')}"
            if text.strip():
                emb = self.ai_engine.extract_text_embedding(text)
                if emb is not None:
                    text_embedding = emb.tolist()

            if image_features and text_embedding:
                if db.update_item_features(item_id, image_features, text_embedding):
                    print("   ✅ Features extracted successfully")
                    return True

            print("   ⚠️  Feature extraction incomplete")
            return False

        except Exception as e:
            print(f"Error extracting features: {e}")
            return False

    # --------------------------------------------------
    async def find_matches(self, item: Dict) -> List[Dict]:
        """Find matches using AI engine"""
        try:
            opposite_type = "found" if item["item_type"] == "lost" else "lost"
            candidates = db.get_all_items(
                item_type=opposite_type, status="active", limit=100
            )

            candidates = [
                c for c in candidates
                if c.get("image_features") and c.get("text_embedding")
            ]

            if not candidates:
                return []

            print(f"🔎 Comparing against {len(candidates)} {opposite_type} items...")

            return self.ai_engine.batch_match(
                query_item=item,
                candidate_items=candidates,
                threshold=self.match_threshold,
                top_k=5,
            )

        except Exception as e:
            print(f"Error finding matches: {e}")
            return []

    # --------------------------------------------------
    async def store_match(self, lost_id: str, found_id: str, scores: Dict):
        """Store match in DB"""
        try:
            match_id = str(uuid.uuid4())
            now = datetime.utcnow().isoformat()

            db.insert_match({
                "match_id": match_id,
                "lost_item_id": lost_id,
                "found_item_id": found_id,
                "confidence_score": scores["confidence_score"],
                "image_similarity": scores["image_similarity"],
                "text_similarity": scores["text_similarity"],
                "location_score": scores["location_score"],
                "status": "pending",
                "created_at": now,
                "updated_at": now,
            })

            print(f"   💾 Match stored: {match_id}")

        except Exception as e:
            print(f"Error storing match: {e}")

    # --------------------------------------------------
    async def notify_users(self, match: Dict, lost_item: Dict, found_item: Dict):
        """
        Notify users ONLY if confidence >= 80%
        """
        try:
            confidence = match["confidence_score"]

            if confidence < EMAIL_CONFIDENCE_THRESHOLD:
                print(
                    f"   📭 Notification skipped "
                    f"({confidence*100:.1f}% < 80%)"
                )
                return

            print("   📧 MATCH NOTIFICATION (EMAIL SENT)")
            print(f"      Lost: {lost_item['title']}")
            print(f"      Found: {found_item['title']}")
            print(f"      Confidence: {confidence*100:.1f}%")
            print(f"      Lost Contact: {lost_item['contact_info']}")
            print(f"      Found Contact: {found_item['contact_info']}")

            # 👉 SMTP / SendGrid / SMS hook goes here later

        except Exception as e:
            print(f"Error sending notification: {e}")

    # --------------------------------------------------
    async def process_item(self, item: Dict):
        """Process single item"""
        try:
            item_id = item["item_id"]

            if not item.get("image_features") or not item.get("text_embedding"):
                if not await self.extract_features(item):
                    return
                item = db.get_item(item_id)
                if not item:
                    return

            matches = await self.find_matches(item)

            if not matches:
                print("   ℹ️  No matches found")
                return

            print(f"   ✨ Found {len(matches)} matches!")

            for match in matches:
                matched_item = match["item"]

                if item["item_type"] == "lost":
                    lost_item, found_item = item, matched_item
                else:
                    lost_item, found_item = matched_item, item

                scores = {
                    "confidence_score": match["confidence_score"],
                    "image_similarity": match["image_similarity"],
                    "text_similarity": match["text_similarity"],
                    "location_score": match["location_score"],
                }

                await self.store_match(
                    lost_item["item_id"],
                    found_item["item_id"],
                    scores,
                )

                await self.notify_users(match, lost_item, found_item)

        except Exception as e:
            print(f"Error processing item: {e}")

    # --------------------------------------------------
    async def run_cycle(self):
        print("\n" + "=" * 60)
        print(f"🔄 Agent Cycle - {datetime.now().strftime('%H:%M:%S')}")
        print("=" * 60)

        items = await self.observe_new_items()

        if not items:
            print("   ℹ️  No new items to process")
            return

        print(f"   📋 Processing {len(items)} items...")

        for i, item in enumerate(items, 1):
            print(f"\n   [{i}/{len(items)}] {item['title']}")
            await self.process_item(item)

        print("\n" + "=" * 60)
        print("✅ Cycle completed")
        print("=" * 60)

    # --------------------------------------------------
    async def start(self):
        self.is_running = True
        print("\n🚀 Agent started!")
        print(f"   Monitoring every {self.check_interval}s")
        print("   Press Ctrl+C to stop\n")

        try:
            while self.is_running:
                await self.run_cycle()
                await asyncio.sleep(self.check_interval)
        except KeyboardInterrupt:
            print("\n🛑 Agent stopped by user")
        finally:
            self.is_running = False


async def run_agent():
    agent = FindoraAgent(match_threshold=0.6, check_interval=30)
    await agent.start()


if __name__ == "__main__":
    asyncio.run(run_agent())
