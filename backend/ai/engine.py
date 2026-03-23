"""
FINDORA - Production AI Engine
FIXED VERSION
- No Lambda layer (saves cleanly)
- Saves as .keras format
- Compatible with huggingface_hub >= 0.16
- AVIF-safe | Windows-safe | Render-ready
"""

import os
import json
import numpy as np
from typing import List, Dict, Optional
from datetime import datetime


# =========================================================
# PATH RESOLVERS
# =========================================================
def get_models_dir():
    if os.path.exists("/data"):
        return "/data/storage/models/findora_production"
    return os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "storage", "models", "findora_production")
    )

def get_images_dir():
    if os.path.exists("/data"):
        return "/data/storage/images"
    return os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "storage", "images")
    )


# =========================================================
# PRODUCTION AI ENGINE
# =========================================================
class ProductionAIEngine:
    def __init__(self, models_dir: str = None):
        if models_dir is None:
            models_dir = get_models_dir()

        self.models_dir = models_dir
        self.images_dir = get_images_dir()
        self.vision_model = None
        self.text_model = None

        print("🚀 Initializing Production AI Engine...")
        print(f"   Models dir: {self.models_dir}")
        print(f"   Images dir: {self.images_dir}")
        self._load_models()

    # =====================================================
    # MODEL LOADING
    # =====================================================
    def _load_models(self):
        # ── Vision model ──────────────────────────────────
        keras_path = os.path.join(self.models_dir, "vision_encoder.keras")
        h5_path    = os.path.join(self.models_dir, "vision_encoder.h5")

        if os.path.exists(keras_path):
            try:
                from tensorflow.keras.models import load_model
                self.vision_model = load_model(keras_path, compile=False)
                print("✅ Vision encoder loaded (.keras)")
            except Exception as e:
                print(f"⚠️  Failed to load .keras model: {e} → rebuilding fallback")
                self._init_fallback_vision()
        elif os.path.exists(h5_path):
            try:
                from tensorflow.keras.models import load_model
                self.vision_model = load_model(h5_path, compile=False)
                print("✅ Vision encoder loaded (.h5)")
            except Exception as e:
                print(f"⚠️  Failed to load .h5 model: {e} → rebuilding fallback")
                self._init_fallback_vision()
        else:
            print("⚠️  No saved vision model found → building fallback MobileNetV3")
            self._init_fallback_vision()

        # ── Text model ────────────────────────────────────
        try:
            from sentence_transformers import SentenceTransformer
            self.text_model = SentenceTransformer("all-MiniLM-L6-v2")
            print("✅ Text encoder loaded")
        except Exception as e:
            print(f"❌ Text encoder failed: {e}")
            raise

    # =====================================================
    # FALLBACK VISION MODEL
    # No Lambda layer — uses a pure Keras subclass instead
    # so the model is fully serialisable
    # =====================================================
    def _init_fallback_vision(self):
        import tensorflow as tf
        from tensorflow.keras.applications import MobileNetV3Small
        from tensorflow.keras.models import Model
        from tensorflow.keras import layers

        # L2-normalisation as a proper Keras layer (no Lambda)
        class L2Norm(layers.Layer):
            def call(self, x):
                return tf.math.l2_normalize(x, axis=1)

        base = MobileNetV3Small(include_top=False, weights="imagenet", pooling="avg")
        out  = L2Norm()(base.output)
        self.vision_model = Model(base.input, out, name="vision_encoder")
        print("✅ Fallback vision model built")

        # Save as .keras (new native format — no pickling issues)
        try:
            os.makedirs(self.models_dir, exist_ok=True)
            save_path = os.path.join(self.models_dir, "vision_encoder.keras")
            self.vision_model.save(save_path)
            print(f"✅ Vision model saved → {save_path}")
        except Exception as e:
            print(f"⚠️  Could not save vision model: {e} (will rebuild next run)")

    # =====================================================
    # IMAGE FEATURES
    # =====================================================
    def extract_image_features(self, image_path: str) -> Optional[np.ndarray]:
        try:
            from PIL import Image
            from tensorflow.keras.preprocessing import image as keras_image
            from tensorflow.keras.applications.mobilenet_v3 import preprocess_input

            if not image_path:
                return None

            image_path = image_path.replace("\\", "/").lstrip("/")

            if image_path.startswith("storage/"):
                if os.path.exists("/data"):
                    full_path = os.path.join("/data", image_path)
                else:
                    backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
                    full_path = os.path.join(backend_dir, image_path)
            else:
                full_path = image_path

            full_path = os.path.normpath(full_path)

            if not os.path.exists(full_path):
                print(f"❌ Image not found: {full_path}")
                return None

            if full_path.lower().endswith(".avif"):
                print(f"⚠️  AVIF skipped: {full_path}")
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
            emb  = self.text_model.encode(text, convert_to_numpy=True)
            norm = np.linalg.norm(emb)
            return emb / norm if norm > 0 else emb
        except Exception as e:
            print(f"❌ Text embedding error: {e}")
            return None

    # =====================================================
    # SCORING
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
        a    = sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
        dist = R * (2 * atan2(sqrt(a), sqrt(1 - a)))
        return 0.0 if dist > max_km else float(np.exp(-dist / (max_km / 3)))

    # =====================================================
    # SMART MATCHING
    # =====================================================
    def match_items(self, item1: Dict, item2: Dict, threshold=0.6) -> Dict:
        image_sim = 0.0
        text_sim  = 0.0

        f1 = self.extract_image_features(item1.get("image_path", ""))
        f2 = self.extract_image_features(item2.get("image_path", ""))
        if f1 is not None and f2 is not None:
            image_sim = self.cosine(f1, f2)

        t1 = f"{item1.get('title','')} {item1.get('description','')}"
        t2 = f"{item2.get('title','')} {item2.get('description','')}"
        e1 = self.extract_text_embedding(t1)
        e2 = self.extract_text_embedding(t2)
        if e1 is not None and e2 is not None:
            text_sim = self.cosine(e1, e2)

        category_boost = 0.1 if item1.get("category") == item2.get("category") else -0.05

        loc = self.location_score(
            item1.get("latitude"), item1.get("longitude"),
            item2.get("latitude"), item2.get("longitude")
        )

        time_score = 0.7
        if item1.get("created_at") and item2.get("created_at"):
            days = abs(
                (datetime.fromisoformat(item1["created_at"]) -
                 datetime.fromisoformat(item2["created_at"])).days
            )
            time_score = float(np.exp(-days / 30))

        confidence = (
            image_sim   * 0.40 +
            text_sim    * 0.35 +
            loc         * 0.15 +
            time_score  * 0.10 +
            category_boost
        )
        confidence = max(0.0, min(confidence, 0.95))

        return {
            "is_match":         confidence >= threshold,
            "confidence_score": round(confidence,  3),
            "image_similarity": round(image_sim,   3),
            "text_similarity":  round(text_sim,    3),
            "location_score":   round(loc,         3),
            "temporal_score":   round(time_score,  3),
        }

    # =====================================================
    # BATCH MATCH
    # =====================================================
    def batch_match(
        self,
        query_item: Dict,
        candidates: Optional[List[Dict]] = None,
        candidate_items: Optional[List[Dict]] = None,
        threshold=0.6,
        top_k=5,
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