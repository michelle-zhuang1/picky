"""
api.py
API interface for the Restaurant Recommendation System
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
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
                               limit: int = 10, include_live_search: bool = False, 
                               use_learning: bool = False) -> Dict[str, Any]:
        """Get restaurant recommendations for a specific city"""
        try:
            if use_learning:
                # Get the most recent session for this user and apply its learning
                result = self._get_recommendations_with_learning(user_id, city, state, limit, include_live_search)
            else:
                result = self.system.get_recommendations_for_city(user_id, city, state, limit, include_live_search)
            
            if result["success"]:
                logger.info(f"Generated {result['count']} city recommendations for {city}")
            
            return result
            
        except Exception as e:
            error_msg = f"Error getting city recommendations: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def _get_recommendations_with_learning(self, user_id: str, city: str, state: str = None,
                                         limit: int = 10, include_live_search: bool = False) -> Dict[str, Any]:
        """Get recommendations with learning applied from most recent session"""
        try:
            # Get the most recent session with feedback for this user in this city
            recent_sessions = self.system.db_manager.get_user_sessions(user_id, limit=10)
            relevant_session = None
            
            for session in recent_sessions:
                session_city = session.location.get('city', '').lower()
                session_state = session.location.get('state', '').lower()
                
                if session_city == city.lower():
                    if not state or session_state == state.lower():
                        # Only use sessions that have feedback
                        if session.liked_restaurant_ids or session.disliked_restaurant_ids or session.session_preferences:
                            relevant_session = session
                            break
            
            if not relevant_session:
                logger.info(f"No previous sessions found for {city}, using regular recommendations")
                return self.system.get_recommendations_for_city(user_id, city, state, limit, include_live_search)
            
            logger.info(f"Applying learning from session {relevant_session.session_id[:8]}... "
                       f"({len(relevant_session.liked_restaurant_ids)} liked, "
                       f"{len(relevant_session.disliked_restaurant_ids)} disliked)")
            
            # Get base recommendations
            recommendations = self.system.recommendation_engine.get_recommendations_by_city(
                user_id, city, state, limit * 2, include_live_search  # Get more to filter
            )
            
            # Apply session learning
            learned_recommendations = self.system.recommendation_engine._apply_session_learning(
                recommendations, relevant_session
            )
            
            # Format like regular city recommendations
            formatted_recs = []
            for rec in learned_recommendations[:limit]:
                formatted_recs.append({
                    'restaurant': {
                        'id': rec.restaurant.id,
                        'name': rec.restaurant.name,
                        'cuisine_type': rec.restaurant.cuisine_type,
                        'location': rec.restaurant.location,
                        'rating': rec.restaurant.user_rating or rec.restaurant.google_rating,
                        'price_level': rec.restaurant.price_level,
                        'vibes': rec.restaurant.vibes,
                        'google_place_id': rec.restaurant.google_place_id
                    },
                    'recommendation_score': rec.score,
                    'reasoning': rec.reasoning,
                    'distance_km': rec.distance_km
                })
            
            return {
                "success": True,
                "count": len(formatted_recs),
                "recommendations": formatted_recs,
                "learning_applied": True,
                "session_id": relevant_session.session_id
            }
            
        except Exception as e:
            logger.error(f"Error applying learning: {e}")
            # Fallback to regular recommendations
            return self.system.get_recommendations_for_city(user_id, city, state, limit, include_live_search)
    
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
    
    def start_interactive_session(self, user_id: str, city: str = None, state: str = None,
                                 latitude: float = None, longitude: float = None) -> Dict[str, Any]:
        """Start an interactive recommendation session"""
        try:
            # Build location dict
            location = {}
            if latitude and longitude:
                location = {'lat': latitude, 'lng': longitude}
            if city:
                location['city'] = city
            if state:
                location['state'] = state
            
            if not location:
                return {"success": False, "error": "Must provide either city or lat/lng"}
            
            session_id = self.system.recommendation_engine.start_recommendation_session(user_id, location)
            
            return {
                "success": True,
                "session_id": session_id,
                "message": f"Started interactive session for {city or 'location'}"
            }
            
        except Exception as e:
            error_msg = f"Error starting interactive session: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def provide_session_feedback(self, session_id: str, 
                                liked_restaurant_ids: List[str] = None,
                                disliked_restaurant_ids: List[str] = None,
                                cuisine_preferences: List[str] = None,
                                vibe_preferences: List[str] = None) -> Dict[str, Any]:
        """Provide feedback for a recommendation session"""
        try:
            liked_ids = liked_restaurant_ids or []
            disliked_ids = disliked_restaurant_ids or []
            
            success = self.system.recommendation_engine.collect_session_feedback(
                session_id=session_id,
                liked_restaurant_ids=liked_ids,
                disliked_restaurant_ids=disliked_ids,
                cuisine_preferences=cuisine_preferences,
                vibe_preferences=vibe_preferences
            )
            
            if success:
                return {
                    "success": True,
                    "message": f"Collected feedback: {len(liked_ids)} liked, {len(disliked_ids)} disliked"
                }
            else:
                return {"success": False, "error": "Failed to collect feedback"}
                
        except Exception as e:
            error_msg = f"Error providing session feedback: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def get_session_recommendations(self, session_id: str, limit: int = 10) -> Dict[str, Any]:
        """Get recommendations for a session with applied learning"""
        try:
            recommendations = self.system.recommendation_engine.get_session_recommendations(
                session_id=session_id,
                limit=limit,
                include_live_search=True
            )
            
            if not recommendations:
                return {
                    "success": True, 
                    "count": 0, 
                    "recommendations": [],
                    "message": "No new recommendations found. Try adjusting your preferences."
                }
            
            # Format recommendations
            formatted_recs = []
            for rec in recommendations:
                formatted_recs.append({
                    'restaurant': {
                        'id': rec.restaurant.id,
                        'name': rec.restaurant.name,
                        'cuisine_type': rec.restaurant.cuisine_type,
                        'location': rec.restaurant.location,
                        'rating': rec.restaurant.user_rating or rec.restaurant.google_rating,
                        'price_level': rec.restaurant.price_level,
                        'vibes': rec.restaurant.vibes,
                        'google_place_id': rec.restaurant.google_place_id
                    },
                    'recommendation_score': rec.score,
                    'reasoning': rec.reasoning,
                    'distance_km': rec.distance_km
                })
            
            return {
                "success": True,
                "count": len(formatted_recs),
                "recommendations": formatted_recs,
                "session_id": session_id
            }
            
        except Exception as e:
            error_msg = f"Error getting session recommendations: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def add_restaurant_by_name(self, name: str, city: str, state: str = None, 
                              user_id: str = None, notes: str = None, 
                              is_wishlist: bool = False) -> Dict[str, Any]:
        """Search for restaurant by name and prepare for addition to database"""
        try:
            if not self.system.google_service:
                return {"success": False, "error": "Google Places API not configured"}
            
            # Build search query
            search_query = f"{name} restaurant {city}"
            if state:
                search_query += f" {state}"
            
            # Search for restaurants using Google Places text search
            places_data = self.system.google_service.search_restaurants_by_text(
                query=search_query,
                location=f"{city}{', ' + state if state else ''}",
                limit=1  # Only get the best match
            )
            
            if not places_data:
                return {"success": False, "error": f"No restaurants found matching '{name}' in {city}"}
            
            # Convert to restaurant object
            restaurants = self.system.google_service.convert_places_to_restaurants(places_data, user_id or "manual_add")
            
            if not restaurants:
                return {"success": False, "error": "Failed to process restaurant data"}
            
            restaurant = restaurants[0]
            
            # Check if restaurant already exists in database
            existing_restaurants = self.system.db_manager.get_all_restaurants()
            for existing in existing_restaurants:
                if existing.google_place_id and existing.google_place_id == restaurant.google_place_id:
                    return {
                        "success": True,
                        "duplicate": True,
                        "existing_restaurant": {
                            'id': existing.id,
                            'name': existing.name,
                            'address': existing.location.get('address', ''),
                            'city': existing.location.get('city', ''),
                            'cuisine_type': existing.cuisine_type,
                            'google_rating': existing.google_rating,
                            'price_level': existing.price_level
                        }
                    }
            
            # Add user-provided metadata
            if notes:
                restaurant.notes = notes
            if is_wishlist:
                restaurant.is_wishlist = True
            
            # Store temporarily for confirmation
            import uuid
            temp_id = str(uuid.uuid4())
            
            # Store in a temporary collection (we'll use a simple dict for now)
            if not hasattr(self, '_temp_restaurants'):
                self._temp_restaurants = {}
            
            self._temp_restaurants[temp_id] = restaurant
            
            return {
                "success": True,
                "duplicate": False,
                "temp_id": temp_id,
                "restaurant": {
                    'name': restaurant.name,
                    'address': restaurant.location.get('address', ''),
                    'city': restaurant.location.get('city', ''),
                    'cuisine_type': restaurant.cuisine_type,
                    'google_rating': restaurant.google_rating,
                    'price_level': restaurant.price_level,
                    'google_place_id': restaurant.google_place_id
                }
            }
            
        except Exception as e:
            error_msg = f"Error searching for restaurant: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def confirm_restaurant_addition(self, temp_id: str) -> Dict[str, Any]:
        """Confirm and save restaurant to database"""
        try:
            if not hasattr(self, '_temp_restaurants') or temp_id not in self._temp_restaurants:
                return {"success": False, "error": "Restaurant confirmation expired or invalid"}
            
            restaurant = self._temp_restaurants[temp_id]
            
            # Save to database
            self.system.db_manager.save_restaurant(restaurant)
            
            # Clean up temporary storage
            del self._temp_restaurants[temp_id]
            
            logger.info(f"Successfully added restaurant {restaurant.name} to database")
            
            return {
                "success": True,
                "restaurant_id": restaurant.id,
                "message": f"Restaurant '{restaurant.name}' added successfully"
            }
            
        except Exception as e:
            error_msg = f"Error confirming restaurant addition: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def update_restaurant_notes(self, restaurant_id: str, notes: str = None, 
                               is_wishlist: bool = False) -> Dict[str, Any]:
        """Update existing restaurant's notes and wishlist status"""
        try:
            restaurant = self.system.db_manager.get_restaurant_by_id(restaurant_id)
            if not restaurant:
                return {"success": False, "error": "Restaurant not found"}
            
            # Update notes and wishlist status
            if notes:
                restaurant.notes = notes
            if is_wishlist:
                restaurant.is_wishlist = True
            
            restaurant.last_updated = datetime.now()
            
            # Save updated restaurant
            self.system.db_manager.save_restaurant(restaurant)
            
            logger.info(f"Updated restaurant {restaurant.name}")
            
            return {
                "success": True,
                "message": f"Restaurant '{restaurant.name}' updated successfully"
            }
            
        except Exception as e:
            error_msg = f"Error updating restaurant: {str(e)}"
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