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
    is_wishlist: bool = False  # True if this is a restaurant the user wants to try
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

@dataclass
class RecommendationSession:
    """Interactive recommendation session model"""
    session_id: str
    user_id: str
    location: Dict[str, Any]  # city, state, lat, lng
    shown_restaurant_ids: List[str] = field(default_factory=list)
    liked_restaurant_ids: List[str] = field(default_factory=list)
    disliked_restaurant_ids: List[str] = field(default_factory=list)
    session_preferences: Dict[str, Any] = field(default_factory=dict)  # temporary preferences for this session
    filters: Dict[str, List[str]] = field(default_factory=dict)  # cuisine_filter, vibe_filter
    cached_live_restaurants: List[str] = field(default_factory=list)  # IDs of live restaurants fetched for this session
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)