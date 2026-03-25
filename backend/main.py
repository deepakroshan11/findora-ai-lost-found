"""
FINDORA - FastAPI Backend v3
- Database  : PostgreSQL via Supabase  (persistent across Render restarts)
- Images    : Cloudinary CDN           (persistent, absolute URLs)
- AI Match  : keyword engine (fast) + background AI agent (deep)
- Email     : Gmail SMTP via notifications.py
- Keep-alive: /ping endpoint (frontend pings every 8 min)
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional, List
from datetime import datetime
import uuid
import os
import re
import cloudinary
import cloudinary.uploader

from database import db
from models import (
    UserCreate, UserResponse, ItemResponse, MatchResponse,
    HealthResponse, validate_category, validate_item_type,
)
from notifications import notify_match

# ── Cloudinary config ─────────────────────────────────────────────────────────
cloudinary.config(
    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key    = os.getenv("CLOUDINARY_API_KEY"),
    api_secret = os.getenv("CLOUDINARY_API_SECRET"),
    secure     = True,
)

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title       = "Findora API",
    description = "AI-Powered Lost & Found",
    version     = "3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],
    allow_credentials = False,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# ── Image helpers ─────────────────────────────────────────────────────────────

def save_image(file: UploadFile, item_id: str) -> str:
    """Upload image to Cloudinary and return the permanent https:// URL."""
    result = cloudinary.uploader.upload(
        file.file,
        public_id     = f"findora/{item_id}",
        overwrite     = True,
        resource_type = "image",
        folder        = "findora",
    )
    return result["secure_url"]   # permanent CDN URL stored directly in DB

# ── Health / Keep-alive ───────────────────────────────────────────────────────

@app.get("/", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status    = "healthy",
        service   = "Findora API",
        version   = "3.0.0",
        timestamp = datetime.utcnow().isoformat(),
        database  = "PostgreSQL/Supabase",
    )

@app.get("/ping")
async def ping():
    """Lightweight keep-alive — frontend calls every 8 min to prevent Render sleep."""
    return {"pong": True, "ts": datetime.utcnow().isoformat()}

# ── Users ─────────────────────────────────────────────────────────────────────

@app.post("/api/users/register", response_model=UserResponse)
async def register_user(user: UserCreate):
    uid = str(uuid.uuid4())
    ts  = datetime.utcnow().isoformat()
    data = {
        "user_id":    uid,
        "email":      user.email,
        "name":       user.name,
        "phone":      user.phone or "",
        "created_at": ts,
        "updated_at": ts,
    }
    if not db.insert_user(data):
        raise HTTPException(status_code=500, detail="User registration failed")
    return UserResponse(**data)

# ── Items ─────────────────────────────────────────────────────────────────────

def _enrich_item(item: dict) -> dict:
    """Strip heavy ML fields before returning to client."""
    item = dict(item)
    item.pop("image_features", None)
    item.pop("text_embedding",  None)
    # image_path is already an absolute Cloudinary URL — no transformation needed
    return item


@app.post("/api/items/report", response_model=ItemResponse)
async def report_item(
    background_tasks: BackgroundTasks,
    title:          str            = Form(...),
    description:    str            = Form(...),
    category:       str            = Form(...),
    location:       str            = Form(...),
    latitude:       Optional[float]= Form(None),
    longitude:      Optional[float]= Form(None),
    item_type:      str            = Form(...),
    reward_amount:  Optional[float]= Form(0.0),
    contact_info:   str            = Form(...),
    user_id:        str            = Form(...),
    image:          UploadFile     = File(...),
):
    if not validate_item_type(item_type):
        raise HTTPException(status_code=400, detail="Invalid item type")
    if not validate_category(category):
        raise HTTPException(status_code=400, detail="Invalid category")

    item_id = str(uuid.uuid4())
    ts      = datetime.utcnow().isoformat()

    # Upload to Cloudinary — returns a permanent https:// URL
    try:
        image_url = save_image(image, item_id)
        print(f"✅ Image uploaded to Cloudinary: {image_url}")
    except Exception as e:
        print(f"❌ Cloudinary upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Image upload failed: {e}")

    item = {
        "item_id":       item_id,
        "user_id":       user_id,
        "title":         title,
        "description":   description,
        "category":      category,
        "location":      location,
        "latitude":      latitude,
        "longitude":     longitude,
        "item_type":     item_type,
        "reward_amount": reward_amount or 0,
        "contact_info":  contact_info,
        "image_path":    image_url,   # Cloudinary URL stored directly
        "status":        "active",
        "created_at":    ts,
        "updated_at":    ts,
    }

    if not db.insert_item(item):
        raise HTTPException(status_code=500, detail="Item submission failed")

    # Trigger both fast keyword match AND deep AI match in background
    background_tasks.add_task(trigger_fast_matching,   item_id)
    background_tasks.add_task(trigger_ai_processing,   item_id)

    return ItemResponse(**_enrich_item(item))


