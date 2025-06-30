"""
preference_analyzer.py
User preference analysis and learning from historical data
"""

import numpy as np
import logging
from typing import Dict, List, Any
from collections import defaultdict, Counter
from models import Restaurant, UserProfile
from database import DatabaseManager

logger = logging.getLogger(__name__)

class PreferenceAnalyzer:
    """Analyzes user preferences from historical data"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def analyze_user_preferences(self, user_id: str) -> UserProfile:
        """Analyze user preferences from restaurant history"""
        restaurants = self.db_manager.get_all_restaurants()
        rated_restaurants = [r for r in restaurants if r.user_rating is not None]
        
        profile = UserProfile(user_id=user_id)
        
        if not rated_restaurants:
            logger.info(f"No rated restaurants found for user {user_id}")
            return profile
        
        logger.info(f"Analyzing preferences for {len(rated_restaurants)} rated restaurants")
        
        # Analyze cuisine preferences
        profile.cuisine_preferences = self._analyze_cuisine_preferences(rated_restaurants)
        
        # Analyze price preferences
        profile.price_preferences = self._analyze_price_preferences(rated_restaurants)
        
        # Analyze vibe preferences
        profile.vibe_preferences = self._analyze_vibe_preferences(rated_restaurants)
        
        # Extract favorite dishes
        profile.favorite_dishes = self._extract_favorite_dishes(rated_restaurants)
        
        # Calculate rating patterns
        profile.rating_patterns = self._calculate_rating_patterns(rated_restaurants)
        
        # Analyze location patterns
        profile.location_history = self._analyze_location_patterns(rated_restaurants)
        
        return profile
    
    def _analyze_cuisine_preferences(self, restaurants: List[Restaurant]) -> Dict[str, float]:
        """Analyze cuisine type preferences"""
        cuisine_ratings = defaultdict(list)
        
        for restaurant in restaurants:
            for cuisine in restaurant.cuisine_type:
                cuisine_ratings[cuisine].append(restaurant.user_rating)
        
        preferences = {}
        overall_avg = np.mean([r.user_rating for r in restaurants])
        
        for cuisine, ratings in cuisine_ratings.items():
            avg_rating = np.mean(ratings)
            count = len(ratings)
            
            # Calculate preference score with confidence weighting
            # More data points = more confident in the preference
            confidence_weight = min(count / 5.0, 1.0)  # Max confidence at 5+ ratings
            preference_score = ((avg_rating - overall_avg) / 2.0) * confidence_weight
            
            preferences[cuisine] = round(preference_score, 3)
        
        return preferences
    
    def _analyze_price_preferences(self, restaurants: List[Restaurant]) -> Dict[int, float]:
        """Analyze price level preferences"""
        price_ratings = defaultdict(list)
        
        for restaurant in restaurants:
            if restaurant.price_level:
                price_ratings[restaurant.price_level].append(restaurant.user_rating)
        
        preferences = {}
        overall_avg = np.mean([r.user_rating for r in restaurants])
        
        for price_level, ratings in price_ratings.items():
            avg_rating = np.mean(ratings)
            count = len(ratings)
            
            # Weight by confidence
            confidence_weight = min(count / 3.0, 1.0)  # Max confidence at 3+ ratings
            preference_score = ((avg_rating - overall_avg) / 2.0) * confidence_weight
            
            preferences[price_level] = round(preference_score, 3)
        
        return preferences
    
    def _analyze_vibe_preferences(self, restaurants: List[Restaurant]) -> Dict[str, float]:
        """Analyze vibe/atmosphere preferences"""
        vibe_ratings = defaultdict(list)
        
        for restaurant in restaurants:
            for vibe in restaurant.vibes:
                vibe_ratings[vibe].append(restaurant.user_rating)
        
        preferences = {}
        overall_avg = np.mean([r.user_rating for r in restaurants])
        
        for vibe, ratings in vibe_ratings.items():
            avg_rating = np.mean(ratings)
            count = len(ratings)
            
            # Weight by confidence
            confidence_weight = min(count / 3.0, 1.0)
            preference_score = ((avg_rating - overall_avg) / 2.0) * confidence_weight
            
            preferences[vibe] = round(preference_score, 3)
        
        return preferences
    
    def _extract_favorite_dishes(self, restaurants: List[Restaurant]) -> List[str]:
        """Extract favorite dishes from highly rated restaurants"""
        favorite_dishes = []
        
        # Only consider restaurants rated 4+ stars
        high_rated_restaurants = [r for r in restaurants if r.user_rating >= 4.0]
        
        for restaurant in high_rated_restaurants:
            favorite_dishes.extend(restaurant.menu_items)
        
        # Count frequency and return most common dishes
        dish_counts = Counter(favorite_dishes)
        
        # Return dishes mentioned more than once, sorted by frequency
        return [dish for dish, count in dish_counts.most_common() if count > 1]
    
    def _calculate_rating_patterns(self, restaurants: List[Restaurant]) -> Dict[str, Any]:
        """Calculate user's rating patterns and tendencies"""
        ratings = [r.user_rating for r in restaurants]
        
        patterns = {
            'average_rating': round(np.mean(ratings), 2),
            'rating_std': round(np.std(ratings), 2),
            'total_restaurants': len(restaurants),
            'rating_distribution': dict(Counter([int(r) for r in ratings])),
            'high_rated_count': len([r for r in ratings if r >= 4.0]),
            'low_rated_count': len([r for r in ratings if r <= 2.0]),
            'rating_range': round(max(ratings) - min(ratings), 1)
        }
        
        # Analyze rating tendency
        if patterns['average_rating'] >= 4.0:
            patterns['rating_tendency'] = 'generous'
        elif patterns['average_rating'] <= 2.5:
            patterns['rating_tendency'] = 'critical'
        else:
            patterns['rating_tendency'] = 'balanced'
        
        # Analyze rating consistency
        if patterns['rating_std'] <= 0.5:
            patterns['rating_consistency'] = 'very_consistent'
        elif patterns['rating_std'] <= 1.0:
            patterns['rating_consistency'] = 'consistent'
        else:
            patterns['rating_consistency'] = 'variable'
        
        return patterns
    
    def _analyze_location_patterns(self, restaurants: List[Restaurant]) -> List[Dict]:
        """Analyze dining location patterns"""
        city_data = defaultdict(lambda: {'count': 0, 'ratings': [], 'cuisines': []})
        
        for restaurant in restaurants:
            city = restaurant.location.get('city', 'Unknown')
            city_data[city]['count'] += 1
            city_data[city]['ratings'].append(restaurant.user_rating)
            city_data[city]['cuisines'].extend(restaurant.cuisine_type)
        
        location_history = []
        for city, data in city_data.items():
            if data['count'] > 0:  # Only include cities with restaurants
                location_history.append({
                    'city': city,
                    'visit_count': data['count'],
                    'average_rating': round(np.mean(data['ratings']), 2),
                    'top_cuisines': [cuisine for cuisine, _ in 
                                   Counter(data['cuisines']).most_common(3)]
                })
        
        # Sort by visit count
        return sorted(location_history, key=lambda x: x['visit_count'], reverse=True)
    
    def update_preferences_with_new_rating(self, user_id: str, restaurant: Restaurant, rating: float):
        """Update user preferences when a new rating is added"""
        # Get current profile
        profile = self.db_manager.get_user_profile(user_id)
        if not profile:
            profile = self.analyze_user_preferences(user_id)
        
        # Update the restaurant's rating
        restaurant.user_rating = rating
        self.db_manager.save_restaurant(restaurant)
        
        # Recalculate preferences
        updated_profile = self.analyze_user_preferences(user_id)
        self.db_manager.save_user_profile(updated_profile)
        
        logger.info(f"Updated preferences for user {user_id} with new rating for {restaurant.name}")
        
        return updated_profile
    
    def get_preference_insights(self, user_id: str) -> Dict[str, Any]:
        """Get human-readable insights about user preferences"""
        profile = self.db_manager.get_user_profile(user_id)
        if not profile:
            return {"error": "No profile found for user"}
        
        insights = {
            "personality": self._determine_dining_personality(profile),
            "top_cuisines": self._get_top_preferences(profile.cuisine_preferences, "cuisines"),
            "preferred_vibes": self._get_top_preferences(profile.vibe_preferences, "vibes"),
            "price_comfort_zone": self._analyze_price_comfort_zone(profile.price_preferences),
            "adventurousness": self._assess_adventurousness(profile),
            "consistency": profile.rating_patterns.get('rating_consistency', 'unknown'),
            "favorite_cities": [loc['city'] for loc in profile.location_history[:5]]
        }
        
        return insights
    
    def _determine_dining_personality(self, profile: UserProfile) -> str:
        """Determine user's dining personality type"""
        patterns = profile.rating_patterns
        avg_rating = patterns.get('average_rating', 3.0)
        consistency = patterns.get('rating_consistency', 'balanced')
        
        if avg_rating >= 4.0 and consistency == 'very_consistent':
            return "The Optimist - Consistently finds the good in every meal"
        elif avg_rating <= 2.5 and consistency == 'very_consistent':
            return "The Critic - Has high standards and isn't easily impressed"
        elif consistency == 'variable':
            return "The Explorer - Experiences vary widely, always trying new things"
        elif 3.0 <= avg_rating <= 3.8:
            return "The Realist - Balanced perspective with honest assessments"
        else:
            return "The Enthusiast - Generally positive about dining experiences"
    
    def _get_top_preferences(self, preferences: Dict[str, float], category: str) -> List[Dict]:
        """Get top preferences with scores"""
        if not preferences:
            return []
        
        sorted_prefs = sorted(preferences.items(), key=lambda x: x[1], reverse=True)
        return [
            {"name": name, "preference_score": score}
            for name, score in sorted_prefs[:5] if score > 0.1
        ]
    
    def _analyze_price_comfort_zone(self, price_preferences: Dict[int, float]) -> str:
        """Analyze user's price comfort zone"""
        if not price_preferences:
            return "Unknown"
        
        # Find the price level with highest positive preference
        best_price = max(price_preferences.items(), key=lambda x: x[1])
        
        price_descriptions = {
            1: "Budget-friendly ($)",
            2: "Moderate ($$)",
            3: "Upscale ($$$)",
            4: "Fine dining ($$$$)"
        }
        
        return price_descriptions.get(best_price[0], "Unknown")
    
    def _assess_adventurousness(self, profile: UserProfile) -> str:
        """Assess how adventurous the user is with food"""
        num_cuisines = len(profile.cuisine_preferences)
        num_cities = len(profile.location_history)
        total_restaurants = profile.rating_patterns.get('total_restaurants', 0)
        
        if num_cuisines >= 10 and num_cities >= 5:
            return "Highly adventurous - Seeks diverse cuisines and travels widely for food"
        elif num_cuisines >= 6 and num_cities >= 3:
            return "Moderately adventurous - Enjoys variety in food and locations"
        elif num_cuisines >= 3:
            return "Somewhat adventurous - Sticks to preferred cuisines but tries new places"
        else:
            return "Creature of habit - Prefers familiar foods and places"