"""
FINDORA - Production AI Engine v2
FIXES vs original:
  - extract_image_features() now accepts Cloudinary https:// URLs
    → downloads the image to a temp file, then extracts features
  - No Lambda layers (uses L2Norm Keras subclass — fully serialisable)
  - Saves model as .keras format
  - AVIF-safe | Windows-safe | Render-ready
"""

import os
import json
import tempfile
import numpy as np
from typing import List, Dict, Optional
from datetime import datetime


# =========================================================
# PATH RESOLVERS  (local dev uses ./storage, Render uses /data)
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
        self.text_model   = None

        print("🚀 Initialising Production AI Engine...")
        print(f"   Models dir : {self.models_dir}")
        print(f"   Images dir : {self.images_dir}")
        self._load_models()

    # =====================================================
    # MODEL LOADING
    # =====================================================
    def _load_models(self):
        keras_path = os.path.join(self.models_dir, "vision_encoder.keras")
        h5_path    = os.path.join(self.models_dir, "vision_encoder.h5")

        if os.path.exists(keras_path):
            try:
                from tensorflow.keras.models import load_model
                self.vision_model = load_model(keras_path, compile=False)
                print("✅ Vision encoder loaded (.keras)")
            except Exception as e:
                print(f"⚠️  .keras load failed: {e} → rebuilding fallback")
                self._init_fallback_vision()
        elif os.path.exists(h5_path):
            try:
                from tensorflow.keras.models import load_model
                self.vision_model = load_model(h5_path, compile=False)
                print("✅ Vision encoder loaded (.h5)")
            except Exception as e:
                print(f"⚠️  .h5 load failed: {e} → rebuilding fallback")
                self._init_fallback_vision()
        else:
            print("⚠️  No saved vision model → building fallback MobileNetV3")
            self._init_fallback_vision()

        try:
            from sentence_transformers import SentenceTransformer
            self.text_model = SentenceTransformer("all-MiniLM-L6-v2")
            print("✅ Text encoder loaded")
        except Exception as e:
            print(f"❌ Text encoder failed: {e}")
            raise

    # =====================================================
    # FALLBACK VISION MODEL  (no Lambda — uses Keras subclass)
    # =====================================================
    def _init_fallback_vision(self):
        import tensorflow as tf
        from tensorflow.keras.applications import MobileNetV3Small
        from tensorflow.keras.models import Model
        from tensorflow.keras import layers

        class L2Norm(layers.Layer):
            def call(self, x):
                return tf.math.l2_normalize(x, axis=1)

        base = MobileNetV3Small(include_top=False, weights="imagenet", pooling="avg")
        out  = L2Norm()(base.output)
        self.vision_model = Model(base.input, out, name="vision_encoder")
        print("✅ Fallback MobileNetV3 vision model built")

        try:
            os.makedirs(self.models_dir, exist_ok=True)
            save_path = os.path.join(self.models_dir, "vision_encoder.keras")
            self.vision_model.save(save_path)
            print(f"✅ Vision model saved → {save_path}")
        except Exception as e:
            print(f"⚠️  Could not save vision model: {e}")

    # =====================================================
    # IMAGE FEATURES  — supports local paths AND https:// URLs
    # =====================================================
    def extract_image_features(self, image_path: str) -> Optional[np.ndarray]:
        """
        Accepts:
          - Cloudinary https:// URL  → download to temp file, then extract
          - Local /storage/images/UUID.ext path
        """
        if not image_path:
            return None

        try:
            from PIL import Image
            from tensorflow.keras.preprocessing import image as keras_image
            from tensorflow.keras.applications.mobilenet_v3 import preprocess_input

            # ── Cloudinary / any remote URL ───────────────────────────────
            if image_path.startswith("http://") or image_path.startswith("https://"):
                return self._extract_from_url(image_path)

            # ── Local file path ───────────────────────────────────────────
            image_path = image_path.replace("\\", "/").lstrip("/")

            if image_path.startswith("storage/"):
                if os.path.exists("/data"):
                    full_path = os.path.join("/data", image_path)
                else:
                    backend_dir = os.path.abspath(
                        os.path.join(os.path.dirname(__file__), "..")
                    )
                    full_path = os.path.join(backend_dir, image_path)
            else:
                full_path = image_path

            full_path = os.path.normpath(full_path)

            if not os.path.exists(full_path):
                print(f"❌ Image file not found: {full_path}")
                return None

            if full_path.lower().endswith(".avif"):
                print(f"⚠️  AVIF skipped: {full_path}")
                return None

            return self._extract_from_pil(Image.open(full_path))

        except Exception as e:
            print(f"❌ Image feature error: {e}")
            return None

    def _extract_from_url(self, url: str) -> Optional[np.ndarray]:
        """Download image from URL to a temp file, then extract features."""
        try:
            import requests
            from PIL import Image

            print(f"   📥 Downloading image from URL: {url[:60]}...")
            resp = requests.get(url, timeout=15, stream=True)
            resp.raise_for_status()

            # Write to temp file preserving extension
            ext = url.split("?")[0].rsplit(".", 1)[-1].lower()
            if ext not in ("jpg", "jpeg", "png", "webp", "gif"):
                ext = "jpg"

            with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as tmp:
                tmp_path = tmp.name
                for chunk in resp.iter_content(chunk_size=8192):
                    tmp.write(chunk)

            try:
                img     = Image.open(tmp_path)
                features = self._extract_from_pil(img)
                return features
            finally:
                os.unlink(tmp_path)   # always clean up

        except Exception as e:
            print(f"❌ URL image download error: {e}")
            return None

    def _extract_from_pil(self, img) -> Optional[np.ndarray]:
        """Run MobileNetV3 on a PIL Image and return the feature vector."""
        try:
            from PIL import Image
            from tensorflow.keras.preprocessing import image as keras_image
            from tensorflow.keras.applications.mobilenet_v3 import preprocess_input

            img = img.convert("RGB").resize((224, 224))
            arr = keras_image.img_to_array(img)
            arr = np.expand_dims(arr, axis=0)
            arr = preprocess_input(arr)

            features = self.vision_model.predict(arr, verbose=0)
            return features.flatten()
        except Exception as e:
            print(f"❌ PIL feature extraction error: {e}")
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
    # SCORING UTILITIES
    # =====================================================
    def cosine(self, a: np.ndarray, b: np.ndarray) -> float:
        from sklearn.metrics.pairwise import cosine_similarity
        return float(
            (cosine_similarity(a.reshape(1, -1), b.reshape(1, -1))[0][0] + 1) / 2
        )

    def location_score(self, lat1, lon1, lat2, lon2, max_km: float = 10) -> float:
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
    # SMART MATCH (single pair)
    # =====================================================
    def match_items(self, item1: Dict, item2: Dict, threshold: float = 0.6) -> Dict:
        image_sim = 0.0
        text_sim  = 0.0

        # Vision similarity
        f1 = None
        f2 = None
        if item1.get("image_features"):
            f1 = np.array(item1["image_features"])
        elif item1.get("image_path"):
            raw = self.extract_image_features(item1["image_path"])
            if raw is not None:
                f1 = raw

        if item2.get("image_features"):
            f2 = np.array(item2["image_features"])
        elif item2.get("image_path"):
            raw = self.extract_image_features(item2["image_path"])
            if raw is not None:
                f2 = raw

        if f1 is not None and f2 is not None:
            image_sim = self.cosine(f1, f2)

        # Text similarity
        e1 = None
        e2 = None
        if item1.get("text_embedding"):
            e1 = np.array(item1["text_embedding"])
        else:
            t1 = f"{item1.get('title','')} {item1.get('description','')}"
            e1 = self.extract_text_embedding(t1)

        if item2.get("text_embedding"):
            e2 = np.array(item2["text_embedding"])
        else:
            t2 = f"{item2.get('title','')} {item2.get('description','')}"
            e2 = self.extract_text_embedding(t2)

        if e1 is not None and e2 is not None:
            text_sim = self.cosine(e1, e2)

        cat_boost = 0.10 if item1.get("category") == item2.get("category") else -0.05

        loc = self.location_score(
            item1.get("latitude"),  item1.get("longitude"),
            item2.get("latitude"),  item2.get("longitude"),
        )

        time_score = 0.7
        if item1.get("created_at") and item2.get("created_at"):
            try:
                days = abs(
                    (datetime.fromisoformat(item1["created_at"]) -
                     datetime.fromisoformat(item2["created_at"])).days
                )
                time_score = float(np.exp(-days / 30))
            except Exception:
                pass

        confidence = (
            image_sim  * 0.40 +
            text_sim   * 0.35 +
            loc        * 0.15 +
            time_score * 0.10 +
            cat_boost
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
        query_item:      Dict,
        candidates:      Optional[List[Dict]] = None,
        candidate_items: Optional[List[Dict]] = None,
        threshold:       float = 0.6,
        top_k:           int   = 5,
    ) -> List[Dict]:
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
_engine: Optional[ProductionAIEngine] = None

def get_ai_engine() -> ProductionAIEngine:
    global _engine
    if _engine is None:
        _engine = ProductionAIEngine()
    return _engine


if __name__ == "__main__":
    get_ai_engine()
    print("✅ AI Engine ready")