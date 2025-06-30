"""
database.py
Database management for the Restaurant Recommendation System
"""

import sqlite3
import json
import logging
from typing import List, Optional
from datetime import datetime
from geopy.distance import geodesic

from models import Restaurant, UserProfile

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Handles all database operations"""
    
    def __init__(self, db_path: str = "restaurant_recommendations.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Restaurants table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS restaurants (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    cuisine_type TEXT,
                    vibes TEXT,
                    latitude REAL,
                    longitude REAL,
                    address TEXT,
                    city TEXT,
                    state TEXT,
                    neighborhood TEXT,
                    google_place_id TEXT,
                    user_rating REAL,
                    google_rating REAL,
                    price_level INTEGER,
                    features TEXT,
                    reviews_summary TEXT,
                    menu_items TEXT,
                    revisit_preference TEXT,
                    notes TEXT,
                    last_updated TIMESTAMP,
                    data_source TEXT
                )
            ''')
            
            # User profiles table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id TEXT PRIMARY KEY,
                    cuisine_preferences TEXT,
                    price_preferences TEXT,
                    vibe_preferences TEXT,
                    location_history TEXT,
                    rating_patterns TEXT,
                    favorite_dishes TEXT,
                    last_updated TIMESTAMP
                )
            ''')
            
            # User restaurant interactions
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_restaurant_interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    restaurant_id TEXT,
                    rating REAL,
                    visited_date TIMESTAMP,
                    context TEXT,
                    notes TEXT,
                    FOREIGN KEY (user_id) REFERENCES user_profiles (user_id),
                    FOREIGN KEY (restaurant_id) REFERENCES restaurants (id)
                )
            ''')
            
            conn.commit()
            logger.info("Database initialized successfully")
    
    def save_restaurant(self, restaurant: Restaurant):
        """Save restaurant to database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO restaurants 
                (id, name, cuisine_type, vibes, latitude, longitude, address, city, state,
                 neighborhood, google_place_id, user_rating, google_rating, price_level, 
                 features, reviews_summary, menu_items, revisit_preference, notes,
                 last_updated, data_source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                restaurant.id, restaurant.name, json.dumps(restaurant.cuisine_type),
                json.dumps(restaurant.vibes), restaurant.location.get('lat'),
                restaurant.location.get('lng'), restaurant.location.get('address'),
                restaurant.location.get('city'), restaurant.location.get('state'),
                restaurant.neighborhood, restaurant.google_place_id,
                restaurant.user_rating, restaurant.google_rating, restaurant.price_level,
                json.dumps(restaurant.features), restaurant.reviews_summary,
                json.dumps(restaurant.menu_items), restaurant.revisit_preference,
                restaurant.notes, restaurant.last_updated, 'csv_import'
            ))
            conn.commit()
    
    def get_restaurants_by_location(self, lat: float, lng: float, radius_km: float = 25) -> List[Restaurant]:
        """Get restaurants within radius of location"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM restaurants 
                WHERE latitude IS NOT NULL AND longitude IS NOT NULL
            ''')
            
            restaurants = []
            for row in cursor.fetchall():
                rest_lat, rest_lng = row[4], row[5]
                if rest_lat and rest_lng:
                    distance = geodesic((lat, lng), (rest_lat, rest_lng)).kilometers
                    if distance <= radius_km:
                        restaurants.append(self._row_to_restaurant(row))
            
            return restaurants
    
    def get_all_restaurants(self) -> List[Restaurant]:
        """Get all restaurants from database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM restaurants')
            return [self._row_to_restaurant(row) for row in cursor.fetchall()]
    
    def get_restaurant_by_id(self, restaurant_id: str) -> Optional[Restaurant]:
        """Get a specific restaurant by ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM restaurants WHERE id = ?', (restaurant_id,))
            row = cursor.fetchone()
            return self._row_to_restaurant(row) if row else None
    
    def save_user_profile(self, profile: UserProfile):
        """Save user profile to database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO user_profiles 
                (user_id, cuisine_preferences, price_preferences, vibe_preferences,
                 location_history, rating_patterns, favorite_dishes, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                profile.user_id, json.dumps(profile.cuisine_preferences),
                json.dumps(profile.price_preferences), json.dumps(profile.vibe_preferences),
                json.dumps(profile.location_history), json.dumps(profile.rating_patterns),
                json.dumps(profile.favorite_dishes), profile.last_updated
            ))
            conn.commit()
    
    def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """Get user profile from database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM user_profiles WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()
            if row:
                return UserProfile(
                    user_id=row[0],
                    cuisine_preferences=json.loads(row[1]) if row[1] else {},
                    price_preferences=json.loads(row[2]) if row[2] else {},
                    vibe_preferences=json.loads(row[3]) if row[3] else {},
                    location_history=json.loads(row[4]) if row[4] else [],
                    rating_patterns=json.loads(row[5]) if row[5] else {},
                    favorite_dishes=json.loads(row[6]) if row[6] else [],
                    last_updated=datetime.fromisoformat(row[7])
                )
        return None
    
    def save_user_interaction(self, user_id: str, restaurant_id: str, rating: float,
                            visited_date: datetime, context: str = None, notes: str = None):
        """Save user-restaurant interaction"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO user_restaurant_interactions 
                (user_id, restaurant_id, rating, visited_date, context, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, restaurant_id, rating, visited_date, context, notes))
            conn.commit()
    
    def get_user_interactions(self, user_id: str) -> List[dict]:
        """Get all interactions for a user"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT uir.*, r.name, r.cuisine_type, r.city
                FROM user_restaurant_interactions uir
                JOIN restaurants r ON uir.restaurant_id = r.id
                WHERE uir.user_id = ?
                ORDER BY uir.visited_date DESC
            ''', (user_id,))
            
            interactions = []
            for row in cursor.fetchall():
                interactions.append({
                    'id': row[0],
                    'user_id': row[1],
                    'restaurant_id': row[2],
                    'rating': row[3],
                    'visited_date': row[4],
                    'context': row[5],
                    'notes': row[6],
                    'restaurant_name': row[7],
                    'cuisine_type': json.loads(row[8]) if row[8] else [],
                    'city': row[9]
                })
            
            return interactions
    
    def _row_to_restaurant(self, row) -> Restaurant:
        """Convert database row to Restaurant object"""
        return Restaurant(
            id=row[0], name=row[1], 
            cuisine_type=json.loads(row[2]) if row[2] else [],
            vibes=json.loads(row[3]) if row[3] else [],
            location={
                'lat': row[4], 'lng': row[5], 'address': row[6],
                'city': row[7], 'state': row[8]
            },
            neighborhood=row[9], google_place_id=row[10], user_rating=row[11], 
            google_rating=row[12], price_level=row[13], 
            features=json.loads(row[14]) if row[14] else {},
            reviews_summary=row[15], 
            menu_items=json.loads(row[16]) if row[16] else [],
            revisit_preference=row[17], notes=row[18],
            last_updated=datetime.fromisoformat(row[19])
        )