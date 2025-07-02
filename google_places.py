"""
google_places.py
Google Places API integration for restaurant data enrichment
"""

import requests
import logging
import time
import re
from typing import Dict, List, Optional
from fuzzywuzzy import fuzz
from models import Restaurant

logger = logging.getLogger(__name__)

class GooglePlacesService:
    """Handles Google Places API integration"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://maps.googleapis.com/maps/api/place"
        self.session = requests.Session()
        self.request_count = 0
        self.last_request_time = 0
    
    def find_place(self, restaurant: Restaurant) -> Optional[Dict]:
        """Find place using Google Places API"""
        if not self.api_key:
            logger.warning("No Google Places API key provided")
            return None
        
        # Rate limiting
        self._handle_rate_limiting()
        
        # Construct search query
        query = f"{restaurant.name}"
        if restaurant.location.get('city'):
            query += f" {restaurant.location['city']}"
        if restaurant.location.get('state'):
            query += f" {restaurant.location['state']}"
        
        params = {
            'query': query,
            'key': self.api_key,
            'fields': 'place_id,name,geometry,formatted_address,rating,price_level,types'
        }
        
        try:
            response = self.session.get(f"{self.base_url}/textsearch/json", params=params)
            response.raise_for_status()
            data = response.json()
            
            self.request_count += 1
            self.last_request_time = time.time()
            
            if data.get('results'):
                # Use fuzzy matching to find best result
                best_match = self._find_best_match(restaurant.name, data['results'])
                return best_match
            
            logger.info(f"No results found for: {query}")
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Google Places API request error: {e}")
            return None
        except Exception as e:
            logger.error(f"Google Places API error: {e}")
            return None
    
    def get_place_details(self, place_id: str) -> Optional[Dict]:
        """Get detailed information about a place"""
        if not self.api_key:
            return None
        
        self._handle_rate_limiting()
        
        params = {
            'place_id': place_id,
            'key': self.api_key,
            'fields': 'name,formatted_address,geometry,rating,price_level,opening_hours,website,formatted_phone_number,reviews'
        }
        
        try:
            response = self.session.get(f"{self.base_url}/details/json", params=params)
            response.raise_for_status()
            data = response.json()
            
            self.request_count += 1
            self.last_request_time = time.time()
            
            return data.get('result')
            
        except Exception as e:
            logger.error(f"Google Places Details API error: {e}")
            return None
    
    def _find_best_match(self, query_name: str, results: List[Dict]) -> Optional[Dict]:
        """Find best matching restaurant from results"""
        best_score = 0
        best_match = None
        
        for result in results:
            # Calculate similarity score
            name_score = fuzz.ratio(query_name.lower(), result['name'].lower())
            
            # Boost score for restaurant types
            type_boost = 0
            result_types = result.get('types', [])
            restaurant_types = ['restaurant', 'food', 'establishment', 'meal_takeaway', 'meal_delivery']
            if any(t in result_types for t in restaurant_types):
                type_boost = 10
            
            total_score = name_score + type_boost
            
            if total_score > best_score and name_score > 40:  # Minimum name similarity threshold
                best_score = total_score
                best_match = result
        
        if best_match:
            logger.info(f"Found match for '{query_name}': '{best_match['name']}' (score: {best_score})")
        
        return best_match
    
    def enrich_restaurant(self, restaurant: Restaurant) -> Restaurant:
        """Enrich restaurant with Google Places data"""
        place_data = self.find_place(restaurant)
        
        if place_data:
            restaurant.google_place_id = place_data.get('place_id')
            restaurant.google_rating = place_data.get('rating')
            
            # Update price level if not already set
            if not restaurant.price_level and place_data.get('price_level'):
                restaurant.price_level = place_data.get('price_level')
            
            # Update location with coordinates and address
            geometry = place_data.get('geometry', {})
            location = geometry.get('location', {})
            if location:
                restaurant.location.update({
                    'lat': location.get('lat'),
                    'lng': location.get('lng')
                })
                
                # Update address if not set
                if not restaurant.location.get('address') and place_data.get('formatted_address'):
                    restaurant.location['address'] = place_data.get('formatted_address')
            
            logger.info(f"Enriched restaurant: {restaurant.name}")
        else:
            logger.warning(f"Could not find Google Places data for: {restaurant.name}")
        
        return restaurant
    
    def enrich_restaurant_with_details(self, restaurant: Restaurant) -> Restaurant:
        """Enrich restaurant with detailed Google Places data"""
        if not restaurant.google_place_id:
            # Try to find the place first
            restaurant = self.enrich_restaurant(restaurant)
        
        if restaurant.google_place_id:
            details = self.get_place_details(restaurant.google_place_id)
            if details:
                # Add additional features
                if not restaurant.features:
                    restaurant.features = {}
                
                # Add website
                if details.get('website'):
                    restaurant.features['website'] = details['website']
                
                # Add phone number
                if details.get('formatted_phone_number'):
                    restaurant.features['phone'] = details['formatted_phone_number']
                
                # Add opening hours info
                if details.get('opening_hours'):
                    restaurant.features['hours_available'] = True
                    if details['opening_hours'].get('open_now') is not None:
                        restaurant.features['open_now'] = details['opening_hours']['open_now']
                
                # Process reviews for summary
                if details.get('reviews'):
                    restaurant.reviews_summary = self._generate_reviews_summary(details['reviews'])
                
                logger.info(f"Added detailed data for: {restaurant.name}")
        
        return restaurant
    
    def _generate_reviews_summary(self, reviews: List[Dict]) -> str:
        """Generate a summary from Google reviews"""
        if not reviews:
            return ""
        
        # Extract key information from reviews
        positive_keywords = []
        negative_keywords = []
        
        for review in reviews[:5]:  # Process first 5 reviews
            text = review.get('text', '').lower()
            rating = review.get('rating', 0)
            
            # Simple keyword extraction based on rating
            if rating >= 4:
                # Look for positive mentions
                if 'great' in text or 'excellent' in text or 'amazing' in text:
                    positive_keywords.append('highly praised')
                if 'food' in text and ('good' in text or 'delicious' in text):
                    positive_keywords.append('great food')
                if 'service' in text and 'good' in text:
                    positive_keywords.append('good service')
            elif rating <= 2:
                # Look for negative mentions
                if 'slow' in text:
                    negative_keywords.append('slow service')
                if 'expensive' in text or 'overpriced' in text:
                    negative_keywords.append('pricey')
        
        # Create summary
        summary_parts = []
        if positive_keywords:
            summary_parts.append(f"Positives: {', '.join(set(positive_keywords))}")
        if negative_keywords:
            summary_parts.append(f"Concerns: {', '.join(set(negative_keywords))}")
        
        return "; ".join(summary_parts) if summary_parts else "Mixed reviews"
    
    def _handle_rate_limiting(self):
        """Handle API rate limiting"""
        current_time = time.time()
        
        # Basic rate limiting: max 10 requests per second
        if self.last_request_time > 0:
            time_since_last = current_time - self.last_request_time
            if time_since_last < 0.1:  # 100ms between requests
                time.sleep(0.1 - time_since_last)
        
        # Log request count for monitoring
        if self.request_count % 50 == 0 and self.request_count > 0:
            logger.info(f"Google Places API requests made: {self.request_count}")
    
    def batch_enrich_restaurants(self, restaurants: List[Restaurant], 
                               detailed: bool = False) -> List[Restaurant]:
        """Enrich multiple restaurants with rate limiting"""
        enriched_restaurants = []
        total = len(restaurants)
        
        logger.info(f"Starting batch enrichment of {total} restaurants")
        
        for i, restaurant in enumerate(restaurants):
            try:
                if detailed:
                    enriched = self.enrich_restaurant_with_details(restaurant)
                else:
                    enriched = self.enrich_restaurant(restaurant)
                
                enriched_restaurants.append(enriched)
                
                # Progress logging
                if (i + 1) % 10 == 0:
                    logger.info(f"Processed {i + 1}/{total} restaurants")
                
                # Additional pause every 50 requests to be safe
                if (i + 1) % 50 == 0:
                    logger.info("Pausing for rate limiting...")
                    time.sleep(2)
                    
            except Exception as e:
                logger.error(f"Failed to enrich restaurant {restaurant.name}: {e}")
                enriched_restaurants.append(restaurant)  # Add original restaurant
        
        logger.info(f"Batch enrichment completed. Processed {len(enriched_restaurants)} restaurants")
        return enriched_restaurants
    
    def search_nearby_restaurants(self, lat: float, lng: float, radius_meters: int = 25000, 
                                cuisine_type: str = None, limit: int = 20) -> List[Dict]:
        """Search for restaurants near a location using Google Places Nearby Search with pagination"""
        if not self.api_key:
            logger.warning("No Google Places API key provided")
            return []
        
        all_results = []
        next_page_token = None
        max_pages = 3  # Google Places allows up to 3 pages (60 results total)
        page_count = 0
        
        while page_count < max_pages and len(all_results) < limit:
            self._handle_rate_limiting()
            
            params = {
                'location': f'{lat},{lng}',
                'radius': min(radius_meters, 50000),  # Max 50km for Google Places
                'type': 'restaurant',
                'key': self.api_key
            }
            
            # Add cuisine filter if specified
            if cuisine_type:
                params['keyword'] = cuisine_type
                
            if next_page_token:
                params['pagetoken'] = next_page_token
            
            try:
                response = self.session.get(f"{self.base_url}/nearbysearch/json", params=params)
                response.raise_for_status()
                data = response.json()
                
                self.request_count += 1
                self.last_request_time = time.time()
                
                results = data.get('results', [])
                all_results.extend(results)
                
                next_page_token = data.get('next_page_token')
                page_count += 1
                
                logger.info(f"Page {page_count}: Found {len(results)} nearby restaurants (total: {len(all_results)})")
                
                # If no next page token, we've reached the end
                if not next_page_token:
                    break
                
                # Google requires a short delay before using the next page token
                if next_page_token and page_count < max_pages and len(all_results) < limit:
                    time.sleep(2)
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Google Places Nearby Search error: {e}")
                break
            except Exception as e:
                logger.error(f"Google Places API error: {e}")
                break
        
        # Return up to the requested limit
        final_results = all_results[:limit]
        logger.info(f"Found {len(final_results)} nearby restaurants")
        return final_results
    
    def search_restaurants_by_text(self, query: str, location: str = None, limit: int = 20) -> List[Dict]:
        """Search for restaurants using Google Places Text Search with pagination support"""
        if not self.api_key:
            logger.warning("No Google Places API key provided")
            return []
        
        all_results = []
        next_page_token = None
        max_pages = 3  # Google Places allows up to 3 pages (60 results total)
        page_count = 0
        
        # Build search query
        search_query = f"restaurants {query}"
        if location:
            search_query += f" {location}"
        
        while page_count < max_pages and len(all_results) < limit:
            self._handle_rate_limiting()
            
            params = {
                'query': search_query,
                'key': self.api_key,
                'type': 'restaurant'
            }
            
            if next_page_token:
                params['pagetoken'] = next_page_token
            
            try:
                response = self.session.get(f"{self.base_url}/textsearch/json", params=params)
                response.raise_for_status()
                data = response.json()
                
                self.request_count += 1
                self.last_request_time = time.time()
                
                results = data.get('results', [])
                all_results.extend(results)
                
                next_page_token = data.get('next_page_token')
                page_count += 1
                
                logger.info(f"Page {page_count}: Found {len(results)} restaurants (total: {len(all_results)})")
                
                # If no next page token, we've reached the end
                if not next_page_token:
                    break
                
                # Google requires a short delay before using the next page token
                if next_page_token and page_count < max_pages and len(all_results) < limit:
                    time.sleep(2)
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Google Places Text Search error: {e}")
                break
            except Exception as e:
                logger.error(f"Google Places API error: {e}")
                break
        
        # Return up to the requested limit
        final_results = all_results[:limit]
        logger.info(f"Found {len(final_results)} restaurants for query: {search_query}")
        return final_results
    
    def _parse_address(self, formatted_address: str) -> Dict[str, str]:
        """Parse formatted address to extract city and state"""
        if not formatted_address:
            return {'city': '', 'state': ''}
        
        # Common US address patterns:
        # "1234 Main St, Seattle, WA 98101, United States"
        # "1234 Main St, Seattle, WA, United States"
        # "Seattle, WA 98101, United States"
        
        # Remove "United States" from the end if present
        address = re.sub(r',\s*United States\s*$', '', formatted_address.strip())
        
        # Split by commas and get the parts
        parts = [part.strip() for part in address.split(',')]
        
        city = ''
        state = ''
        
        if len(parts) >= 2:
            # Look for state pattern (2 letter code possibly followed by zip)
            for i, part in enumerate(parts):
                # Check if this part contains a state code
                state_match = re.search(r'\b([A-Z]{2})\b', part)
                if state_match and i > 0:
                    state = state_match.group(1)
                    # The city should be the part before the state
                    city = parts[i-1].strip()
                    break
            
            # If no state pattern found, assume last part might be state and second to last is city
            if not city and not state and len(parts) >= 2:
                potential_state = parts[-1].strip()
                potential_city = parts[-2].strip()
                
                # Check if potential_state looks like a state (2 letters or state name)
                if re.match(r'^[A-Z]{2}$', potential_state) or len(potential_state.split()) == 1:
                    state = potential_state
                    city = potential_city
        
        return {'city': city, 'state': state}
    
    def convert_places_to_restaurants(self, places_data: List[Dict], user_id: str = "live_search") -> List[Restaurant]:
        """Convert Google Places API results to Restaurant objects"""
        restaurants = []
        
        for place in places_data:
            try:
                # Extract location info
                geometry = place.get('geometry', {})
                location_data = geometry.get('location', {})
                
                # Parse address to extract city and state
                formatted_address = place.get('formatted_address', place.get('vicinity', ''))
                parsed_address = self._parse_address(formatted_address)
                
                # Create restaurant object
                restaurant = Restaurant(
                    id=f"gp_{place.get('place_id', '')}",
                    name=place.get('name', 'Unknown'),
                    cuisine_type=self._extract_cuisine_types(place.get('types', []), place.get('name', '')),
                    location={
                        'lat': location_data.get('lat'),
                        'lng': location_data.get('lng'),
                        'address': formatted_address,
                        'city': parsed_address['city'],
                        'state': parsed_address['state']
                    },
                    google_place_id=place.get('place_id'),
                    google_rating=place.get('rating'),
                    price_level=place.get('price_level'),
                    user_rating=None,
                    vibes=self._extract_vibes_from_types(place.get('types', [])),
                    features={
                        'open_now': place.get('opening_hours', {}).get('open_now', None),
                        'photo_reference': place.get('photos', [{}])[0].get('photo_reference') if place.get('photos') else None
                    }
                )
                
                restaurants.append(restaurant)
                
            except Exception as e:
                logger.warning(f"Error converting place to restaurant: {e}")
                continue
        
        return restaurants
    
    def _extract_cuisine_types(self, google_types: List[str], restaurant_name: str = "") -> List[str]:
        """Extract cuisine types from Google Places types and restaurant name"""
        cuisine_mapping = {
            'chinese_restaurant': 'Chinese',
            'italian_restaurant': 'Italian', 
            'japanese_restaurant': 'Japanese',
            'indian_restaurant': 'Indian',
            'mexican_restaurant': 'Mexican',
            'thai_restaurant': 'Thai',
            'french_restaurant': 'French',
            'american_restaurant': 'American',
            'mediterranean_restaurant': 'Mediterranean',
            'korean_restaurant': 'Korean',
            'vietnamese_restaurant': 'Vietnamese',
            'pizza_restaurant': 'Pizza',
            'seafood_restaurant': 'Seafood',
            'steakhouse': 'Steakhouse',
            'bakery': 'Bakery',
            'cafe': 'Cafe',
            'night_club': 'Bar',
            'fast_food_restaurant': 'Fast Food',
            'meal_takeaway': 'Takeout',
            'meal_delivery': 'Delivery'
        }
        
        cuisines = []
        
        # First try to extract from Google types, but prioritize specific cuisines over generic ones
        specific_cuisines = []
        generic_types = []
        
        for gtype in google_types:
            if gtype in cuisine_mapping:
                if gtype in ['cafe', 'bakery', 'night_club']:
                    generic_types.append(cuisine_mapping[gtype])
                else:
                    specific_cuisines.append(cuisine_mapping[gtype])
        
        # Prefer specific cuisines over generic ones
        cuisines.extend(specific_cuisines)
        if not cuisines:
            cuisines.extend(generic_types)
        
        # If no specific cuisine found, try to infer from restaurant name
        if not cuisines and restaurant_name:
            name_lower = restaurant_name.lower()
            name_keywords = {
                'pizza': 'Pizza',
                'pizzeria': 'Pizza',
                'sushi': 'Japanese', 
                'ramen': 'Japanese',
                'izakaya': 'Japanese',
                'pho': 'Vietnamese',
                'thai': 'Thai',
                'pad thai': 'Thai',
                'taco': 'Mexican',
                'burrito': 'Mexican',
                'cantina': 'Mexican',
                'chinese': 'Chinese',
                'dim sum': 'Chinese',
                'indian': 'Indian',
                'curry': 'Indian',
                'italian': 'Italian',
                'ristorante': 'Italian',
                'trattoria': 'Italian', 
                'osteria': 'Italian',
                'pasta': 'Italian',
                'french': 'French',
                'bistro': 'French',
                'brasserie': 'French',
                'mediterranean': 'Mediterranean',
                'greek': 'Mediterranean',
                'korean': 'Korean',
                'bbq': 'BBQ',
                'barbecue': 'BBQ',
                'steakhouse': 'Steakhouse',
                'chophouse': 'Steakhouse',
                'seafood': 'Seafood',
                'oyster': 'Seafood',
                'fish': 'Seafood',
                'crab': 'Seafood',
                'lobster': 'Seafood',
                'burger': 'American',
                'diner': 'American',
                'grill': 'American',
                'kitchen': 'American',
                'bakery': 'Bakery',
                'cafe': 'Cafe',
                'coffee': 'Cafe',
                'tavern': 'Bar & Grill',
                'pub': 'Bar & Grill',
                'lounge': 'Bar & Grill',
                'gastropub': 'Bar & Grill'
            }
            
            for keyword, cuisine in name_keywords.items():
                if keyword in name_lower:
                    cuisines.append(cuisine)
                    break
        
        # Look for more specific restaurant types in Google types
        if not cuisines:
            specific_types = {
                'lodging': 'Hotel Restaurant',
                'spa': 'Spa Restaurant', 
                'tourist_attraction': 'Tourist Restaurant'
            }
            
            for gtype in google_types:
                if gtype in specific_types:
                    cuisines.append(specific_types[gtype])
                    break
        
        # Default fallback based on other types
        if not cuisines:
            if 'cafe' in google_types:
                cuisines.append('Cafe')
            elif 'bakery' in google_types:
                cuisines.append('Bakery')
            elif 'bar' in google_types and 'restaurant' in google_types:
                cuisines.append('Bar & Grill')  # Restaurant with bar
            elif 'bar' in google_types:
                cuisines.append('Bar')  # Primarily a bar
            elif 'restaurant' in google_types or 'food' in google_types or 'establishment' in google_types:
                cuisines.append('American')  # Better default than "Restaurant"
        
        return cuisines if cuisines else ['Dining']
    
    def _extract_vibes_from_types(self, google_types: List[str]) -> List[str]:
        """Extract vibes from Google Places types with enhanced mapping"""
        vibe_mapping = {
            'bar': 'Bar',
            'night_club': 'Nightlife',
            'cafe': 'Casual',
            'bakery': 'Counter-Service/To-Go',
            'fast_food_restaurant': 'Counter-Service/To-Go',
            'meal_takeaway': 'Counter-Service/To-Go',
            'meal_delivery': 'Counter-Service/To-Go',
            'lodging': 'Hotel',
            'spa': 'Upscale',
            'tourist_attraction': 'Tourist',
            'establishment': 'Casual'  # Most establishments are casual
        }
        
        # Enhanced vibe inference based on combinations of types
        vibes = set()
        has_restaurant = 'restaurant' in google_types
        has_food = 'food' in google_types
        has_establishment = 'establishment' in google_types
        
        # Extract direct vibe mappings
        for gtype in google_types:
            if gtype in vibe_mapping:
                vibes.add(vibe_mapping[gtype])
        
        # Infer additional vibes based on type combinations
        if has_restaurant or has_food or has_establishment:
            # If it's a restaurant/food place without specific vibes, it's likely casual
            if not vibes or 'Casual' in vibes:
                vibes.add('Casual')
            
            # Add "Casual" to restaurants that might also be bars (they can be both)
            if 'Bar' in vibes:
                vibes.add('Casual')  # Bar restaurants are often casual too
        
        # Convert back to list and ensure we always have at least one vibe
        vibes_list = list(vibes)
        if not vibes_list:
            vibes_list = ['Casual']
        
        return vibes_list

    def get_api_usage_stats(self) -> Dict:
        """Get API usage statistics"""
        return {
            'total_requests': self.request_count,
            'requests_today': self.request_count,  # Would need date tracking for actual daily count
            'last_request_time': self.last_request_time
        }