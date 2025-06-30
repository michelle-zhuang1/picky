"""
example_usage.py
Usage examples and testing for the Restaurant Recommendation System
"""

import logging
import os
from api import RestaurantRecommendationAPI, quick_import_and_analyze, get_recommendations_for_trip
from config import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def example_complete_workflow():
    """Example of complete workflow from CSV import to recommendations"""
    
    print("="*60)
    print("RESTAURANT RECOMMENDATION SYSTEM - COMPLETE WORKFLOW")
    print("="*60)
    
    # Initialize the API with automatic Google API key detection
    api = RestaurantRecommendationAPI(db_path="example_restaurants.db")
    
    # Check if Google API integration is available
    if config.has_google_api_key():
        print("✓ Google Places API integration is enabled")
        print("  - Restaurant locations will be enriched with Google data")
        print("  - Ratings and reviews will be enhanced")
        print("  - More accurate location matching")
    else:
        print("⚠ Google Places API integration is disabled")
        print("  - Set GOOGLE_PLACES_API_KEY environment variable to enable")
        print("  - Limited location enrichment available")
    
    user_id = "example_user"
    csv_path = "sample_restaurants.csv"  # Replace with your CSV file path
    
    print(f"\n1. IMPORTING RESTAURANT DATA")
    print("-" * 40)
    
    # Import restaurant data (enable Google enrichment if API key is available)
    import_result = api.upload_csv(csv_path, user_id, enrich_with_google=config.has_google_api_key())
    print(f"Import Status: {'✓ Success' if import_result['success'] else '✗ Failed'}")
    
    if import_result["success"]:
        print(f"Imported: {import_result['imported_count']} restaurants")
        print(f"Validation: {import_result['validation']['non_empty_restaurants']} valid entries")
    else:
        print(f"Error: {import_result.get('error', 'Unknown error')}")
        return
    
    print(f"\n2. USER PATTERN ANALYSIS")
    print("-" * 40)
    
    # Analyze user patterns
    analysis = api.get_user_analysis(user_id)
    if analysis["success"]:
        print(f"Total restaurants rated: {analysis['total_restaurants']}")
        print(f"Average rating: {analysis['average_rating']:.1f}")
        print(f"Dining personality: {analysis['personality']}")
        print(f"Price comfort zone: {analysis['price_comfort_zone']}")
        print(f"Top cuisines: {[c['name'] for c in analysis['top_cuisines'][:3]]}")
        print(f"Favorite cities: {analysis['favorite_cities'][:3]}")
    
    print(f"\n3. LOCATION-BASED RECOMMENDATIONS")
    print("-" * 40)
    
    # Get recommendations for Philadelphia (example coordinates)
    philadelphia_lat, philadelphia_lng = 39.9526, -75.1652
    
    location_recs = api.get_recommendations(
        user_id=user_id,
        latitude=philadelphia_lat,
        longitude=philadelphia_lng,
        radius_km=25,
        limit=5
    )
    
    if location_recs["success"]:
        print(f"Found {location_recs['count']} recommendations near Philadelphia:")
        for i, rec in enumerate(location_recs['recommendations'][:3], 1):
            restaurant = rec['restaurant']
            print(f"  {i}. {restaurant['name']}")
            print(f"     Cuisine: {', '.join(restaurant['cuisine_type'])}")
            print(f"     Score: {rec['recommendation_score']:.2f}")
            print(f"     Reason: {rec['reasoning']}")
            if rec['distance_km']:
                print(f"     Distance: {rec['distance_km']:.1f} km")
    
    print(f"\n4. CITY-SPECIFIC RECOMMENDATIONS")
    print("-" * 40)
    
    # Get recommendations for a specific city
    city_recs = api.get_city_recommendations(user_id, "Atlanta", "GA", limit=3)
    
    if city_recs["success"]:
        print(f"Found {city_recs['count']} recommendations in Atlanta, GA:")
        for i, rec in enumerate(city_recs['recommendations'], 1):
            restaurant = rec['restaurant']
            print(f"  {i}. {restaurant['name']}")
            print(f"     Cuisine: {', '.join(restaurant['cuisine_type'])}")
            print(f"     Score: {rec['recommendation_score']:.2f}")
    else:
        print("No recommendations found for Atlanta, GA")
    
    print(f"\n5. WISHLIST RECOMMENDATIONS")
    print("-" * 40)
    
    # Get wishlist recommendations
    wishlist_recs = api.get_wishlist_recommendations(user_id)
    
    if wishlist_recs["success"] and wishlist_recs['count'] > 0:
        print(f"Found {wishlist_recs['count']} restaurants from your wishlist:")
        for i, rec in enumerate(wishlist_recs['recommendations'][:3], 1):
            restaurant = rec['restaurant']
            print(f"  {i}. {restaurant['name']}")
            print(f"     Location: {restaurant['location'].get('city')}")
            print(f"     Cuisine: {', '.join(restaurant['cuisine_type'])}")
    else:
        print("No wishlist recommendations found")
    
    print(f"\n6. FINDING SIMILAR RESTAURANTS")
    print("-" * 40)
    
    # Find similar restaurants to a highly-rated one
    if analysis["success"] and analysis['highly_rated_restaurants']:
        target_restaurant = analysis['highly_rated_restaurants'][0]
        similar_recs = api.find_similar_restaurants(
            restaurant_name=target_restaurant['name'],
            city=target_restaurant['city'],
            user_id=user_id,
            limit=3
        )
        
        if similar_recs["success"]:
            print(f"Restaurants similar to {target_restaurant['name']}:")
            for i, restaurant in enumerate(similar_recs['similar_restaurants'], 1):
                print(f"  {i}. {restaurant['name']}")
                print(f"     Location: {restaurant['location'].get('city')}")
                print(f"     Cuisine: {', '.join(restaurant['cuisine'])}")
    
    print(f"\n7. SYSTEM STATISTICS")
    print("-" * 40)
    
    # Get system stats
    stats = api.get_system_stats()
    if stats["success"]:
        s = stats['stats']
        print(f"Total restaurants in system: {s['total_restaurants']}")
        print(f"Restaurants you've rated: {s['rated_restaurants']}")
        print(f"Unrated restaurants: {s['unrated_restaurants']}")
        print(f"Cities covered: {s['cities_covered']}")
        print(f"Cuisines covered: {s['cuisines_covered']}")
    
    print(f"\n{'='*60}")
    print("WORKFLOW COMPLETED SUCCESSFULLY!")
    print("="*60)


