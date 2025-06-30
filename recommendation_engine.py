"""
recommendation_engine.py
Core recommendation engine for personalized restaurant suggestions
"""

import numpy as np
import logging
from typing import List, Tuple, Optional, Dict, Any
from geopy.distance import geodesic
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from models import Restaurant, UserProfile, Recommendation
from database import DatabaseManager
from preference_analyzer import PreferenceAnalyzer

logger = logging.getLogger(__name__)

class RecommendationEngine:
    """Core recommendation engine"""
    
    def __init__(self, db_manager: DatabaseManager, google_service=None):
        self.db_manager = db_manager
        self.preference_analyzer = PreferenceAnalyzer(db_manager)
        self.google_service = google_service
    
    def get_recommendations(self, user_id: str, lat: float, lng: float, 
                          radius_km: float = 25, limit: int = 10,
                          exclude_visited: bool = True, include_live_search: bool = False) -> List[Recommendation]:
        """Get personalized restaurant recommendations for a location"""
        
        # Get user profile
        user_profile = self.db_manager.get_user_profile(user_id)
        if not user_profile:
            # Generate profile from historical data
            user_profile = self.preference_analyzer.analyze_user_preferences(user_id)
            self.db_manager.save_user_profile(user_profile)
        
        # Get nearby restaurants from database
        nearby_restaurants = self.db_manager.get_restaurants_by_location(lat, lng, radius_km)
        
        # Add live search results if requested
        if include_live_search and self.google_service:
            live_restaurants = self._get_live_restaurant_recommendations(lat, lng, radius_km, user_profile)
            nearby_restaurants.extend(live_restaurants)
            logger.info(f"Added {len(live_restaurants)} live restaurants from Google Places")
        
        # Filter out already visited restaurants if requested
        if exclude_visited:
            visited_restaurants = {r.id for r in self.db_manager.get_all_restaurants() 
                                 if r.user_rating is not None}
            nearby_restaurants = [r for r in nearby_restaurants if r.id not in visited_restaurants]
        
        if not nearby_restaurants:
            if include_live_search and not self.google_service:
                logger.warning("Live search requested but Google service not available")
            logger.warning(f"No restaurants found within {radius_km}km of location")
            return []
        
        # Score restaurants
        recommendations = []
        for restaurant in nearby_restaurants:
            score = self._calculate_recommendation_score(restaurant, user_profile)
            reasoning = self._generate_recommendation_reasoning(restaurant, user_profile, score)
            
            # Calculate distance
            if restaurant.location.get('lat') and restaurant.location.get('lng'):
                distance = geodesic(
                    (lat, lng), 
                    (restaurant.location['lat'], restaurant.location['lng'])
                ).kilometers
            else:
                distance = None
            
            recommendation = Recommendation(
                restaurant=restaurant,
                score=score,
                reasoning=reasoning,
                distance_km=distance
            )
            recommendations.append(recommendation)
        
        # Sort by score and return top recommendations
        recommendations.sort(key=lambda x: x.score, reverse=True)
        
        logger.info(f"Generated {len(recommendations)} recommendations for user {user_id}")
        return recommendations[:limit]
    
    def _calculate_recommendation_score(self, restaurant: Restaurant, profile: UserProfile) -> float:
        """Calculate recommendation score for a restaurant"""
        score = 0.0
        
        # Cuisine preference score (40% weight)
        cuisine_score = self._calculate_cuisine_score(restaurant, profile)
        score += cuisine_score * 0.4
        
        # Price preference score (20% weight)
        price_score = self._calculate_price_score(restaurant, profile)
        score += price_score * 0.2
        
        # Vibe preference score (20% weight)
        vibe_score = self._calculate_vibe_score(restaurant, profile)
        score += vibe_score * 0.2
        
        # Quality indicators (15% weight)
        quality_score = self._calculate_quality_score(restaurant)
        score += quality_score * 0.15
        
        # Special preferences (5% weight)
        special_score = self._calculate_special_score(restaurant, profile)
        score += special_score * 0.05
        
        return round(score, 3)
    
    def _calculate_cuisine_score(self, restaurant: Restaurant, profile: UserProfile) -> float:
        """Calculate cuisine preference score"""
        if not restaurant.cuisine_type:
            return 0.0
        
        cuisine_scores = []
        for cuisine in restaurant.cuisine_type:
            if cuisine in profile.cuisine_preferences:
                cuisine_scores.append(profile.cuisine_preferences[cuisine])
            else:
                # Unknown cuisine gets neutral score
                cuisine_scores.append(0.0)
        
        # Return the best cuisine match
        return max(cuisine_scores) if cuisine_scores else 0.0
    
    def _calculate_price_score(self, restaurant: Restaurant, profile: UserProfile) -> float:
        """Calculate price preference score"""
        if not restaurant.price_level or not profile.price_preferences:
            return 0.0
        
        return profile.price_preferences.get(restaurant.price_level, 0.0)
    
    def _calculate_vibe_score(self, restaurant: Restaurant, profile: UserProfile) -> float:
        """Calculate vibe preference score"""
        if not restaurant.vibes:
            return 0.0
        
        vibe_scores = []
        for vibe in restaurant.vibes:
            if vibe in profile.vibe_preferences:
                vibe_scores.append(profile.vibe_preferences[vibe])
            else:
                vibe_scores.append(0.0)
        
        # Return the best vibe match
        return max(vibe_scores) if vibe_scores else 0.0
    
    def _calculate_quality_score(self, restaurant: Restaurant) -> float:
        """Calculate quality score based on ratings and features"""
        score = 0.0
        
        # Google rating component
        if restaurant.google_rating:
            # Normalize Google rating (1-5) to (-1, 1)
            normalized_rating = (restaurant.google_rating - 3) / 2
            score += normalized_rating * 0.8
        
        # Features that indicate quality
        if restaurant.features:
            if restaurant.features.get('website'):
                score += 0.1
            if restaurant.features.get('phone'):
                score += 0.1
        
        return min(score, 1.0)  # Cap at 1.0
    
    def _calculate_special_score(self, restaurant: Restaurant, profile: UserProfile) -> float:
        """Calculate special preference bonuses"""
        score = 0.0
        
        # Revisit preference bonus
        if restaurant.revisit_preference in ['Y', 'Yes', 'yes']:
            score += 1.0
        
        # Favorite dishes bonus
        if profile.favorite_dishes and restaurant.menu_items:
            for dish in profile.favorite_dishes:
                for menu_item in restaurant.menu_items:
                    if dish.lower() in menu_item.lower():
                        score += 0.3
                        break
        
        return min(score, 1.0)  # Cap at 1.0
    
    def _generate_recommendation_reasoning(self, restaurant: Restaurant, 
                                         profile: UserProfile, score: float) -> str:
        """Generate human-readable reasoning for recommendation"""
        reasons = []
        
        # Cuisine reasoning
        if restaurant.cuisine_type:
            cuisine_scores = {cuisine: profile.cuisine_preferences.get(cuisine, 0) 
                            for cuisine in restaurant.cuisine_type}
            best_cuisine = max(cuisine_scores.items(), key=lambda x: x[1])
            
            if best_cuisine[1] > 0.2:
                reasons.append(f"You love {best_cuisine[0]} cuisine")
            elif best_cuisine[1] > -0.2:
                reasons.append(f"Serves {', '.join(restaurant.cuisine_type)} cuisine")
        
        # Rating reasoning
        if restaurant.google_rating and restaurant.google_rating >= 4.0:
            reasons.append(f"Highly rated ({restaurant.google_rating}/5.0)")
        
        # Price reasoning
        if restaurant.price_level and restaurant.price_level in profile.price_preferences:
            price_pref = profile.price_preferences[restaurant.price_level]
            if price_pref > 0.2:
                price_desc = {1: "budget-friendly", 2: "moderately priced", 
                            3: "upscale", 4: "fine dining"}
                reasons.append(f"Matches your {price_desc.get(restaurant.price_level, '')} preference")
        
        # Vibe reasoning
        if restaurant.vibes:
            vibe_scores = {vibe: profile.vibe_preferences.get(vibe, 0) for vibe in restaurant.vibes}
            best_vibe = max(vibe_scores.items(), key=lambda x: x[1])
            
            if best_vibe[1] > 0.2:
                reasons.append(f"Perfect {best_vibe[0].lower()} atmosphere for you")
        
        # Special reasons
        if restaurant.revisit_preference in ['Y', 'Yes', 'yes']:
            reasons.append("Previously marked as 'would revisit'")
        
        # Fallback reasoning
        if not reasons:
            if score > 0.5:
                reasons.append("Strongly matches your preferences")
            elif score > 0:
                reasons.append("Good match for your tastes")
            else:
                reasons.append("Worth trying something new")
        
        return "; ".join(reasons)
    
    def find_similar_restaurants(self, restaurant_id: str, limit: int = 5, 
                               user_id: Optional[str] = None) -> List[Restaurant]:
        """Find restaurants similar to a given restaurant"""
        target_restaurant = self.db_manager.get_restaurant_by_id(restaurant_id)
        if not target_restaurant:
            logger.warning(f"Restaurant with ID {restaurant_id} not found")
            return []
        
        all_restaurants = self.db_manager.get_all_restaurants()
        similar_restaurants = []
        
        for restaurant in all_restaurants:
            if restaurant.id == restaurant_id:
                continue
            
            similarity = self._calculate_similarity(target_restaurant, restaurant)
            if similarity > 0.3:  # Minimum similarity threshold
                similar_restaurants.append((restaurant, similarity))
        
        # Sort by similarity and return top results
        similar_restaurants.sort(key=lambda x: x[1], reverse=True)
        
        # If user_id provided, also consider user preferences
        if user_id:
            user_profile = self.db_manager.get_user_profile(user_id)
            if user_profile:
                # Re-score with user preferences
                final_recommendations = []
                for restaurant, similarity in similar_restaurants:
                    user_score = self._calculate_recommendation_score(restaurant, user_profile)
                    combined_score = (similarity * 0.7) + (user_score * 0.3)
                    final_recommendations.append((restaurant, combined_score))
                
                final_recommendations.sort(key=lambda x: x[1], reverse=True)
                return [r[0] for r in final_recommendations[:limit]]
        
        return [r[0] for r in similar_restaurants[:limit]]
    
    def _calculate_similarity(self, restaurant1: Restaurant, restaurant2: Restaurant) -> float:
        """Calculate similarity between two restaurants"""
        similarity = 0.0
        
        # Cuisine similarity (40% weight)
        cuisine_sim = self._calculate_set_similarity(
            set(restaurant1.cuisine_type), set(restaurant2.cuisine_type)
        )
        similarity += cuisine_sim * 0.4
        
        # Vibe similarity (30% weight)
        vibe_sim = self._calculate_set_similarity(
            set(restaurant1.vibes), set(restaurant2.vibes)
        )
        similarity += vibe_sim * 0.3
        
        # Price similarity (20% weight)
        if restaurant1.price_level and restaurant2.price_level:
            price_diff = abs(restaurant1.price_level - restaurant2.price_level)
            price_similarity = max(0, 1 - price_diff / 3)  # Max diff is 3
            similarity += price_similarity * 0.2
        
        # Location similarity (10% weight)
        if (restaurant1.location.get('city') and restaurant2.location.get('city')):
            if restaurant1.location['city'] == restaurant2.location['city']:
                similarity += 0.1
        
        return similarity
    
    def _calculate_set_similarity(self, set1: set, set2: set) -> float:
        """Calculate Jaccard similarity between two sets"""
        if not set1 and not set2:
            return 1.0
        if not set1 or not set2:
            return 0.0
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0
    
    def get_recommendations_by_city(self, user_id: str, city: str, state: str = None,
                                  limit: int = 10, include_live_search: bool = False) -> List[Recommendation]:
        """Get recommendations for a specific city"""
        all_restaurants = self.db_manager.get_all_restaurants()
        
        # Filter by city (and state if provided)
        city_restaurants = []
        for restaurant in all_restaurants:
            restaurant_city = restaurant.location.get('city', '').lower()
            restaurant_state = restaurant.location.get('state', '').lower()
            
            city_match = restaurant_city == city.lower()
            state_match = not state or restaurant_state == state.lower()
            
            if city_match and state_match and restaurant.user_rating is None:
                city_restaurants.append(restaurant)
        
        # Add live search results if requested
        if include_live_search and self.google_service:
            live_restaurants = self._get_live_city_restaurants(city, state)
            city_restaurants.extend(live_restaurants)
            logger.info(f"Added {len(live_restaurants)} live restaurants from Google Places for {city}")
        
        if not city_restaurants:
            if include_live_search and not self.google_service:
                logger.warning("Live search requested but Google service not available")
            logger.warning(f"No unvisited restaurants found in {city}")
            return []
        
        # Get user profile
        user_profile = self.db_manager.get_user_profile(user_id)
        if not user_profile:
            user_profile = self.preference_analyzer.analyze_user_preferences(user_id)
        
        # Score restaurants
        recommendations = []
        for restaurant in city_restaurants:
            score = self._calculate_recommendation_score(restaurant, user_profile)
            reasoning = self._generate_recommendation_reasoning(restaurant, user_profile, score)
            
            recommendation = Recommendation(
                restaurant=restaurant,
                score=score,
                reasoning=reasoning
            )
            recommendations.append(recommendation)
        
        # Sort and return
        recommendations.sort(key=lambda x: x.score, reverse=True)
        return recommendations[:limit]
    
    def get_wishlist_recommendations(self, user_id: str, lat: float = None, lng: float = None,
                                   radius_km: float = 50) -> List[Recommendation]:
        """Get recommendations from restaurants marked for revisit"""
        all_restaurants = self.db_manager.get_all_restaurants()
        
        # Filter restaurants marked for revisit
        wishlist_restaurants = [
            r for r in all_restaurants 
            if r.revisit_preference in ['Y', 'Yes', 'yes'] and r.user_rating is None
        ]
        
        # If location provided, filter by proximity
        if lat is not None and lng is not None:
            nearby_wishlist = []
            for restaurant in wishlist_restaurants:
                if restaurant.location.get('lat') and restaurant.location.get('lng'):
                    distance = geodesic(
                        (lat, lng),
                        (restaurant.location['lat'], restaurant.location['lng'])
                    ).kilometers
                    if distance <= radius_km:
                        nearby_wishlist.append(restaurant)
            wishlist_restaurants = nearby_wishlist
        
        if not wishlist_restaurants:
            return []
        
        # Get user profile
        user_profile = self.db_manager.get_user_profile(user_id)
        if not user_profile:
            user_profile = self.preference_analyzer.analyze_user_preferences(user_id)
        
        # Create recommendations
        recommendations = []
        for restaurant in wishlist_restaurants:
            # Wishlist items get a base score boost
            base_score = self._calculate_recommendation_score(restaurant, user_profile)
            wishlist_score = min(base_score + 0.3, 1.0)  # Boost score but cap at 1.0
            
            reasoning = "From your wishlist; " + self._generate_recommendation_reasoning(
                restaurant, user_profile, base_score
            )
            
            # Calculate distance if location provided
            distance = None
            if lat is not None and lng is not None:
                if restaurant.location.get('lat') and restaurant.location.get('lng'):
                    distance = geodesic(
                        (lat, lng),
                        (restaurant.location['lat'], restaurant.location['lng'])
                    ).kilometers
            
            recommendation = Recommendation(
                restaurant=restaurant,
                score=wishlist_score,
                reasoning=reasoning,
                distance_km=distance
            )
            recommendations.append(recommendation)
        
        # Sort by score (and distance if available)
        if lat is not None and lng is not None:
            recommendations.sort(key=lambda x: (-x.score, x.distance_km or float('inf')))
        else:
            recommendations.sort(key=lambda x: x.score, reverse=True)
        
        return recommendations
    
    def _get_live_restaurant_recommendations(self, lat: float, lng: float, 
                                           radius_km: float, user_profile) -> List:
        """Get live restaurant recommendations from Google Places"""
        try:
            # Convert km to meters for Google Places API
            radius_meters = int(radius_km * 1000)
            
            # Search for nearby restaurants
            places_data = self.google_service.search_nearby_restaurants(
                lat=lat, 
                lng=lng, 
                radius_meters=radius_meters,
                limit=20  # Get more results to filter and rank
            )
            
            if not places_data:
                logger.info("No live restaurants found from Google Places")
                return []
            
            # Convert Google Places results to Restaurant objects
            live_restaurants = self.google_service.convert_places_to_restaurants(places_data)
            
            # Filter out restaurants that already exist in our database
            existing_place_ids = set()
            existing_restaurants = self.db_manager.get_all_restaurants()
            for restaurant in existing_restaurants:
                if restaurant.google_place_id:
                    existing_place_ids.add(restaurant.google_place_id)
            
            # Only return new restaurants not in our database
            new_restaurants = [r for r in live_restaurants 
                             if r.google_place_id not in existing_place_ids]
            
            logger.info(f"Found {len(new_restaurants)} new restaurants from Google Places (filtered from {len(live_restaurants)} total)")
            return new_restaurants
            
        except Exception as e:
            logger.error(f"Error getting live restaurant recommendations: {e}")
            return []
    
    def _get_live_city_restaurants(self, city: str, state: str = None) -> List:
        """Get live restaurant recommendations for a city using Google Places"""
        try:
            # Build search query for the city
            location_query = city
            if state:
                location_query += f", {state}"
            
            # Search for restaurants in the city using text search
            places_data = self.google_service.search_restaurants_by_text(
                query="restaurants",  # Search for restaurants
                location=location_query,
                limit=20
            )
            
            if not places_data:
                logger.info(f"No live restaurants found for {location_query}")
                return []
            
            # Convert Google Places results to Restaurant objects
            live_restaurants = self.google_service.convert_places_to_restaurants(places_data)
            
            # Filter out restaurants that already exist in our database
            existing_place_ids = set()
            existing_restaurants = self.db_manager.get_all_restaurants()
            for restaurant in existing_restaurants:
                if restaurant.google_place_id:
                    existing_place_ids.add(restaurant.google_place_id)
            
            # Only return new restaurants not in our database
            new_restaurants = [r for r in live_restaurants 
                             if r.google_place_id not in existing_place_ids]
            
            logger.info(f"Found {len(new_restaurants)} new restaurants for {location_query} (filtered from {len(live_restaurants)} total)")
            return new_restaurants
            
        except Exception as e:
            logger.error(f"Error getting live city restaurants: {e}")
            return []
        