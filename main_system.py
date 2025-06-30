"""
main_system.py
Main system orchestrator for the Restaurant Recommendation System
"""

import logging
import time
from typing import List, Dict, Any, Optional
from pathlib import Path

from models import Restaurant, UserProfile, Recommendation
from database import DatabaseManager
from data_processor import CSVImporter
from google_places import GooglePlacesService
from preference_analyzer import PreferenceAnalyzer
from recommendation_engine import RecommendationEngine
from config import config

logger = logging.getLogger(__name__)

class RestaurantRecommendationSystem:
    """Main system orchestrator"""
    
    def __init__(self, db_path: str = None, google_api_key: Optional[str] = None):
        """Initialize the recommendation system"""
        # Use configuration defaults if not provided
        if db_path is None:
            db_path = config.default_db_path
        
        # Use provided API key, or fall back to config
        if google_api_key is None:
            google_api_key = config.get_google_api_key()
        
        self.db_manager = DatabaseManager(db_path)
        self.google_service = GooglePlacesService(google_api_key) if google_api_key else None
        self.recommendation_engine = RecommendationEngine(self.db_manager, self.google_service)
        self.csv_importer = CSVImporter(self.db_manager)
        self.preference_analyzer = PreferenceAnalyzer(self.db_manager)
        
        logger.info("Restaurant Recommendation System initialized")
        if google_api_key:
            logger.info("Google Places API integration enabled")
        else:
            logger.warning("No Google API key available - location enrichment will be limited")
            logger.info("Set GOOGLE_PLACES_API_KEY environment variable to enable Google Places integration")
    
    def import_user_restaurants(self, csv_path: str, user_id: str = "default",
                              enrich_with_google: bool = True) -> Dict[str, Any]:
        """Import user's restaurant history from CSV"""
        if not Path(csv_path).exists():
            return {"success": False, "error": f"CSV file not found: {csv_path}"}
        
        # Validate CSV format first
        validation = self.csv_importer.validate_csv_format(csv_path)
        if not validation['valid']:
            return {"success": False, "error": f"Invalid CSV format: {validation.get('error', 'Unknown error')}"}
        
        # Import restaurants
        restaurants = self.csv_importer.import_from_csv(csv_path, user_id)
        
        if not restaurants:
            return {"success": False, "error": "No restaurants could be imported from CSV"}
        
        result = {
            "success": True,
            "imported_count": len(restaurants),
            "validation": validation
        }
        
        # Enrich with Google Places data if service is available and requested
        if self.google_service and enrich_with_google:
            logger.info("Enriching restaurants with Google Places data...")
            try:
                enriched_restaurants = self.google_service.batch_enrich_restaurants(restaurants)
                
                # Save enriched data
                for restaurant in enriched_restaurants:
                    self.db_manager.save_restaurant(restaurant)
                
                # Count how many were successfully enriched
                enriched_count = sum(1 for r in enriched_restaurants if r.google_place_id)
                
                result.update({
                    "google_enrichment": True,
                    "enriched_count": enriched_count,
                    "api_requests_made": self.google_service.request_count
                })
                
                logger.info(f"Google enrichment completed: {enriched_count}/{len(restaurants)} restaurants enriched")
                
            except Exception as e:
                logger.error(f"Google enrichment failed: {e}")
                result.update({
                    "google_enrichment": False,
                    "enrichment_error": str(e)
                })
        
        # Generate user profile from imported data
        try:
            user_profile = self.preference_analyzer.analyze_user_preferences(user_id)
            self.db_manager.save_user_profile(user_profile)
            result["profile_generated"] = True
            
        except Exception as e:
            logger.error(f"Failed to generate user profile: {e}")
            result["profile_generated"] = False
        
        return result
    
    def get_recommendations_for_location(self, user_id: str, lat: float, lng: float,
                                       radius_km: float = 25, limit: int = 10,
                                       exclude_visited: bool = True, include_live_search: bool = False) -> Dict[str, Any]:
        """Get recommendations for a specific location"""
        try:
            recommendations = self.recommendation_engine.get_recommendations(
                user_id, lat, lng, radius_km, limit, exclude_visited, include_live_search
            )
            
            # Format for output
            formatted_recs = []
            for rec in recommendations:
                formatted_recs.append({
                    'restaurant': {
                        'id': rec.restaurant.id,
                        'name': rec.restaurant.name,
                        'cuisine_type': rec.restaurant.cuisine_type,
                        'vibes': rec.restaurant.vibes,
                        'location': rec.restaurant.location,
                        'rating': rec.restaurant.google_rating or rec.restaurant.user_rating,
                        'price_level': rec.restaurant.price_level,
                        'notes': rec.restaurant.notes,
                        'neighborhood': rec.restaurant.neighborhood
                    },
                    'recommendation_score': rec.score,
                    'reasoning': rec.reasoning,
                    'distance_km': rec.distance_km
                })
            
            return {
                "success": True,
                "recommendations": formatted_recs,
                "count": len(formatted_recs),
                "location": {"lat": lat, "lng": lng, "radius_km": radius_km}
            }
            
        except Exception as e:
            logger.error(f"Error getting recommendations: {e}")
            return {"success": False, "error": str(e)}
    
    def get_recommendations_for_city(self, user_id: str, city: str, state: str = None,
                                   limit: int = 10, include_live_search: bool = False) -> Dict[str, Any]:
        """Get recommendations for a specific city"""
        try:
            recommendations = self.recommendation_engine.get_recommendations_by_city(
                user_id, city, state, limit, include_live_search
            )
            
            # Format for output
            formatted_recs = []
            for rec in recommendations:
                formatted_recs.append({
                    'restaurant': {
                        'id': rec.restaurant.id,
                        'name': rec.restaurant.name,
                        'cuisine_type': rec.restaurant.cuisine_type,
                        'vibes': rec.restaurant.vibes,
                        'location': rec.restaurant.location,
                        'rating': rec.restaurant.google_rating or rec.restaurant.user_rating,
                        'price_level': rec.restaurant.price_level,
                        'notes': rec.restaurant.notes,
                        'neighborhood': rec.restaurant.neighborhood
                    },
                    'recommendation_score': rec.score,
                    'reasoning': rec.reasoning
                })
            
            return {
                "success": True,
                "recommendations": formatted_recs,
                "count": len(formatted_recs),
                "city": city,
                "state": state
            }
            
        except Exception as e:
            logger.error(f"Error getting city recommendations: {e}")
            return {"success": False, "error": str(e)}
    
    def get_wishlist_recommendations(self, user_id: str, lat: float = None, lng: float = None,
                                   radius_km: float = 50) -> Dict[str, Any]:
        """Get recommendations from user's wishlist"""
        try:
            recommendations = self.recommendation_engine.get_wishlist_recommendations(
                user_id, lat, lng, radius_km
            )
            
            # Format for output
            formatted_recs = []
            for rec in recommendations:
                formatted_recs.append({
                    'restaurant': {
                        'id': rec.restaurant.id,
                        'name': rec.restaurant.name,
                        'cuisine_type': rec.restaurant.cuisine_type,
                        'vibes': rec.restaurant.vibes,
                        'location': rec.restaurant.location,
                        'rating': rec.restaurant.google_rating or rec.restaurant.user_rating,
                        'price_level': rec.restaurant.price_level,
                        'notes': rec.restaurant.notes,
                        'neighborhood': rec.restaurant.neighborhood
                    },
                    'recommendation_score': rec.score,
                    'reasoning': rec.reasoning,
                    'distance_km': rec.distance_km
                })
            
            return {
                "success": True,
                "recommendations": formatted_recs,
                "count": len(formatted_recs)
            }
            
        except Exception as e:
            logger.error(f"Error getting wishlist recommendations: {e}")
            return {"success": False, "error": str(e)}
    
    def analyze_user_patterns(self, user_id: str) -> Dict[str, Any]:
        """Analyze and return user dining patterns"""
        try:
            restaurants = self.db_manager.get_all_restaurants()
            rated_restaurants = [r for r in restaurants if r.user_rating is not None]
            
            if not rated_restaurants:
                return {"success": False, "message": "No rated restaurants found for analysis"}
            
            # Get detailed preference insights
            insights = self.preference_analyzer.get_preference_insights(user_id)
            
            # Get user profile for additional data
            user_profile = self.db_manager.get_user_profile(user_id)
            if not user_profile:
                user_profile = self.preference_analyzer.analyze_user_preferences(user_id)
            
            analysis = {
                "success": True,
                "total_restaurants": len(rated_restaurants),
                "average_rating": user_profile.rating_patterns.get('average_rating', 0),
                "rating_distribution": user_profile.rating_patterns.get('rating_distribution', {}),
                "personality": insights.get('personality'),
                "top_cuisines": insights.get('top_cuisines', []),
                "preferred_vibes": insights.get('preferred_vibes', []),
                "price_comfort_zone": insights.get('price_comfort_zone'),
                "adventurousness": insights.get('adventurousness'),
                "consistency": insights.get('consistency'),
                "favorite_cities": insights.get('favorite_cities', []),
                "location_history": user_profile.location_history,
                "highly_rated_restaurants": self._get_highly_rated_restaurants(rated_restaurants),
                "recommendations_to_revisit": self._get_revisit_recommendations(restaurants)
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing user patterns: {e}")
            return {"success": False, "error": str(e)}
    
    def find_similar_restaurants(self, restaurant_name: str, city: str = None,
                               user_id: str = None, limit: int = 5) -> Dict[str, Any]:
        """Find restaurants similar to a given restaurant"""
        try:
            # Find the target restaurant
            all_restaurants = self.db_manager.get_all_restaurants()
            target_restaurant = None
            
            for restaurant in all_restaurants:
                name_match = restaurant.name.lower() == restaurant_name.lower()
                city_match = not city or restaurant.location.get('city', '').lower() == city.lower()
                
                if name_match and city_match:
                    target_restaurant = restaurant
                    break
            
            if not target_restaurant:
                return {
                    "success": False,
                    "error": f"Restaurant '{restaurant_name}' not found" + 
                            (f" in {city}" if city else "")
                }
            
            # Find similar restaurants
            similar = self.recommendation_engine.find_similar_restaurants(
                target_restaurant.id, limit, user_id
            )
            
            # Format response
            similar_data = []
            for restaurant in similar:
                similar_data.append({
                    "id": restaurant.id,
                    "name": restaurant.name,
                    "cuisine": restaurant.cuisine_type,
                    "vibes": restaurant.vibes,
                    "location": restaurant.location,
                    "rating": restaurant.google_rating or restaurant.user_rating,
                    "price_level": restaurant.price_level,
                    "notes": restaurant.notes
                })
            
            return {
                "success": True,
                "target_restaurant": {
                    "name": target_restaurant.name,
                    "city": target_restaurant.location.get('city'),
                    "cuisine": target_restaurant.cuisine_type
                },
                "similar_restaurants": similar_data,
                "count": len(similar_data)
            }
            
        except Exception as e:
            logger.error(f"Error finding similar restaurants: {e}")
            return {"success": False, "error": str(e)}
    
    def add_restaurant_rating(self, user_id: str, restaurant_id: str, rating: float,
                            notes: str = None) -> Dict[str, Any]:
        """Add a rating for a restaurant"""
        try:
            restaurant = self.db_manager.get_restaurant_by_id(restaurant_id)
            if not restaurant:
                return {"success": False, "error": "Restaurant not found"}
            
            # Update restaurant rating
            restaurant.user_rating = rating
            if notes:
                restaurant.notes = notes
            
            self.db_manager.save_restaurant(restaurant)
            
            # Update user preferences
            updated_profile = self.preference_analyzer.update_preferences_with_new_rating(
                user_id, restaurant, rating
            )
            
            return {
                "success": True,
                "message": f"Rating added for {restaurant.name}",
                "restaurant": restaurant.name,
                "rating": rating,
                "profile_updated": True
            }
            
        except Exception as e:
            logger.error(f"Error adding restaurant rating: {e}")
            return {"success": False, "error": str(e)}
    
    def _get_highly_rated_restaurants(self, restaurants: List[Restaurant]) -> List[Dict]:
        """Get highly rated restaurants for analysis"""
        highly_rated = [r for r in restaurants if r.user_rating >= 4.0]
        highly_rated.sort(key=lambda x: x.user_rating, reverse=True)
        
        return [
            {
                "name": r.name,
                "rating": r.user_rating,
                "cuisine": r.cuisine_type,
                "city": r.location.get('city'),
                "notes": r.notes
            }
            for r in highly_rated[:10]
        ]
    
    def _get_revisit_recommendations(self, restaurants: List[Restaurant]) -> List[Dict]:
        """Get restaurants marked for revisit"""
        to_revisit = [r for r in restaurants if r.revisit_preference in ['Y', 'Yes', 'yes']]
        
        return [
            {
                "name": r.name,
                "cuisine": r.cuisine_type,
                "city": r.location.get('city'),
                "vibes": r.vibes,
                "price_level": r.price_level,
                "notes": r.notes
            }
            for r in to_revisit[:10]
        ]
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get system statistics"""
        try:
            all_restaurants = self.db_manager.get_all_restaurants()
            rated_count = len([r for r in all_restaurants if r.user_rating is not None])
            
            stats = {
                "total_restaurants": len(all_restaurants),
                "rated_restaurants": rated_count,
                "unrated_restaurants": len(all_restaurants) - rated_count,
                "google_enriched": len([r for r in all_restaurants if r.google_place_id]),
                "cities_covered": len(set(r.location.get('city') for r in all_restaurants if r.location.get('city'))),
                "cuisines_covered": len(set(cuisine for r in all_restaurants for cuisine in r.cuisine_type))
            }
            
            if self.google_service:
                stats["google_api_usage"] = self.google_service.get_api_usage_stats()
            
            return {"success": True, "stats": stats}
            
        except Exception as e:
            logger.error(f"Error getting system stats: {e}")
            return {"success": False, "error": str(e)}