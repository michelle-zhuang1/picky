"""
api.py
API interface for the Restaurant Recommendation System
"""

import logging
from typing import Dict, Any, Optional
from main_system import RestaurantRecommendationSystem
from config import config

logger = logging.getLogger(__name__)

class RestaurantRecommendationAPI:
    """Simple API wrapper for the recommendation system"""
    
    def __init__(self, db_path: str = None, google_api_key: Optional[str] = None):
        """Initialize the API with the recommendation system"""
        self.system = RestaurantRecommendationSystem(db_path, google_api_key)
        logger.info("Restaurant Recommendation API initialized")
        
        # Provide helpful info about Google API integration
        if config.has_google_api_key() or google_api_key:
            logger.info("Google Places API integration is enabled")
        else:
            logger.info("Google Places API integration is disabled - set GOOGLE_PLACES_API_KEY environment variable to enable")
    
    def upload_csv(self, csv_path: str, user_id: str, 
                   enrich_with_google: bool = True) -> Dict[str, Any]:
        """Upload and process CSV file"""
        try:
            result = self.system.import_user_restaurants(csv_path, user_id, enrich_with_google)
            
            if result["success"]:
                logger.info(f"Successfully imported restaurants for user {user_id}")
            else:
                logger.error(f"Failed to import CSV for user {user_id}: {result.get('error')}")
            
            return result
            
        except Exception as e:
            error_msg = f"Error importing CSV: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def get_recommendations(self, user_id: str, latitude: float, longitude: float,
                          radius_km: float = 25, limit: int = 10,
                          exclude_visited: bool = True, include_live_search: bool = False) -> Dict[str, Any]:
        """Get restaurant recommendations for a location"""
        try:
            result = self.system.get_recommendations_for_location(
                user_id, latitude, longitude, radius_km, limit, exclude_visited, include_live_search
            )
            
            if result["success"]:
                logger.info(f"Generated {result['count']} recommendations for user {user_id}")
            
            return result
            
        except Exception as e:
            error_msg = f"Error getting recommendations: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def get_city_recommendations(self, user_id: str, city: str, state: str = None,
                               limit: int = 10, include_live_search: bool = False) -> Dict[str, Any]:
        """Get restaurant recommendations for a specific city"""
        try:
            result = self.system.get_recommendations_for_city(user_id, city, state, limit, include_live_search)
            
            if result["success"]:
                logger.info(f"Generated {result['count']} city recommendations for {city}")
            
            return result
            
        except Exception as e:
            error_msg = f"Error getting city recommendations: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def get_wishlist_recommendations(self, user_id: str, latitude: float = None,
                                   longitude: float = None, radius_km: float = 50) -> Dict[str, Any]:
        """Get recommendations from user's wishlist"""
        try:
            result = self.system.get_wishlist_recommendations(user_id, latitude, longitude, radius_km)
            
            if result["success"]:
                logger.info(f"Generated {result['count']} wishlist recommendations")
            
            return result
            
        except Exception as e:
            error_msg = f"Error getting wishlist recommendations: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def get_user_analysis(self, user_id: str) -> Dict[str, Any]:
        """Get user dining pattern analysis"""
        try:
            result = self.system.analyze_user_patterns(user_id)
            
            if result["success"]:
                logger.info(f"Generated user analysis for {user_id}")
            
            return result
            
        except Exception as e:
            error_msg = f"Error analyzing user patterns: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def find_similar_restaurants(self, restaurant_name: str, city: str = None,
                               user_id: str = None, limit: int = 5) -> Dict[str, Any]:
        """Find restaurants similar to a given restaurant"""
        try:
            result = self.system.find_similar_restaurants(restaurant_name, city, user_id, limit)
            
            if result["success"]:
                logger.info(f"Found {result['count']} similar restaurants to {restaurant_name}")
            
            return result
            
        except Exception as e:
            error_msg = f"Error finding similar restaurants: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def add_restaurant_rating(self, user_id: str, restaurant_id: str, rating: float,
                            notes: str = None) -> Dict[str, Any]:
        """Add a rating for a restaurant"""
        try:
            if not 1.0 <= rating <= 5.0:
                return {"success": False, "error": "Rating must be between 1.0 and 5.0"}
            
            result = self.system.add_restaurant_rating(user_id, restaurant_id, rating, notes)
            
            if result["success"]:
                logger.info(f"Added rating {rating} for restaurant {restaurant_id}")
            
            return result
            
        except Exception as e:
            error_msg = f"Error adding restaurant rating: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get system statistics"""
        try:
            result = self.system.get_system_stats()
            
            if result["success"]:
                logger.info("Retrieved system statistics")
            
            return result
            
        except Exception as e:
            error_msg = f"Error getting system stats: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def validate_csv_format(self, csv_path: str) -> Dict[str, Any]:
        """Validate CSV format before import"""
        try:
            validation = self.system.csv_importer.validate_csv_format(csv_path)
            logger.info(f"CSV validation completed for {csv_path}")
            return {"success": True, "validation": validation}
            
        except Exception as e:
            error_msg = f"Error validating CSV: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def search_nearby_restaurants(self, latitude: float, longitude: float, 
                                radius_km: float = 25, cuisine_type: str = None,
                                limit: int = 10, user_id: str = "live_search") -> Dict[str, Any]:
        """Search for restaurants using live Google Places data"""
        try:
            if not self.system.google_service:
                return {"success": False, "error": "Google Places API not configured"}
            
            # Convert km to meters
            radius_meters = int(radius_km * 1000)
            
            # Search for nearby restaurants
            places_data = self.system.google_service.search_nearby_restaurants(
                lat=latitude, 
                lng=longitude, 
                radius_meters=radius_meters,
                cuisine_type=cuisine_type,
                limit=limit
            )
            
            if not places_data:
                return {"success": True, "count": 0, "restaurants": []}
            
            # Convert to restaurant objects
            restaurants = self.system.google_service.convert_places_to_restaurants(places_data, user_id)
            
            # Format results
            formatted_restaurants = []
            for restaurant in restaurants:
                formatted_restaurants.append({
                    'id': restaurant.id,
                    'name': restaurant.name,
                    'cuisine_type': restaurant.cuisine_type,
                    'location': restaurant.location,
                    'google_rating': restaurant.google_rating,
                    'price_level': restaurant.price_level,
                    'vibes': restaurant.vibes,
                    'features': restaurant.features
                })
            
            return {
                "success": True,
                "count": len(formatted_restaurants),
                "restaurants": formatted_restaurants,
                "search_location": {"latitude": latitude, "longitude": longitude, "radius_km": radius_km}
            }
            
        except Exception as e:
            error_msg = f"Error searching nearby restaurants: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}


