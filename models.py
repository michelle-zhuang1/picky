"""
models.py
Core data models for the Restaurant Recommendation System
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime

@dataclass
class Restaurant:
    """Core restaurant data model"""
    id: str
    name: str
    cuisine_type: List[str]
    location: Dict[str, Any]  # lat, lng, address, city, state
    vibes: List[str] = field(default_factory=list)
    google_place_id: Optional[str] = None
    user_rating: Optional[float] = None
    google_rating: Optional[float] = None
    price_level: Optional[int] = None  # 1-4 scale
    features: Dict[str, Any] = field(default_factory=dict)
    reviews_summary: Optional[str] = None
    menu_items: List[str] = field(default_factory=list)
    revisit_preference: Optional[str] = None
    notes: Optional[str] = None
    neighborhood: Optional[str] = None
    last_updated: datetime = field(default_factory=datetime.now)

@dataclass
class UserProfile:
    """User preference profile model"""
    user_id: str
    cuisine_preferences: Dict[str, float] = field(default_factory=dict)
    price_preferences: Dict[int, float] = field(default_factory=dict)
    vibe_preferences: Dict[str, float] = field(default_factory=dict)
    location_history: List[Dict] = field(default_factory=list)
    rating_patterns: Dict[str, Any] = field(default_factory=dict)
    favorite_dishes: List[str] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)

@dataclass
class Recommendation:
    """Recommendation result model"""
    restaurant: Restaurant
    score: float
    reasoning: str
    distance_km: Optional[float] = None