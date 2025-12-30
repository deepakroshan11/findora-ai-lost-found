"""
FINDORA - Production AI Engine
FINAL STABLE VERSION (AVIF-SAFE + SMART MATCHING)
Agent-compatible | Windows-safe | Production-ready
"""

import os
import json
import numpy as np
from typing import List, Dict, Optional
from datetime import datetime


# =========================================================
# PRODUCTION AI ENGINE
# =========================================================

class ProductionAIEngine:
    def __init__(self, models_dir: str = None):
        if models_dir is None:
            models_dir = os.path.abspath(
                os.path.join(
                    os.path.dirname(__file__),
                    "..", "storage", "models", "findora_production"
                )
            )

        self.models_dir = models_dir
        self.vision_model = None
        self.text_model = None

        print("🚀 Initializing Production AI Engine...")
        self._load_models()

    # =====================================================
    # MODEL LOADING
    # =====================================================
    def _load_models(self):
        try:
            vision_path = os.path.join(self.models_dir, "vision_encoder.h5")
            if os.path.exists(vision_path):
                from tensorflow.keras.models import load_model
                self.vision_model = load_model(vision_path, compile=False)
                print("✅ Vision encoder loaded")
            else:
                self._init_fallback_vision()

            from sentence_transformers import SentenceTransformer
            self.text_model = SentenceTransformer("all-MiniLM-L6-v2")
            print("✅ Text encoder loaded")

        except Exception as e:
            print(f"⚠️ Model load error: {e}")
            self._init_fallback_vision()
            from sentence_transformers import SentenceTransformer
            self.text_model = SentenceTransformer("all-MiniLM-L6-v2")

    def _init_fallback_vision(self):
        from tensorflow.keras.applications import MobileNetV3Small
        from tensorflow.keras.models import Model
        import tensorflow as tf

        base = MobileNetV3Small(include_top=False, weights="imagenet", pooling="avg")
        x = tf.keras.layers.Lambda(
            lambda t: tf.math.l2_normalize(t, axis=1)
        )(base.output)

        self.vision_model = Model(base.input, x)
        print("✅ Fallback vision model loaded")

    # =====================================================
    # IMAGE FEATURES (AVIF SAFE)
    # =====================================================
    def extract_image_features(self, image_path: str) -> Optional[np.ndarray]:
        try:
            from PIL import Image
            from tensorflow.keras.preprocessing import image as keras_image
            from tensorflow.keras.applications.mobilenet_v3 import preprocess_input

            backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            image_path = image_path.replace("\\", "/").lstrip("/")
            full_path = os.path.normpath(
                os.path.join(backend_dir, image_path)
                if image_path.startswith("storage/")
                else image_path
            )

            if not os.path.exists(full_path):
                print(f"❌ Image not found: {full_path}")
                return None

            # 🚫 AVIF BLOCK
            if full_path.lower().endswith(".avif"):
                print(f"⚠️ AVIF detected → skipping vision: {full_path}")
                return None

            img = Image.open(full_path).convert("RGB").resize((224, 224))
            arr = keras_image.img_to_array(img)
            arr = np.expand_dims(arr, axis=0)
            arr = preprocess_input(arr)

            features = self.vision_model.predict(arr, verbose=0)
            return features.flatten()

        except Exception as e:
            print(f"❌ Image feature error: {e}")
            return None

    # =====================================================
    # TEXT EMBEDDINGS
    # =====================================================
    def extract_text_embedding(self, text: str) -> Optional[np.ndarray]:
        try:
            text = " ".join(text.lower().split())
            emb = self.text_model.encode(text, convert_to_numpy=True)
            return emb / np.linalg.norm(emb)
        except Exception as e:
            print(f"❌ Text embedding error: {e}")
            return None

    # =====================================================
    # SCORING HELPERS
    # =====================================================
    def cosine(self, a, b):
        from sklearn.metrics.pairwise import cosine_similarity
        return float((cosine_similarity(a.reshape(1, -1), b.reshape(1, -1))[0][0] + 1) / 2)

    def location_score(self, lat1, lon1, lat2, lon2, max_km=10):
        if not all([lat1, lon1, lat2, lon2]):
            return 0.5

        from math import radians, sin, cos, sqrt, atan2
        R = 6371
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat, dlon = lat2 - lat1, lon2 - lon1

        a = sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
        dist = R * (2 * atan2(sqrt(a), sqrt(1-a)))

        return 0.0 if dist > max_km else float(np.exp(-dist / (max_km / 3)))

    # =====================================================
    # SMART MATCHING
    # =====================================================
    def match_items(self, item1: Dict, item2: Dict, threshold=0.6) -> Dict:
        image_sim = 0.0
        text_sim = 0.0

        # Image
        f1 = self.extract_image_features(item1.get("image_path", ""))
        f2 = self.extract_image_features(item2.get("image_path", ""))
        if f1 is not None and f2 is not None:
            image_sim = self.cosine(f1, f2)

        # Text
        t1 = f"{item1.get('title','')} {item1.get('description','')}"
        t2 = f"{item2.get('title','')} {item2.get('description','')}"
        e1, e2 = self.extract_text_embedding(t1), self.extract_text_embedding(t2)
        if e1 is not None and e2 is not None:
            text_sim = self.cosine(e1, e2)

        # Category-aware boost
        category_boost = 0.1 if item1.get("category") == item2.get("category") else -0.05

        # Location + time
        loc = self.location_score(
            item1.get("latitude"), item1.get("longitude"),
            item2.get("latitude"), item2.get("longitude")
        )

        time = 0.7
        if item1.get("created_at") and item2.get("created_at"):
            days = abs(
                (datetime.fromisoformat(item1["created_at"]) -
                 datetime.fromisoformat(item2["created_at"])).days
            )
            time = float(np.exp(-days / 30))

        confidence = (
            image_sim * 0.4 +
            text_sim * 0.35 +
            loc * 0.15 +
            time * 0.1 +
            category_boost
        )

        confidence = max(0.0, min(confidence, 0.95))  # cap confidence

        return {
            "is_match": confidence >= threshold,
            "confidence_score": round(confidence, 3),
            "image_similarity": round(image_sim, 3),
            "text_similarity": round(text_sim, 3),
            "location_score": round(loc, 3),
            "temporal_score": round(time, 3)
        }

    # =====================================================
    # BATCH MATCH (AGENT SAFE)
    # =====================================================
    def batch_match(
        self,
        query_item: Dict,
        candidates: Optional[List[Dict]] = None,
        candidate_items: Optional[List[Dict]] = None,
        threshold=0.6,
        top_k=5
    ):
        if candidates is None:
            candidates = candidate_items or []

        matches = []
        for c in candidates:
            r = self.match_items(query_item, c, threshold)
            if r["is_match"]:
                matches.append({**r, "item": c})

        matches.sort(key=lambda x: x["confidence_score"], reverse=True)
        return matches[:top_k]


# =====================================================
# SINGLETON
# =====================================================
_engine = None

def get_ai_engine():
    global _engine
    if _engine is None:
        _engine = ProductionAIEngine()
    return _engine


if __name__ == "__main__":
    get_ai_engine()
    print("✅ AI Engine ready")
