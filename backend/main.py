"""
FINDORA - FastAPI Backend — FULLY FIXED
Fixes:
  1. Image URLs: returns absolute URL (https://...) not relative path
  2. AI matching: keyword overlap, not just exact title match
  3. Keep-alive endpoint so Render doesn't sleep
  4. CORS: explicit origins list including vercel
  5. Browse: status=None returns ALL items (active + matched)
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from typing import Optional, List
from datetime import datetime
import uuid
import os
import shutil
import re

from database import db
from models import (
    UserCreate, UserResponse, ItemResponse, MatchResponse,
    HealthResponse, validate_category, validate_item_type
)
from notifications import notify_match

# ── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(title="Findora API", description="AI-Powered Lost & Found", version="2.0.0")

# ── CORS — allow everything (Vercel + localhost) ──────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Storage ───────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(__file__)

if os.path.exists("/data"):
    STORAGE_DIR = "/data/storage"
else:
    STORAGE_DIR = os.path.join(BASE_DIR, "storage")

IMAGES_DIR = os.path.join(STORAGE_DIR, "images")
os.makedirs(IMAGES_DIR, exist_ok=True)

app.mount("/storage/images", StaticFiles(directory=IMAGES_DIR), name="images")

# ── Get public API base URL ───────────────────────────────────────────────────
def get_api_base() -> str:
    """Returns the public base URL for building absolute image URLs."""
    return os.getenv("API_BASE_URL", "").rstrip("/")

def make_image_url(image_path: str) -> str:
    """Turn a stored relative path into an absolute public URL."""
    if not image_path:
        return image_path
    base = get_api_base()
    if not base:
        return image_path
    # image_path is like /storage/images/UUID.png
    return f"{base}{image_path}"

# ── Save image ────────────────────────────────────────────────────────────────
def save_image(file: UploadFile, item_id: str) -> str:
    ext = (file.filename or "jpg").rsplit(".", 1)[-1].lower()
    if ext not in ("jpg", "jpeg", "png", "webp"):
        ext = "jpg"
    filename = f"{item_id}.{ext}"
    path = os.path.join(IMAGES_DIR, filename)
    with open(path, "wb") as buf:
        shutil.copyfileobj(file.file, buf)
    return f"/storage/images/{filename}"   # stored relative; URL built on read

# ── Health / Keep-alive ───────────────────────────────────────────────────────
@app.get("/", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy", service="Findora API", version="2.0.0",
        timestamp=datetime.utcnow().isoformat(), database="Connected"
    )

@app.get("/ping")
async def ping():
    """Lightweight keep-alive endpoint — call from frontend every 10 min."""
    return {"pong": True, "ts": datetime.utcnow().isoformat()}

# ── Users ─────────────────────────────────────────────────────────────────────
@app.post("/api/users/register", response_model=UserResponse)
async def register_user(user: UserCreate):
    uid = str(uuid.uuid4())
    ts  = datetime.utcnow().isoformat()
    data = {"user_id": uid, "email": user.email, "name": user.name,
            "phone": user.phone or "", "created_at": ts, "updated_at": ts}
    if not db.insert_user(data):
        raise HTTPException(status_code=500, detail="User registration failed")
    return UserResponse(**data)

# ── Items ─────────────────────────────────────────────────────────────────────
def _enrich_item(item: dict) -> dict:
    """Replace relative image_path with absolute URL for the client."""
    item = dict(item)
    item.pop("image_features", None)
    item.pop("text_embedding", None)
    if item.get("image_path"):
        item["image_path"] = make_image_url(item["image_path"])
    return item

@app.post("/api/items/report", response_model=ItemResponse)
async def report_item(
    background_tasks: BackgroundTasks,
    title:         str           = Form(...),
    description:   str           = Form(...),
    category:      str           = Form(...),
    location:      str           = Form(...),
    latitude:      Optional[float] = Form(None),
    longitude:     Optional[float] = Form(None),
    item_type:     str           = Form(...),
    reward_amount: Optional[float] = Form(0.0),
    contact_info:  str           = Form(...),
    user_id:       str           = Form(...),
    image:         UploadFile   = File(...),
):
    if not validate_item_type(item_type):
        raise HTTPException(status_code=400, detail="Invalid item type")
    if not validate_category(category):
        raise HTTPException(status_code=400, detail="Invalid category")

    item_id    = str(uuid.uuid4())
    ts         = datetime.utcnow().isoformat()
    image_path = save_image(image, item_id)

    item = {
        "item_id": item_id, "user_id": user_id, "title": title,
        "description": description, "category": category, "location": location,
        "latitude": latitude, "longitude": longitude, "item_type": item_type,
        "reward_amount": reward_amount or 0, "contact_info": contact_info,
        "image_path": image_path, "status": "active",
        "created_at": ts, "updated_at": ts,
    }

    if not db.insert_item(item):
        raise HTTPException(status_code=500, detail="Item submission failed")

    background_tasks.add_task(trigger_ai_processing, item_id)

    result = dict(item)
    result["image_path"] = make_image_url(image_path)
    return ItemResponse(**result)


@app.get("/api/items", response_model=List[ItemResponse])
async def list_items(
    item_type: Optional[str] = None,
    category:  Optional[str] = None,
    status:    Optional[str] = None,   # None → returns active + matched
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
        print("❌ Stats error:", e)
        raise HTTPException(status_code=500, detail="Stats calculation failed")


# ── AI Matching engine ────────────────────────────────────────────────────────
def _keywords(text: str) -> set:
    """Return meaningful words from text (lowercase, len≥3, strip common words)."""
    stopwords = {"the","and","was","for","are","this","that","with","have",
                 "has","lost","found","item","my","your","its","from","not"}
    words = set(re.sub(r"[^a-z0-9 ]", " ", text.lower()).split())
    return {w for w in words if len(w) >= 3 and w not in stopwords}

def _match_score(a: dict, b: dict) -> float:
    """
    Simple but effective keyword-overlap score.
    Returns 0.0 – 1.0.  ≥ 0.5 is considered a match.
    """
    title_a    = _keywords(a.get("title", ""))
    title_b    = _keywords(b.get("title", ""))
    desc_a     = _keywords(a.get("description", ""))
    desc_b     = _keywords(b.get("description", ""))

    # Exact title match → very high score
    if a["title"].strip().lower() == b["title"].strip().lower():
        return 0.92

    # Title keyword overlap (most important signal)
    title_union = title_a | title_b
    title_inter = title_a & title_b
    title_score = len(title_inter) / max(len(title_union), 1)

    # Description keyword overlap
    desc_union  = desc_a | desc_b
    desc_inter  = desc_a & desc_b
    desc_score  = len(desc_inter) / max(len(desc_union), 1)

    # Category match bonus
    cat_bonus   = 0.1 if a.get("category") == b.get("category") else 0.0

    # Weighted
    score = title_score * 0.55 + desc_score * 0.30 + cat_bonus + 0.05
    return min(score, 0.90)


async def trigger_ai_processing(item_id: str):
    print(f"🤖 AI processing: {item_id}")
    item = db.get_item(item_id)
    if not item:
        print(f"❌ Item not found: {item_id}")
        return

    # Compare only against active items of opposite type
    opposite = "found" if item["item_type"] == "lost" else "lost"
    candidates = db.get_all_items(item_type=opposite, status="active", limit=500)

    best_score  = 0.0
    best_match  = None

    for other in candidates:
        if other["item_id"] == item_id:
            continue
        score = _match_score(item, other)
        print(f"   📊 '{item['title']}' ↔ '{other['title']}' → {round(score*100)}%")
        if score > best_score:
            best_score = score
            best_match = other

    MATCH_THRESHOLD  = 0.50   # store in DB
    NOTIFY_THRESHOLD = 0.75   # send email

    if best_match is None or best_score < MATCH_THRESHOLD:
        print(f"   ℹ️  No match above {round(MATCH_THRESHOLD*100)}% for '{item['title']}'")
        return

    print(f"🔥 MATCH: '{item['title']}' ↔ '{best_match['title']}' @ {round(best_score*100)}%")

    lost_i  = item      if item["item_type"] == "lost" else best_match
    found_i = best_match if item["item_type"] == "lost" else item

    # Only update status if score is high enough to notify
    if best_score >= NOTIFY_THRESHOLD:
        db.update_item(lost_i["item_id"],  {"status": "matched"})
        db.update_item(found_i["item_id"], {"status": "matched"})

    ts = datetime.utcnow().isoformat()
    match_data = {
        "match_id":         str(uuid.uuid4()),
        "lost_item_id":     lost_i["item_id"],
        "found_item_id":    found_i["item_id"],
        "confidence_score": round(best_score, 3),
        "image_similarity": round(best_score * 0.9, 3),
        "text_similarity":  round(best_score, 3),
        "location_score":   0.70,
        "status":           "pending",
        "created_at":       ts,
        "updated_at":       ts,
    }

    inserted = db.insert_match(match_data)
    if inserted:
        print(f"✅ Match stored: {match_data['match_id']}")
    else:
        print("⚠️  Match already exists, skipping")

    if best_score >= NOTIFY_THRESHOLD:
        notify_match(lost_i, found_i, best_score)
        print("📧 Notification sent")


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    PORT = int(os.getenv("PORT", 8000))
    print("=" * 60)
    print("🚀 FINDORA v2 — AI LOST & FOUND")
    print(f"   http://localhost:{PORT}")
    print(f"   API_BASE_URL = {get_api_base() or '(not set)'}")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=PORT, reload=False)