@app.get("/api/items", response_model=List[ItemResponse])
async def list_items(
    item_type: Optional[str] = None,
    category:  Optional[str] = None,
    status:    Optional[str] = None,   # None → active + matched (all)
    limit:     int           = 50,
):
    items = db.get_all_items(item_type=item_type, status=status, limit=limit)
    if category:
        items = [i for i in items if i["category"] == category]
    return [ItemResponse(**_enrich_item(i)) for i in items]


@app.get("/api/items/{item_id}", response_model=ItemResponse)
async def get_item(item_id: str):
    item = db.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return ItemResponse(**_enrich_item(item))

# ── Matches ───────────────────────────────────────────────────────────────────

@app.get("/api/matches/{item_id}", response_model=List[MatchResponse])
async def get_matches(item_id: str):
    matches = db.get_matches_for_item(item_id)
    matches.sort(key=lambda x: x["confidence_score"], reverse=True)
    return [MatchResponse(**m) for m in matches]

# ── Stats ─────────────────────────────────────────────────────────────────────

@app.get("/api/stats")
async def get_stats():
    try:
        all_items = db.get_all_items(status=None, limit=1000)
        return {
            "total_items":   len(all_items),
            "lost_items":    sum(1 for i in all_items if i.get("item_type") == "lost"),
            "found_items":   sum(1 for i in all_items if i.get("item_type") == "found"),
            "matched_items": sum(1 for i in all_items if i.get("status")    == "matched"),
        }
    except Exception as e:
        print(f"❌ Stats error: {e}")
        raise HTTPException(status_code=500, detail="Stats calculation failed")

# ── Fast keyword matching (always runs, no ML deps) ───────────────────────────

def _keywords(text: str) -> set:
    """Return meaningful words (lowercase, len≥2, exclude stopwords)."""
    stopwords = {
        "the","and","was","for","are","this","that","with","have",
        "has","lost","found","item","my","your","its","from","not","a","an",
    }
    words = set(re.sub(r"[^a-z0-9 ]", " ", text.lower()).split())
    return {w for w in words if len(w) >= 2 and w not in stopwords}


def _keyword_match_score(a: dict, b: dict) -> float:
    """
    Fast keyword-overlap scoring. Returns 0.0–1.0.
    Exact title match → 0.92.
    """
    if a["title"].strip().lower() == b["title"].strip().lower():
        return 0.92

    title_a = _keywords(a.get("title", ""))
    title_b = _keywords(b.get("title", ""))
    desc_a  = _keywords(a.get("description", ""))
    desc_b  = _keywords(b.get("description", ""))

    title_union = title_a | title_b
    title_score = len(title_a & title_b) / max(len(title_union), 1)

    desc_union = desc_a | desc_b
    desc_score = len(desc_a & desc_b) / max(len(desc_union), 1)

    cat_bonus = 0.10 if a.get("category") == b.get("category") else 0.0

    return min(title_score * 0.55 + desc_score * 0.30 + cat_bonus + 0.05, 0.90)


async def trigger_fast_matching(item_id: str):
    """Keyword-based matching — fast, runs immediately after submission."""
    print(f"⚡ Fast keyword matching: {item_id}")
    item = db.get_item(item_id)
    if not item:
        return

    opposite   = "found" if item["item_type"] == "lost" else "lost"
    candidates = db.get_all_items(item_type=opposite, status="active", limit=500)

    best_score = 0.0
    best_match = None

    for other in candidates:
        if other["item_id"] == item_id:
            continue
        score = _keyword_match_score(item, other)
        print(f"   📊 '{item['title']}' ↔ '{other['title']}' → {round(score*100)}%")
        if score > best_score:
            best_score = score
            best_match = other

    MATCH_THRESHOLD  = 0.50
    NOTIFY_THRESHOLD = 0.75

    if best_match is None or best_score < MATCH_THRESHOLD:
        print(f"   ℹ️  No keyword match above {round(MATCH_THRESHOLD*100)}% for '{item['title']}'")
        return

    print(f"🔥 Keyword MATCH: '{item['title']}' ↔ '{best_match['title']}' @ {round(best_score*100)}%")

    lost_i  = item       if item["item_type"] == "lost"  else best_match
    found_i = best_match if item["item_type"] == "lost"  else item

    if best_score >= NOTIFY_THRESHOLD:
        db.update_item(lost_i["item_id"],  {"status": "matched"})
        db.update_item(found_i["item_id"], {"status": "matched"})

    ts = datetime.utcnow().isoformat()
    match_data = {
        "match_id":         str(uuid.uuid4()),
        "lost_item_id":     lost_i["item_id"],
        "found_item_id":    found_i["item_id"],
        "confidence_score": round(best_score, 3),
        "image_similarity": round(best_score * 0.7, 3),
        "text_similarity":  round(best_score, 3),
        "location_score":   0.70,
        "status":           "pending",
        "created_at":       ts,
        "updated_at":       ts,
    }

    if db.insert_match(match_data):
        print(f"✅ Keyword match stored")
    else:
        print("⚠️  Match already exists — skipping")

    if best_score >= NOTIFY_THRESHOLD:
        try:
            notify_match(lost_i, found_i, best_score)
            print("📧 Notification sent (keyword match)")
        except Exception as e:
            print(f"❌ Notification error: {e}")

