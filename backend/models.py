# backend/models.py
"""
Pydantic Models for Findora
Data validation and serialization
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime

# ==================== REQUEST MODELS ====================

class UserCreate(BaseModel):
    """User registration model"""
    email: EmailStr
    name: str = Field(..., min_length=2, max_length=100)
    phone: Optional[str] = None

class ItemCreate(BaseModel):
    """Item creation model"""
    title: str = Field(..., min_length=3, max_length=100)
    description: str = Field(..., min_length=10, max_length=1000)
    category: str = Field(..., description="wallet, phone, bag, keys, etc.")
    location: str = Field(..., min_length=3, max_length=200)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    item_type: str = Field(..., description="lost or found")
    reward_amount: Optional[float] = 0.0
    contact_info: str = Field(..., min_length=5, max_length=100)

# ==================== RESPONSE MODELS ====================

class UserResponse(BaseModel):
    """User response model"""
    user_id: str
    email: str
    name: str
    phone: Optional[str]
    created_at: str
    updated_at: str

class ItemResponse(BaseModel):
    """Item response model"""
    item_id: str
    user_id: str
    title: str
    description: str
    category: str
    location: str
    latitude: Optional[float]
    longitude: Optional[float]
    item_type: str
    reward_amount: float
    contact_info: str
    image_path: Optional[str]
    status: str
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True

class MatchResponse(BaseModel):
    """Match response model"""
    match_id: str
    lost_item_id: str
    found_item_id: str
    confidence_score: float
    image_similarity: float
    text_similarity: float
    location_score: float
    status: str
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True

class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    service: str
    version: str
    timestamp: str
    database: str = "connected"

# ==================== INTERNAL MODELS ====================

class AIFeatures(BaseModel):
    """AI features for an item"""
    image_features: Optional[List[float]] = None
    text_embedding: Optional[List[float]] = None

class MatchScore(BaseModel):
    """Match scoring details"""
    image_similarity: float
    text_similarity: float
    location_score: float
    confidence_score: float
    threshold: float

# ==================== VALIDATION ====================

VALID_CATEGORIES = [
    'wallet', 'phone', 'keys', 'bag', 'jewelry', 
    'documents', 'electronics', 'clothing', 'accessories', 'other'
]

VALID_ITEM_TYPES = ['lost', 'found']

VALID_STATUSES = ['active', 'matched', 'closed']

VALID_MATCH_STATUSES = ['pending', 'accepted', 'rejected']

def validate_category(category: str) -> bool:
    """Validate item category"""
    return category.lower() in VALID_CATEGORIES

def validate_item_type(item_type: str) -> bool:
    """Validate item type"""
    return item_type.lower() in VALID_ITEM_TYPES

def validate_status(status: str) -> bool:
    """Validate item status"""
    return status.lower() in VALID_STATUSES
