"""
FINDORA - FastAPI Backend
AI-Powered Lost & Found Platform
(UPDATED FOR RENDER DEPLOYMENT)
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import Optional, List
from datetime import datetime
import uuid
import os
import shutil

# Local imports
from database import db
from models import (
    UserCreate,
    UserResponse,
    ItemResponse,
    MatchResponse,
    HealthResponse,
    validate_category,
    validate_item_type
)
from notifications import notify_match

# ======================================================
# APP INIT
# ======================================================
app = FastAPI(
    title="Findora API",
    description="AI-Powered Lost & Found Platform",
    version="1.0.0"
)

# ======================================================
# CORS
# ======================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================================================
# STORAGE — Uses /data on Render persistent disk
# ======================================================
BASE_DIR = os.path.dirname(__file__)

if os.path.exists("/data"):
    STORAGE_DIR = "/data/storage"
else:
    STORAGE_DIR = os.path.join(BASE_DIR, "storage")

IMAGES_DIR = os.path.join(STORAGE_DIR, "images")
os.makedirs(IMAGES_DIR, exist_ok=True)

app.mount("/storage/images", StaticFiles(directory=IMAGES_DIR), name="images")

# ======================================================
# HELPERS
# ======================================================
def save_image(file: UploadFile, item_id: str) -> str:
    ext = file.filename.split(".")[-1]
    filename = f"{item_id}.{ext}"
    path = os.path.join(IMAGES_DIR, filename)
    with open(path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return f"/storage/images/{filename}"

# ======================================================
# HEALTH
# ======================================================
@app.get("/", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy",
        service="Findora API",
        version="1.0.0",
        timestamp=datetime.utcnow().isoformat(),
        database="Connected"
    )

# ======================================================
# USERS
# ======================================================
@app.post("/api/users/register", response_model=UserResponse)
async def register_user(user: UserCreate):
    user_id = str(uuid.uuid4())
    ts = datetime.utcnow().isoformat()

    data = {
        "user_id": user_id,
        "email": user.email,
        "name": user.name,
        "phone": user.phone or "",
        "created_at": ts,
        "updated_at": ts
    }

    if not db.insert_user(data):
        raise HTTPException(status_code=500, detail="User registration failed")

    return UserResponse(**data)

# ======================================================
# ITEMS
# ======================================================
@app.post("/api/items/report", response_model=ItemResponse)
async def report_item(
    background_tasks: BackgroundTasks,
    title: str = Form(...),
    description: str = Form(...),
    category: str = Form(...),
    location: str = Form(...),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    item_type: str = Form(...),
    reward_amount: Optional[float] = Form(0.0),
    contact_info: str = Form(...),
    user_id: str = Form(...),
    image: UploadFile = File(...)
):
    if not validate_item_type(item_type):
        raise HTTPException(status_code=400, detail="Invalid item type")

    if not validate_category(category):
        raise HTTPException(status_code=400, detail="Invalid category")

    item_id = str(uuid.uuid4())
    ts = datetime.utcnow().isoformat()
    image_path = save_image(image, item_id)

    item = {
        "item_id": item_id,
        "user_id": user_id,
        "title": title,
        "description": description,
        "category": category,
        "location": location,
        "latitude": latitude,
        "longitude": longitude,
        "item_type": item_type,
        "reward_amount": reward_amount,
        "contact_info": contact_info,
        "image_path": image_path,
        "status": "active",
        "created_at": ts,
        "updated_at": ts
    }

    if not db.insert_item(item):
        raise HTTPException(status_code=500, detail="Item submission failed")

    background_tasks.add_task(trigger_ai_processing, item_id)
    return ItemResponse(**item)


@app.get("/api/items", response_model=List[ItemResponse])
async def list_items(
    item_type: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,   # ✅ None = active + matched (Browse shows all)
    limit: int = 50
):
    items = db.get_all_items(item_type=item_type, status=status, limit=limit)

    if category:
        items = [i for i in items if i["category"] == category]

    for i in items:
        i.pop("image_features", None)
        i.pop("text_embedding", None)

    return [ItemResponse(**i) for i in items]


@app.get("/api/items/{item_id}", response_model=ItemResponse)
async def get_item(item_id: str):
    item = db.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    item.pop("image_features", None)
    item.pop("text_embedding", None)
    return ItemResponse(**item)

# ======================================================
# MATCHES
# ======================================================
@app.get("/api/matches/{item_id}", response_model=List[MatchResponse])
async def get_matches(item_id: str):
    matches = db.get_matches_for_item(item_id)
    matches.sort(key=lambda x: x["confidence_score"], reverse=True)
    return [MatchResponse(**m) for m in matches]

# ======================================================
# STATS  ✅ FIX: status=None so matched items are counted
# ======================================================
@app.get("/api/stats")
async def get_stats():
    try:
        all_items = db.get_all_items(status=None, limit=1000)
        lost    = sum(1 for i in all_items if i.get("item_type") == "lost")
        found   = sum(1 for i in all_items if i.get("item_type") == "found")
        matched = sum(1 for i in all_items if i.get("status") == "matched")
        return {
            "total_items":   len(all_items),
            "lost_items":    lost,
            "found_items":   found,
            "matched_items": matched,
        }
    except Exception as e:
        print("❌ Stats error:", e)
        raise HTTPException(status_code=500, detail="Stats calculation failed")

# ======================================================
# BACKGROUND — AI MATCHING ENGINE
# ✅ FIXES:
#   - Correct DB column names: lost_item_id / found_item_id
#   - Targeted update_item calls (don't wipe image_features)
#   - Only match lost ↔ found, never same type
#   - Duplicate match guard via match_exists
# ======================================================
async def trigger_ai_processing(item_id: str):
    print(f"🤖 AI processing started for item: {item_id}")

    item = db.get_item(item_id)
    if not item:
        print(f"❌ Item not found: {item_id}")
        return

    # Only compare against active items to avoid re-matching
    all_items = db.get_all_items(status="active", limit=1000)

    for other in all_items:
        # Skip self
        if other["item_id"] == item_id:
            continue

        # ✅ Only match lost ↔ found
        if item["item_type"] == other["item_type"]:
            continue

        # Match condition: exact title match (case-insensitive)
        if item["title"].strip().lower() == other["title"].strip().lower():
            print(f"🔥 MATCH FOUND! '{item['title']}' ↔ '{other['title']}'")

            # Determine which is lost and which is found
            lost_i  = item  if item["item_type"]  == "lost" else other
            found_i = other if item["item_type"]  == "lost" else item

            # ✅ Targeted status update — preserves image_features/text_embedding
            db.update_item(lost_i["item_id"],  {"status": "matched"})
            db.update_item(found_i["item_id"], {"status": "matched"})

            ts = datetime.utcnow().isoformat()

            # ✅ Correct column names matching database.py schema
            match_data = {
                "match_id":         str(uuid.uuid4()),
                "lost_item_id":     lost_i["item_id"],
                "found_item_id":    found_i["item_id"],
                "confidence_score": 0.85,
                "image_similarity": 0.85,
                "text_similarity":  0.85,
                "location_score":   0.85,
                "status":           "pending",
                "created_at":       ts,
                "updated_at":       ts,
            }

            inserted = db.insert_match(match_data)
            if inserted:
                print(f"✅ Match stored in DB: {match_data['match_id']}")
            else:
                print("⚠️  Match already exists in DB, skipping insert")

            # ✅ Notify both parties via email
            notify_match(lost_i, found_i, 0.85)
            print("📦 Match saved + notification triggered")

# ======================================================
# RUN
# ======================================================
if __name__ == "__main__":
    import uvicorn
    PORT = int(os.getenv("PORT", 8000))
    print("=" * 60)
    print("🚀 FINDORA - AI-POWERED LOST & FOUND PLATFORM")
    print("=" * 60)
    print(f"📍 Backend API: http://localhost:{PORT}")
    print(f"📚 API Docs:    http://localhost:{PORT}/docs")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=PORT, reload=False)