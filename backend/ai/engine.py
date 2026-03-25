"""
FINDORA - Production AI Engine v4
- Image matching  : CLIP (clip-vit-base-patch32) via transformers — ~380MB RAM
- Text matching   : sentence-transformers (all-MiniLM-L6-v2) — already in requirements
- NO TensorFlow   : runs fine on Render free tier (512MB)
- Cloudinary URLs : downloaded on-the-fly for feature extraction
"""

import os
import io
import tempfile
import numpy as np
from typing import List, Dict, Optional
from datetime import datetime


# =========================================================
# PRODUCTION AI ENGINE
# =========================================================
class ProductionAIEngine:

    def __init__(self):
        self.clip_model      = None
        self.clip_processor  = None
        self.text_model      = None
        self._loaded         = False

        print("🚀 Initialising Production AI Engine (CLIP + SentenceTransformers)...")
        self._load_models()

    # ─────────────────────────────────────────────────────
    # MODEL LOADING
    # ─────────────────────────────────────────────────────
    def _load_models(self):
        # ── CLIP for image (and cross-modal) similarity ───────────────────
        try:
            from transformers import CLIPProcessor, CLIPModel
            print("   📥 Loading CLIP model (first run downloads ~600MB, cached after)...")
            self.clip_model     = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
            self.clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
            self.clip_model.eval()
            print("   ✅ CLIP loaded")
        except Exception as e:
            print(f"   ❌ CLIP load failed: {e}")
            self.clip_model = None

        # ── SentenceTransformers for pure text similarity ─────────────────
        try:
            from sentence_transformers import SentenceTransformer
            self.text_model = SentenceTransformer("all-MiniLM-L6-v2")
            print("   ✅ SentenceTransformer loaded")
        except Exception as e:
            print(f"   ❌ SentenceTransformer load failed: {e}")
            self.text_model = None

        self._loaded = self.clip_model is not None or self.text_model is not None
        if self._loaded:
            print("✅ AI Engine ready")
        else:
            print("❌ AI Engine could not load any models — falling back to keyword matching")

    # ─────────────────────────────────────────────────────
    # IMAGE HELPERS
    # ─────────────────────────────────────────────────────
    def _load_pil_image(self, image_path: str):
        """Load a PIL Image from a Cloudinary URL or local path."""
        from PIL import Image

        if image_path.startswith("http://") or image_path.startswith("https://"):
            import requests
            resp = requests.get(image_path, timeout=15)
            resp.raise_for_status()
            return Image.open(io.BytesIO(resp.content)).convert("RGB")

        # Local path
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")
        return Image.open(image_path).convert("RGB")

    # ─────────────────────────────────────────────────────
    # FEATURE EXTRACTION
    # ─────────────────────────────────────────────────────
    def extract_image_features(self, image_path: str) -> Optional[np.ndarray]:
        """Extract CLIP image embedding (512-d, L2-normalised)."""
        if not image_path or self.clip_model is None:
            return None
        try:
            import torch
            img    = self._load_pil_image(image_path)
            inputs = self.clip_processor(images=img, return_tensors="pt")
            with torch.no_grad():
                feats = self.clip_model.get_image_features(**inputs)
                feats = feats / feats.norm(dim=-1, keepdim=True)   # L2 normalise
            return feats.squeeze().numpy()
        except Exception as e:
            print(f"   ❌ Image feature error ({image_path[:60]}…): {e}")
            return None

    def extract_text_embedding(self, text: str) -> Optional[np.ndarray]:
        """Extract SentenceTransformer embedding (384-d, L2-normalised)."""
        if not text or self.text_model is None:
            return None
        try:
            text = " ".join(text.lower().split())
            emb  = self.text_model.encode(text, convert_to_numpy=True)
            norm = np.linalg.norm(emb)
            return emb / norm if norm > 0 else emb
        except Exception as e:
            print(f"   ❌ Text embedding error: {e}")
            return None

    # ─────────────────────────────────────────────────────
    # SCORING
    # ─────────────────────────────────────────────────────
    def _cosine(self, a: np.ndarray, b: np.ndarray) -> float:
        """Cosine similarity mapped to [0, 1]."""
        dot  = float(np.dot(a, b))
        norm = float(np.linalg.norm(a) * np.linalg.norm(b))
        raw  = dot / norm if norm > 0 else 0.0
        return (raw + 1.0) / 2.0   # map [-1,1] → [0,1]

    def _location_score(self, lat1, lon1, lat2, lon2, max_km: float = 10) -> float:
        if not all([lat1, lon1, lat2, lon2]):
            return 0.5
        from math import radians, sin, cos, sqrt, atan2
        R = 6371
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat, dlon = lat2 - lat1, lon2 - lon1
        a    = sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
        dist = R * (2 * atan2(sqrt(a), sqrt(1 - a)))
        return 0.0 if dist > max_km else float(np.exp(-dist / (max_km / 3)))

    # ─────────────────────────────────────────────────────
    # MATCH SINGLE PAIR
    # ─────────────────────────────────────────────────────
    def match_items(self, item1: Dict, item2: Dict, threshold: float = 0.60) -> Dict:
        image_sim = 0.0
        text_sim  = 0.0

        # ── Image similarity (CLIP) ───────────────────────────────────────
        f1, f2 = None, None

        if item1.get("image_features"):
            f1 = np.array(item1["image_features"])
        elif item1.get("image_path"):
            f1 = self.extract_image_features(item1["image_path"])

        if item2.get("image_features"):
            f2 = np.array(item2["image_features"])
        elif item2.get("image_path"):
            f2 = self.extract_image_features(item2["image_path"])

        if f1 is not None and f2 is not None:
            image_sim = self._cosine(f1, f2)

        # ── Text similarity (SentenceTransformers) ────────────────────────
        e1, e2 = None, None

        if item1.get("text_embedding"):
            e1 = np.array(item1["text_embedding"])
        else:
            e1 = self.extract_text_embedding(
                f"{item1.get('title','')} {item1.get('description','')}"
            )

        if item2.get("text_embedding"):
            e2 = np.array(item2["text_embedding"])
        else:
            e2 = self.extract_text_embedding(
                f"{item2.get('title','')} {item2.get('description','')}"
            )

        if e1 is not None and e2 is not None:
            text_sim = self._cosine(e1, e2)

        # ── Category bonus ────────────────────────────────────────────────
        cat_bonus = 0.10 if item1.get("category") == item2.get("category") else -0.05

        # ── Location score ────────────────────────────────────────────────
        loc = self._location_score(
            item1.get("latitude"),  item1.get("longitude"),
            item2.get("latitude"),  item2.get("longitude"),
        )

        # ── Temporal score ────────────────────────────────────────────────
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

        # ── Final confidence ──────────────────────────────────────────────
        confidence = (
            image_sim  * 0.40 +
            text_sim   * 0.35 +
            loc        * 0.15 +
            time_score * 0.10 +
            cat_bonus
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

    # ─────────────────────────────────────────────────────
    # BATCH MATCH
    # ─────────────────────────────────────────────────────
    def batch_match(
        self,
        query_item:      Dict,
        candidates:      Optional[List[Dict]] = None,
        candidate_items: Optional[List[Dict]] = None,
        threshold:       float = 0.60,
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


# ─────────────────────────────────────────────────────────
# SINGLETON
# ─────────────────────────────────────────────────────────
_engine: Optional[ProductionAIEngine] = None

def get_ai_engine() -> ProductionAIEngine:
    global _engine
    if _engine is None:
        _engine = ProductionAIEngine()
    return _engine


if __name__ == "__main__":
    get_ai_engine()
    print("✅ AI Engine ready")