# Convenience functions for direct usage
def create_api(db_path: str = "restaurant_recommendations.db", 
               google_api_key: str = None) -> RestaurantRecommendationAPI:
    """Create and return a new API instance"""
    return RestaurantRecommendationAPI(db_path, google_api_key)


def quick_import_and_analyze(csv_path: str, user_id: str = "default",
                           google_api_key: str = None) -> Dict[str, Any]:
    """Quick function to import CSV and get basic analysis"""
    api = create_api(google_api_key=google_api_key)
    
    # Import data
    import_result = api.upload_csv(csv_path, user_id)
    if not import_result["success"]:
        return import_result
    
    # Get analysis
    analysis_result = api.get_user_analysis(user_id)
    
    return {
        "import_result": import_result,
        "analysis_result": analysis_result
    }


def get_recommendations_for_trip(csv_path: str, city: str, state: str = None,
                               user_id: str = "default", limit: int = 10,
                               google_api_key: str = None) -> Dict[str, Any]:
    """Quick function to get recommendations for a trip to a specific city"""
    api = create_api(google_api_key=google_api_key)
    
    # Import data if needed
    import_result = api.upload_csv(csv_path, user_id, enrich_with_google=False)
    if not import_result["success"]:
        return import_result
    
    # Get city recommendations
    return api.get_city_recommendations(user_id, city, state, limit)