def example_quick_functions():
    """Example using convenience functions"""
    
    print("\n" + "="*50)
    print("QUICK FUNCTION EXAMPLES")
    print("="*50)
    
    csv_path = "sample_restaurants.csv"
    user_id = "quick_user"
    
    print("\n1. Quick Import and Analysis")
    print("-" * 30)
    
    # Quick import and analysis
    result = quick_import_and_analyze(csv_path, user_id)
    
    if result.get("import_result", {}).get("success"):
        import_data = result["import_result"]
        analysis_data = result.get("analysis_result", {})
        
        print(f"✓ Imported {import_data['imported_count']} restaurants")
        
        if analysis_data.get("success"):
            print(f"✓ Analysis complete: {analysis_data['personality']}")
            print(f"  Top cuisine: {analysis_data['top_cuisines'][0]['name'] if analysis_data['top_cuisines'] else 'None'}")
    
    print("\n2. Trip Planning")
    print("-" * 30)
    
    # Get recommendations for a trip
    trip_recs = get_recommendations_for_trip(
        csv_path=csv_path,
        city="New York",
        state="NY",
        user_id=user_id,
        limit=5
    )
    
    if trip_recs.get("success"):
        print(f"✓ Found {trip_recs['count']} recommendations for New York:")
        for rec in trip_recs['recommendations'][:3]:
            restaurant = rec['restaurant']
            print(f"  • {restaurant['name']} ({', '.join(restaurant['cuisine_type'])})")


