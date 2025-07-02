"""
database.py
Database management for the Restaurant Recommendation System
"""

import sqlite3
import json
import logging
import time
from typing import List, Optional
from datetime import datetime
from geopy.distance import geodesic

from models import Restaurant, UserProfile, RecommendationSession

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Handles all database operations"""
    
    def __init__(self, db_path: str = "restaurant_recommendations.db"):
        self.db_path = db_path
        self.init_database()
        self.migrate_database()
    
    def get_connection(self, timeout: float = 30.0, retries: int = 3):
        """Get a database connection with timeout and retry logic"""
        for attempt in range(retries):
            try:
                conn = sqlite3.connect(self.db_path, timeout=timeout)
                # Enable WAL mode for better concurrent access
                conn.execute("PRAGMA journal_mode=WAL")
                return conn
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and attempt < retries - 1:
                    wait_time = (attempt + 1) * 0.5  # Exponential backoff: 0.5s, 1s, 1.5s
                    logger.warning(f"Database locked, retrying in {wait_time}s (attempt {attempt + 1}/{retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    # Re-raise the exception with helpful context
                    if "database is locked" in str(e):
                        raise sqlite3.OperationalError(
                            "Database is locked. Please close any database browser applications (like DB Browser) "
                            "that might have the database file open, then try again."
                        ) from e
                    else:
                        raise
        
        # This shouldn't be reached, but just in case
        raise sqlite3.OperationalError("Failed to connect to database after all retries")
    
    def init_database(self):
        """Initialize database with required tables"""
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
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
                    is_wishlist BOOLEAN DEFAULT 0,
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
            
            # Recommendation sessions
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS recommendation_sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    location_data TEXT,
                    shown_restaurant_ids TEXT,
                    liked_restaurant_ids TEXT,
                    disliked_restaurant_ids TEXT,
                    session_preferences TEXT,
                    filters TEXT,
                    created_at TIMESTAMP,
                    last_activity TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES user_profiles (user_id)
                )
            ''')
            
            # Session feedback (detailed feedback tracking)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS session_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    restaurant_id TEXT,
                    feedback_type TEXT, -- 'liked', 'disliked', 'neutral'
                    feedback_details TEXT,
                    created_at TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES recommendation_sessions (session_id)
                )
            ''')
            
            conn.commit()
            logger.info("Database initialized successfully")
    
    def migrate_database(self):
        """Apply database migrations"""
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            cursor = conn.cursor()
            
            # Check if is_wishlist column exists
            cursor.execute("PRAGMA table_info(restaurants)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'is_wishlist' not in columns:
                logger.info("Adding is_wishlist column to restaurants table")
                cursor.execute("ALTER TABLE restaurants ADD COLUMN is_wishlist BOOLEAN DEFAULT 0")
                
                # Migrate existing data: restaurants added manually with revisit_preference="Yes" 
                # that have Google Place IDs (indicating they were added via the add command)
                # should be marked as wishlist items
                cursor.execute("""
                    UPDATE restaurants 
                    SET is_wishlist = 1 
                    WHERE revisit_preference = 'Yes' 
                    AND google_place_id IS NOT NULL 
                    AND data_source IS NULL
                """)
                
                conn.commit()
                logger.info("Database migration completed successfully")
    
    def save_restaurant(self, restaurant: Restaurant):
        """Save restaurant to database"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO restaurants 
                (id, name, cuisine_type, vibes, latitude, longitude, address, city, state,
                 neighborhood, google_place_id, user_rating, google_rating, price_level, 
                 features, reviews_summary, menu_items, revisit_preference, notes, is_wishlist,
                 last_updated, data_source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                restaurant.id, restaurant.name, json.dumps(restaurant.cuisine_type),
                json.dumps(restaurant.vibes), restaurant.location.get('lat'),
                restaurant.location.get('lng'), restaurant.location.get('address'),
                restaurant.location.get('city'), restaurant.location.get('state'),
                restaurant.neighborhood, restaurant.google_place_id,
                restaurant.user_rating, restaurant.google_rating, restaurant.price_level,
                json.dumps(restaurant.features), restaurant.reviews_summary,
                json.dumps(restaurant.menu_items), restaurant.revisit_preference,
                restaurant.notes, restaurant.is_wishlist, restaurant.last_updated, 'csv_import'
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
            last_updated=datetime.fromisoformat(row[19]) if row[19] else datetime.now(),
            is_wishlist=bool(row[21]) if len(row) > 21 else False
        )
    
    def save_recommendation_session(self, session: RecommendationSession):
        """Save recommendation session to database"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO recommendation_sessions
                (session_id, user_id, location_data, shown_restaurant_ids, liked_restaurant_ids,
                 disliked_restaurant_ids, session_preferences, filters, created_at, last_activity)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                session.session_id, session.user_id, json.dumps(session.location),
                json.dumps(session.shown_restaurant_ids), json.dumps(session.liked_restaurant_ids),
                json.dumps(session.disliked_restaurant_ids), json.dumps(session.session_preferences),
                json.dumps(session.filters), session.created_at.isoformat(), 
                session.last_activity.isoformat()
            ))
            conn.commit()
    
    def get_recommendation_session(self, session_id: str) -> Optional[RecommendationSession]:
        """Get recommendation session from database"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM recommendation_sessions WHERE session_id = ?', (session_id,))
            row = cursor.fetchone()
            if row:
                return RecommendationSession(
                    session_id=row[0],
                    user_id=row[1],
                    location=json.loads(row[2]) if row[2] else {},
                    shown_restaurant_ids=json.loads(row[3]) if row[3] else [],
                    liked_restaurant_ids=json.loads(row[4]) if row[4] else [],
                    disliked_restaurant_ids=json.loads(row[5]) if row[5] else [],
                    session_preferences=json.loads(row[6]) if row[6] else {},
                    filters=json.loads(row[7]) if row[7] else {},
                    created_at=datetime.fromisoformat(row[8]),
                    last_activity=datetime.fromisoformat(row[9])
                )
        return None
    
    def save_session_feedback(self, session_id: str, restaurant_id: str, 
                            feedback_type: str, feedback_details: str = None):
        """Save session feedback to database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO session_feedback
                (session_id, restaurant_id, feedback_type, feedback_details, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (session_id, restaurant_id, feedback_type, feedback_details, datetime.now().isoformat()))
            conn.commit()
    
    def get_user_sessions(self, user_id: str, limit: int = 10) -> List[RecommendationSession]:
        """Get recent recommendation sessions for a user"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM recommendation_sessions 
                WHERE user_id = ? 
                ORDER BY last_activity DESC 
                LIMIT ?
            ''', (user_id, limit))
            
            sessions = []
            for row in cursor.fetchall():
                sessions.append(RecommendationSession(
                    session_id=row[0],
                    user_id=row[1],
                    location=json.loads(row[2]) if row[2] else {},
                    shown_restaurant_ids=json.loads(row[3]) if row[3] else [],
                    liked_restaurant_ids=json.loads(row[4]) if row[4] else [],
                    disliked_restaurant_ids=json.loads(row[5]) if row[5] else [],
                    session_preferences=json.loads(row[6]) if row[6] else {},
                    filters=json.loads(row[7]) if row[7] else {},
                    created_at=datetime.fromisoformat(row[8]),
                    last_activity=datetime.fromisoformat(row[9])
                ))
            
            return sessions