# ── Deep AI matching (MobileNetV3 + SentenceTransformers) ────────────────────

async def trigger_ai_processing(item_id: str):
    """
    Deep AI matching using vision + text embeddings.
    Images are now Cloudinary URLs — engine.py downloads them on the fly.
    Falls back gracefully if ML libs are unavailable (Render free tier RAM).
    """
    print(f"🤖 Deep AI processing: {item_id}")
    try:
        from ai.engine import get_ai_engine
        engine = get_ai_engine()
    except Exception as e:
        print(f"⚠️  AI engine unavailable ({e}) — keyword matching already ran")
        return

    item = db.get_item(item_id)
    if not item:
        return

    # ── Extract & store features ──────────────────────────────────────────
    image_features = None
    if item.get("image_path"):
        feats = engine.extract_image_features(item["image_path"])
        if feats is not None:
            image_features = feats.tolist()

    text = f"{item.get('title','')} {item.get('description','')}"
    text_embedding = None
    emb = engine.extract_text_embedding(text)
    if emb is not None:
        text_embedding = emb.tolist()

    if image_features and text_embedding:
        db.update_item_features(item_id, image_features, text_embedding)
        item = db.get_item(item_id)  # reload with features
    else:
        print("   ⚠️  Feature extraction incomplete — using text only for AI match")

    # ── Find AI matches ───────────────────────────────────────────────────
    opposite   = "found" if item["item_type"] == "lost" else "lost"
    candidates = db.get_all_items(item_type=opposite, status="active", limit=500)
    candidates = [c for c in candidates if c.get("image_features") and c.get("text_embedding")]

    if not candidates:
        print("   ℹ️  No candidates with features yet — keyword match already ran")
        return

    print(f"🔎 Deep AI comparing against {len(candidates)} candidate(s)...")
    matches = engine.batch_match(
        query_item      = item,
        candidate_items = candidates,
        threshold       = 0.60,
        top_k           = 5,
    )

    NOTIFY_THRESHOLD = 0.80

    for match in matches:
        matched_item = match["item"]
        confidence   = match["confidence_score"]

        lost_i  = item         if item["item_type"] == "lost"  else matched_item
        found_i = matched_item if item["item_type"] == "lost"  else item

        print(f"🔥 AI MATCH: '{lost_i['title']}' ↔ '{found_i['title']}' @ {round(confidence*100)}%")

        ts = datetime.utcnow().isoformat()
        match_data = {
            "match_id":         str(uuid.uuid4()),
            "lost_item_id":     lost_i["item_id"],
            "found_item_id":    found_i["item_id"],
            "confidence_score": round(confidence, 3),
            "image_similarity": round(match.get("image_similarity", 0), 3),
            "text_similarity":  round(match.get("text_similarity",  0), 3),
            "location_score":   round(match.get("location_score",  0.7), 3),
            "status":           "pending",
            "created_at":       ts,
            "updated_at":       ts,
        }

        inserted = db.insert_match(match_data)

        if confidence >= NOTIFY_THRESHOLD:
            db.update_item(lost_i["item_id"],  {"status": "matched"})
            db.update_item(found_i["item_id"], {"status": "matched"})
            if inserted:
                try:
                    notify_match(lost_i, found_i, confidence)
                    print("📧 Notification sent (AI match)")
                except Exception as e:
                    print(f"❌ Notification error: {e}")

# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    PORT = int(os.getenv("PORT", 8000))
    print("=" * 60)
    print("🚀 FINDORA v3 — Supabase + Cloudinary + AI Matching")
    print(f"   http://localhost:{PORT}")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=PORT, reload=False)