def example_api_usage_scenarios():
    """Example API usage for different scenarios"""
    
    print("\n" + "="*50)
    print("API USAGE SCENARIOS")
    print("="*50)
    
    api = RestaurantRecommendationAPI()
    user_id = "scenario_user"
    
    print("\nScenario 1: Business Trip to Chicago")
    print("-" * 40)
    
    # Business traveler needs dinner recommendations
    chicago_lat, chicago_lng = 41.8781, -87.6298
    
    business_recs = api.get_recommendations(
        user_id=user_id,
        latitude=chicago_lat,
        longitude=chicago_lng,
        radius_km=15,
        limit=3
    )
    
    if business_recs["success"]:
        print("Recommended for business dinner:")
        for rec in business_recs['recommendations']:
            restaurant = rec['restaurant']
            if 'Fine Dining' in restaurant.get('vibes', []) or restaurant.get('price_level', 0) >= 3:
                print(f"  • {restaurant['name']} - {rec['reasoning']}")
                break
    
    print("\nScenario 2: Weekend Food Adventure")
    print("-" * 40)
    
    # Food enthusiast looking for highly-rated spots
    foodie_recs = api.get_recommendations(
        user_id=user_id,
        latitude=chicago_lat,
        longitude=chicago_lng,
        radius_km=25,
        limit=5,
        exclude_visited=False  # Include all restaurants
    )
    
    if foodie_recs["success"]:
        print("Top-rated discoveries:")
        for rec in foodie_recs['recommendations'][:2]:
            restaurant = rec['restaurant']
            if restaurant.get('rating', 0) >= 4.0:
                print(f"  • {restaurant['name']} ({restaurant.get('rating', 'N/A')}/5) - {', '.join(restaurant['cuisine_type'])}")
    
    print("\nScenario 3: Checking Your Food Memory")
    print("-" * 40)
    
    # User wants to revisit analysis of their dining habits
    memory_analysis = api.get_user_analysis(user_id)
    
    if memory_analysis["success"]:
        patterns = memory_analysis
        print(f"Your dining personality: {patterns.get('personality', 'Unknown')}")
        print(f"You've explored {len(patterns.get('favorite_cities', []))} cities")
        print(f"Your rating style: {patterns.get('consistency', 'Unknown')} rater")


def example_csv_validation():
    """Example CSV validation before import"""
    
    print("\n" + "="*50)
    print("CSV VALIDATION EXAMPLE")
    print("="*50)
    
    api = RestaurantRecommendationAPI()
    csv_path = "sample_restaurants.csv"
    
    # Validate CSV format
    validation = api.validate_csv_format(csv_path)
    
    if validation["success"]:
        v = validation["validation"]
        print(f"✓ CSV validation successful")
        print(f"  Total rows: {v['total_rows']}")
        print(f"  Valid restaurants: {v['non_empty_restaurants']}")
        print(f"  Restaurants with ratings: {v['restaurants_with_ratings']}")
        print(f"  Available columns: {len(v['columns'])}")
        
        if v['missing_required_columns']:
            print(f"  ⚠ Missing required columns: {v['missing_required_columns']}")
        else:
            print(f"  ✓ All required columns present")
        
        print(f"  Optional columns found: {len(v['available_optional_columns'])}")
        
    else:
        print(f"✗ CSV validation failed: {validation.get('error')}")


def example_rating_updates():
    """Example of adding new ratings and seeing preference updates"""
    
    print("\n" + "="*50)
    print("RATING UPDATE EXAMPLE")
    print("="*50)
    
    api = RestaurantRecommendationAPI()
    user_id = "rating_user"
    
    # This would typically be called after trying a recommended restaurant
    print("Example: User tries a recommended restaurant and rates it")
    
    # In a real scenario, you'd get the restaurant_id from a recommendation
    # For this example, we'll show the structure
    
    example_rating = {
        "user_id": user_id,
        "restaurant_id": "example_restaurant_123",
        "rating": 4.5,
        "notes": "Great pasta, excellent service, will definitely return!"
    }
    
    print(f"User rated restaurant: {example_rating['rating']}/5")
    print(f"Notes: {example_rating['notes']}")
    print("→ This would update user preferences and improve future recommendations")


if __name__ == "__main__":
    """Run all examples"""
    
    try:
        # Run complete workflow example
        example_complete_workflow()
        
        # Run quick function examples
        example_quick_functions()
        
        # Run API scenario examples
        example_api_usage_scenarios()
        
        # Run CSV validation example
        example_csv_validation()
        
        # Run rating update example
        example_rating_updates()
        
        print(f"\n{'='*60}")
        print("ALL EXAMPLES COMPLETED!")
        print("="*60)
        print("\nNext steps:")
        print("1. Replace 'restaurant_data.csv' with your actual CSV file")
        print("2. Add your Google Places API key for location enrichment")
        print("3. Customize the recommendation parameters for your use case")
        print("4. Integrate with your preferred frontend or application")
        
    except FileNotFoundError:
        print("\n⚠ CSV file not found. Please ensure 'restaurant_data.csv' exists")
        print("Or modify the csv_path variable to point to your data file.")
        
    except Exception as e:
        print(f"\n✗ Error running examples: {e}")
        print("Check that all required dependencies are installed:")
        print("pip install pandas numpy scikit-learn geopy fuzzywuzzy requests")