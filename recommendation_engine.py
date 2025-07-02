"""
recommendation_engine.py
Core recommendation engine for personalized restaurant suggestions
"""

import numpy as np
import logging
import time
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime
from geopy.distance import geodesic
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from models import Restaurant, UserProfile, Recommendation, RecommendationSession
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
                                  limit: int = 10, include_live_search: bool = False, 
                                  session_preferences: Dict = None) -> List[Recommendation]:
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
            live_restaurants = self._get_live_city_restaurants(city, state, session_preferences)
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
        """Get recommendations from restaurants marked as wishlist items"""
        all_restaurants = self.db_manager.get_all_restaurants()
        
        # Filter restaurants marked as wishlist items (haven't been visited yet)
        wishlist_restaurants = [
            r for r in all_restaurants 
            if r.is_wishlist and r.user_rating is None
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
                limit=60  # Get more results to filter and rank (uses pagination)
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
    
    def _get_live_city_restaurants(self, city: str, state: str = None, session_preferences: Dict = None) -> List:
        """Get live restaurant recommendations for a city using Google Places with diverse search strategies"""
        try:
            # Build search query for the city
            location_query = city
            if state:
                location_query += f", {state}"
            
            all_places_data = []
            seen_place_ids = set()
            
            # Build preference-aware search queries
            search_queries = ["restaurants"]  # Always include generic search
            
            # Add cuisine-specific searches if preferences specified
            if session_preferences and 'preferred_cuisines' in session_preferences:
                for cuisine in session_preferences['preferred_cuisines']:
                    search_queries.extend([
                        f"{cuisine} restaurants",
                        f"{cuisine} food",
                        f"best {cuisine} restaurants"
                    ])
            
            # Add vibe-specific searches if preferences specified  
            if session_preferences and 'preferred_vibes' in session_preferences:
                for vibe in session_preferences['preferred_vibes']:
                    if vibe.lower() == 'casual':
                        search_queries.extend([
                            "casual dining",
                            "casual restaurants",
                            "family restaurants"
                        ])
                    elif vibe.lower() == 'upscale':
                        search_queries.extend([
                            "fine dining",
                            "upscale restaurants",
                            "elegant restaurants"
                        ])
            
            # If no preferences, use diverse generic queries
            if not session_preferences or (not session_preferences.get('preferred_cuisines') and not session_preferences.get('preferred_vibes')):
                search_queries.extend([
                    "dining",
                    "food", 
                    "best restaurants",
                    "popular restaurants"
                ])
            
            logger.info(f"Using search queries: {search_queries}")
            
            # Search with different queries to get variety
            for query in search_queries:
                if len(all_places_data) >= 100:  # Cap total results to avoid excessive API calls
                    break
                    
                places_data = self.google_service.search_restaurants_by_text(
                    query=query,
                    location=location_query,
                    limit=30  # Smaller limit per query for variety
                )
                
                # Deduplicate by place_id
                for place in places_data:
                    place_id = place.get('place_id')
                    if place_id and place_id not in seen_place_ids:
                        all_places_data.append(place)
                        seen_place_ids.add(place_id)
                
                logger.info(f"Query '{query}': Found {len(places_data)} places (unique total: {len(all_places_data)})")
                
                # Small delay between different query types
                time.sleep(0.5)
            
            if not all_places_data:
                logger.info(f"No live restaurants found for {location_query}")
                return []
            
            # Convert Google Places results to Restaurant objects
            live_restaurants = self.google_service.convert_places_to_restaurants(all_places_data)
            
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
    
    def start_recommendation_session(self, user_id: str, location: Dict) -> str:
        """Start a new interactive recommendation session"""
        import uuid
        
        session_id = str(uuid.uuid4())
        session = RecommendationSession(
            session_id=session_id,
            user_id=user_id,
            location=location
        )
        
        self.db_manager.save_recommendation_session(session)
        logger.info(f"Started recommendation session {session_id} for user {user_id}")
        return session_id
    
    def collect_session_feedback(self, session_id: str, 
                               liked_restaurant_ids: List[str],
                               disliked_restaurant_ids: List[str],
                               cuisine_preferences: List[str] = None,
                               vibe_preferences: List[str] = None) -> bool:
        """Collect user feedback for a recommendation session"""
        try:
            session = self.db_manager.get_recommendation_session(session_id)
            if not session:
                logger.error(f"Session {session_id} not found")
                return False
            
            # Update session with feedback
            session.liked_restaurant_ids.extend(liked_restaurant_ids)
            session.disliked_restaurant_ids.extend(disliked_restaurant_ids)
            session.last_activity = datetime.now()
            
            # Update session preferences
            if cuisine_preferences:
                session.session_preferences['preferred_cuisines'] = cuisine_preferences
            if vibe_preferences:
                session.session_preferences['preferred_vibes'] = vibe_preferences
            
            # Save updated session
            self.db_manager.save_recommendation_session(session)
            
            # Save detailed feedback
            for restaurant_id in liked_restaurant_ids:
                self.db_manager.save_session_feedback(session_id, restaurant_id, 'liked')
            
            for restaurant_id in disliked_restaurant_ids:
                self.db_manager.save_session_feedback(session_id, restaurant_id, 'disliked')
            
            logger.info(f"Collected feedback for session {session_id}: "
                       f"{len(liked_restaurant_ids)} liked, {len(disliked_restaurant_ids)} disliked")
            return True
            
        except Exception as e:
            logger.error(f"Error collecting session feedback: {e}")
            return False
    
    def get_session_recommendations(self, session_id: str, limit: int = 10,
                                  include_live_search: bool = True) -> List[Recommendation]:
        """Get recommendations for a session with learned preferences"""
        try:
            session = self.db_manager.get_recommendation_session(session_id)
            if not session:
                logger.error(f"Session {session_id} not found")
                return []
            
            # Get base recommendations based on session location
            location = session.location
            if 'lat' in location and 'lng' in location:
                # Location-based recommendations
                # Use cached live restaurants if available to avoid redundant API calls
                use_live_search = include_live_search and not session.cached_live_restaurants
                recommendations = self.get_recommendations(
                    user_id=session.user_id,
                    lat=location['lat'],
                    lng=location['lng'],
                    radius_km=location.get('radius_km', 25),
                    limit=200,  # Get large pool for multiple rounds
                    include_live_search=use_live_search
                )
                
                # If we just fetched live restaurants, cache them in the session
                if use_live_search and recommendations:
                    live_restaurant_ids = [rec.restaurant.id for rec in recommendations 
                                         if rec.restaurant.id.startswith('gp_')]
                    session.cached_live_restaurants.extend(live_restaurant_ids)
                    logger.info(f"Cached {len(live_restaurant_ids)} live restaurants for session {session_id}")
            elif 'city' in location:
                # City-based recommendations - get much larger pool for session cycling
                # Use cached live restaurants if available to avoid redundant API calls
                use_live_search = include_live_search and not session.cached_live_restaurants
                if session.cached_live_restaurants:
                    logger.info(f"Using cached live restaurants from session (avoiding API calls)")
                recommendations = self.get_recommendations_by_city(
                    user_id=session.user_id,
                    city=location['city'],
                    state=location.get('state'),
                    limit=200,  # Get large pool of recommendations for multiple rounds
                    include_live_search=use_live_search,
                    session_preferences=session.session_preferences
                )
                
                # If we just fetched live restaurants, cache them in the session
                if use_live_search and recommendations:
                    live_restaurant_ids = [rec.restaurant.id for rec in recommendations 
                                         if rec.restaurant.id.startswith('gp_')]
                    session.cached_live_restaurants.extend(live_restaurant_ids)
                    logger.info(f"Cached {len(live_restaurant_ids)} live restaurants for session {session_id}")
            else:
                logger.error(f"Invalid location data in session {session_id}")
                return []
            
            # Apply session-specific filtering and learning
            filtered_recommendations = self._apply_session_learning(recommendations, session)
            
            # Update session with shown restaurants
            shown_ids = [rec.restaurant.id for rec in filtered_recommendations[:limit]]
            session.shown_restaurant_ids.extend(shown_ids)
            session.last_activity = datetime.now()
            self.db_manager.save_recommendation_session(session)
            
            return filtered_recommendations[:limit]
            
        except Exception as e:
            logger.error(f"Error getting session recommendations: {e}")
            return []
    
    def _apply_session_learning(self, recommendations: List[Recommendation], 
                              session: RecommendationSession) -> List[Recommendation]:
        """Apply session-specific learning to recommendations"""
        filtered_recs = []
        
        for rec in recommendations:
            restaurant = rec.restaurant
            
            # Skip already shown restaurants
            if restaurant.id in session.shown_restaurant_ids:
                continue
            
            # Skip disliked restaurants
            if restaurant.id in session.disliked_restaurant_ids:
                continue
            
            # Get session preferences for filtering and boosting
            session_prefs = session.session_preferences
            
            # Apply preference-based scoring instead of strict filtering
            # This allows more restaurants while boosting preferred ones
            
            preference_boost = 0.0
            matches_preferences = True
            
            # Check cuisine preferences
            cuisine_boost = 0.0
            cuisine_matches = False
            if 'preferred_cuisines' in session_prefs and session_prefs['preferred_cuisines']:
                preferred_cuisines = session_prefs['preferred_cuisines']
                
                # Cuisine category mapping for flexible matching
                cuisine_categories = {
                    'asian': ['vietnamese', 'chinese', 'thai', 'japanese', 'korean', 'indian', 'sushi', 'ramen', 'pho'],
                    'european': ['italian', 'french', 'mediterranean', 'greek', 'spanish'],
                    'american': ['american', 'bbq', 'burger', 'steakhouse', 'diner'],
                    'latin': ['mexican', 'latin', 'spanish', 'cuban', 'brazilian'],
                    'middle eastern': ['middle eastern', 'turkish', 'lebanese', 'persian'],
                    'casual': ['cafe', 'fast food', 'takeout', 'pizza', 'bakery']
                }
                
                for cuisine in restaurant.cuisine_type:
                    for pref in preferred_cuisines:
                        pref_lower = pref.lower()
                        cuisine_lower = cuisine.lower()
                        
                        # Direct match
                        if pref_lower in cuisine_lower or cuisine_lower in pref_lower:
                            cuisine_matches = True
                            cuisine_boost = 0.5  # Strong boost for direct match
                            break
                        
                        # Category match - check if preference is a category that includes this cuisine
                        if pref_lower in cuisine_categories:
                            if any(cat_cuisine in cuisine_lower for cat_cuisine in cuisine_categories[pref_lower]):
                                cuisine_matches = True
                                cuisine_boost = 0.4  # Good boost for category match
                                break
                        
                        # Reverse category match - check if cuisine is a category that includes this preference
                        if cuisine_lower in cuisine_categories:
                            if any(cat_cuisine in pref_lower for cat_cuisine in cuisine_categories[cuisine_lower]):
                                cuisine_matches = True
                                cuisine_boost = 0.4  # Good boost for category match
                                break
                    
                    if cuisine_matches:
                        break
                
                # Only filter out if strongly incompatible (could add logic here if needed)
                # For now, include all restaurants but boost matching ones
                preference_boost += cuisine_boost
            
            # Check vibe preferences
            vibe_boost = 0.0
            vibe_matches = False
            if 'preferred_vibes' in session_prefs and session_prefs['preferred_vibes']:
                preferred_vibes = session_prefs['preferred_vibes']
                for vibe in restaurant.vibes:
                    if any(pref.lower() in vibe.lower() or vibe.lower() in pref.lower()
                          for pref in preferred_vibes):
                        vibe_matches = True
                        vibe_boost = 0.3  # Boost for vibe match
                        break
                
                preference_boost += vibe_boost
            
            # Log preference matching for debugging
            if preference_boost > 0:
                logger.debug(f"Boosting {restaurant.name} by {preference_boost} (cuisine: {cuisine_boost}, vibe: {vibe_boost})")
            
            # Boost score based on session learning and preferences
            adjusted_score = rec.score + preference_boost
            
            # Boost if similar to liked restaurants
            for liked_id in session.liked_restaurant_ids:
                liked_restaurant = self.db_manager.get_restaurant_by_id(liked_id)
                if liked_restaurant:
                    # Boost for similar cuisine
                    cuisine_overlap = set(restaurant.cuisine_type) & set(liked_restaurant.cuisine_type)
                    if cuisine_overlap:
                        adjusted_score += 0.2
                    
                    # Boost for similar vibes
                    vibe_overlap = set(restaurant.vibes) & set(liked_restaurant.vibes)
                    if vibe_overlap:
                        adjusted_score += 0.1
            
            # Create new recommendation with adjusted score
            adjusted_rec = Recommendation(
                restaurant=restaurant,
                score=min(adjusted_score, 1.0),
                reasoning=self._generate_session_reasoning(restaurant, session, rec.reasoning),
                distance_km=rec.distance_km
            )
            
            filtered_recs.append(adjusted_rec)
        
        # Sort by adjusted score
        filtered_recs.sort(key=lambda x: x.score, reverse=True)
        return filtered_recs
    
    def _generate_session_reasoning(self, restaurant: Restaurant, session: RecommendationSession, 
                                  base_reasoning: str) -> str:
        """Generate reasoning that incorporates session learning"""
        reasoning_parts = [base_reasoning]
        
        # Check if similar to liked restaurants
        similar_cuisines = []
        similar_vibes = []
        
        for liked_id in session.liked_restaurant_ids:
            liked_restaurant = self.db_manager.get_restaurant_by_id(liked_id)
            if liked_restaurant:
                cuisine_overlap = set(restaurant.cuisine_type) & set(liked_restaurant.cuisine_type)
                vibe_overlap = set(restaurant.vibes) & set(liked_restaurant.vibes)
                
                similar_cuisines.extend(cuisine_overlap)
                similar_vibes.extend(vibe_overlap)
        
        if similar_cuisines:
            reasoning_parts.append(f"Similar cuisine to restaurants you liked")
        
        if similar_vibes:
            reasoning_parts.append(f"Similar vibe to your preferences")
        
        # Check session preferences
        session_prefs = session.session_preferences
        if 'preferred_cuisines' in session_prefs:
            matching_cuisines = set(restaurant.cuisine_type) & set(session_prefs['preferred_cuisines'])
            if matching_cuisines:
                reasoning_parts.append(f"Matches your requested {', '.join(matching_cuisines)} preference")
        
        return "; ".join(reasoning_parts)