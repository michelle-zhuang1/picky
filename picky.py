#!/usr/bin/env python3
"""
picky.py
Command line interface for the Picky Restaurant Recommendation System
"""

import argparse
import sys
import os
from pathlib import Path
import logging
from typing import Optional

from api import RestaurantRecommendationAPI
from config import config

def setup_logging(verbose: bool = False):
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(levelname)s: %(message)s'
    )

def check_csv_file(csv_path: str) -> bool:
    """Check if CSV file exists and is readable"""
    if not os.path.exists(csv_path):
        print(f"❌ Error: CSV file '{csv_path}' not found")
        return False
    
    if not csv_path.lower().endswith('.csv'):
        print(f"⚠️  Warning: File '{csv_path}' doesn't have .csv extension")
    
    return True

def import_restaurants(args):
    """Import restaurants from CSV file"""
    print("🍽️  Picky Restaurant Recommendation System")
    print("=" * 50)
    
    # Check CSV file
    if not check_csv_file(args.csv_file):
        sys.exit(1)
    
    # Initialize API
    api = RestaurantRecommendationAPI(db_path=args.database)
    
    # Check Google API status
    if config.has_google_api_key():
        print("✅ Google Places API integration enabled")
        enrich = True
    else:
        print("⚠️  Google Places API not configured (limited functionality)")
        print("   Run: python setup_google_api.py to enable full features")
        enrich = False
    
    print(f"\n📂 Importing restaurants from: {args.csv_file}")
    print(f"👤 User ID: {args.user_id}")
    
    # Import CSV
    result = api.upload_csv(args.csv_file, args.user_id, enrich_with_google=enrich)
    
    if result["success"]:
        print(f"\n✅ Import successful!")
        print(f"   📊 Imported: {result['imported_count']} restaurants")
        if 'enriched_count' in result:
            print(f"   🌟 Google enriched: {result['enriched_count']} restaurants")
        
        # Generate user analysis
        print(f"\n🧠 Analyzing your dining preferences...")
        analysis = api.get_user_analysis(args.user_id)
        
        if analysis["success"]:
            print(f"✅ Analysis complete!")
            print(f"   🍽️  Total restaurants: {analysis['total_restaurants']}")
            print(f"   ⭐ Average rating: {analysis.get('average_rating', 0):.1f}")
            print(f"   🎭 Dining personality: {analysis.get('personality', 'Unknown')}")
            print(f"   🏷️  Top cuisines: {[c['name'] for c in analysis.get('top_cuisines', [])[:3]]}")
            
            print(f"\n🎉 Ready to get recommendations!")
            print(f"   Use: python picky.py recommend --user {args.user_id} --city 'City Name'")
            print(f"   Or:  python picky.py recommend --user {args.user_id} --lat 40.7589 --lng -73.9851")
        
    else:
        print(f"❌ Import failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)

def get_recommendations(args):
    """Get restaurant recommendations"""
    api = RestaurantRecommendationAPI(db_path=args.database)
    
    print("🔍 Getting personalized recommendations...")
    print(f"👤 User: {args.user_id}")
    
    recommendations = None
    
    # Location-based recommendations
    if args.latitude and args.longitude:
        print(f"📍 Location: {args.latitude}, {args.longitude}")
        print(f"🔄 Radius: {args.radius} km")
        
        recommendations = api.get_recommendations(
            user_id=args.user_id,
            latitude=args.latitude,
            longitude=args.longitude,
            radius_km=args.radius,
            limit=args.limit
        )
    
    # City-based recommendations
    elif args.city:
        print(f"🏙️  City: {args.city}")
        if args.state:
            print(f"🗺️  State: {args.state}")
        
        recommendations = api.get_city_recommendations(
            user_id=args.user_id,
            city=args.city,
            state=args.state,
            limit=args.limit
        )
    
    else:
        print("❌ Error: Must specify either --lat/--lng or --city")
        sys.exit(1)
    
    # Display results
    if recommendations and recommendations["success"]:
        recs = recommendations['recommendations']
        if recs:
            print(f"\n🎯 Found {len(recs)} recommendations:")
            print("=" * 60)
            
            for i, rec in enumerate(recs, 1):
                restaurant = rec['restaurant']
                score = rec['recommendation_score']
                reasoning = rec['reasoning']
                
                print(f"\n{i}. 🍽️  {restaurant['name']}")
                print(f"   📍 {restaurant['location'].get('city', 'Unknown')}")
                print(f"   🍜 {', '.join(restaurant['cuisine_type'])}")
                
                # Show restaurant rating first (1-5 stars)
                if restaurant.get('rating'):
                    print(f"   ⭐ Rating: {restaurant['rating']}/5")
                else:
                    print(f"   ⭐ Rating: Not rated")
                
                # Show recommendation match score (0-100%)
                match_percentage = score * 100
                print(f"   🎯 Match: {match_percentage:.0f}%")
                print(f"   💭 Why: {reasoning}")
                
                if rec.get('distance_km'):
                    print(f"   📏 Distance: {rec['distance_km']:.1f} km")
                
                if restaurant.get('price_level'):
                    price_symbols = '$' * restaurant['price_level']
                    print(f"   💰 Price: {price_symbols}")
        else:
            print("😞 No recommendations found.")
            print("Try:")
            print("   • Increasing the search radius with --radius")
            print("   • Searching a different city")
            print("   • Adding more restaurants to your profile")
    
    else:
        error = recommendations.get('error', 'Unknown error') if recommendations else 'Unknown error'
        print(f"❌ Error getting recommendations: {error}")

def analyze_user(args):
    """Analyze user dining patterns"""
    api = RestaurantRecommendationAPI(db_path=args.database)
    
    print(f"🧠 Analyzing dining patterns for: {args.user_id}")
    
    analysis = api.get_user_analysis(args.user_id)
    
    if analysis["success"]:
        print("\n📊 Your Dining Profile:")
        print("=" * 40)
        
        print(f"🍽️  Total restaurants: {analysis['total_restaurants']}")
        print(f"⭐ Average rating: {analysis.get('average_rating', 0):.1f}")
        print(f"🎭 Dining personality: {analysis.get('personality', 'Unknown')}")
        print(f"💰 Price comfort zone: {analysis.get('price_comfort_zone', 'Unknown')}")
        
        # Top cuisines
        top_cuisines = analysis.get('top_cuisines', [])
        if top_cuisines:
            print(f"\n🏷️  Your favorite cuisines:")
            for i, cuisine in enumerate(top_cuisines[:5], 1):
                print(f"   {i}. {cuisine['name']} ({cuisine['percentage']:.0f}%)")
        
        # Favorite cities
        cities = analysis.get('favorite_cities', [])
        if cities:
            print(f"\n🏙️  Cities you've explored:")
            for city in cities[:5]:
                print(f"   • {city}")
        
        # Highly rated restaurants
        highly_rated = analysis.get('highly_rated_restaurants', [])
        if highly_rated:
            print(f"\n🌟 Your top-rated restaurants:")
            for restaurant in highly_rated[:3]:
                print(f"   • {restaurant['name']} ({restaurant['rating']}/5) - {restaurant['city']}")
    
    else:
        print(f"❌ Error analyzing user: {analysis.get('error', 'Unknown error')}")

def system_status(args):
    """Show system status and statistics"""
    api = RestaurantRecommendationAPI(db_path=args.database)
    
    print("🔧 Picky System Status")
    print("=" * 30)
    
    # Check Google API
    if config.has_google_api_key():
        print("✅ Google Places API: Enabled")
    else:
        print("⚠️  Google Places API: Disabled")
        print("   Run: python setup_google_api.py to enable")
    
    # Get system stats
    stats = api.get_system_stats()
    
    if stats["success"]:
        s = stats["stats"]
        print(f"\n📊 Database Statistics:")
        print(f"   🍽️  Total restaurants: {s['total_restaurants']}")
        print(f"   ⭐ Rated restaurants: {s['rated_restaurants']}")
        print(f"   📍 Google enriched: {s['google_enriched']}")
        print(f"   🏙️  Cities covered: {s['cities_covered']}")
        print(f"   🍜 Cuisines covered: {s['cuisines_covered']}")
        
        print(f"\n💾 Database file: {args.database}")
        
        if 'google_api_usage' in s:
            usage = s['google_api_usage']
            print(f"🌐 Google API requests: {usage['total_requests']}")
    
    else:
        print(f"❌ Error getting system stats: {stats.get('error')}")

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Picky - Personal Restaurant Recommendation System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Import restaurant data
  python picky.py import my_restaurants.csv --user john

  # Get recommendations near a location
  python picky.py recommend --user john --lat 40.7589 --lng -73.9851

  # Get recommendations for a city
  python picky.py recommend --user john --city "San Francisco" --state CA

  # Analyze your dining patterns
  python picky.py analyze --user john

  # Check system status
  python picky.py status
        """
    )
    
    parser.add_argument('--database', '-d', default='restaurant_recommendations.db',
                       help='Database file path (default: restaurant_recommendations.db)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Import command
    import_parser = subparsers.add_parser('import', help='Import restaurant data from CSV')
    import_parser.add_argument('csv_file', help='Path to CSV file containing restaurant data')
    import_parser.add_argument('--user', '--user-id', dest='user_id', default='default',
                              help='User ID (default: default)')
    
    # Recommend command
    recommend_parser = subparsers.add_parser('recommend', help='Get restaurant recommendations')
    recommend_parser.add_argument('--user', '--user-id', dest='user_id', required=True,
                                 help='User ID to get recommendations for')
    recommend_parser.add_argument('--lat', '--latitude', dest='latitude', type=float,
                                 help='Latitude for location-based search')
    recommend_parser.add_argument('--lng', '--longitude', dest='longitude', type=float,
                                 help='Longitude for location-based search')
    recommend_parser.add_argument('--city', help='City name for city-based search')
    recommend_parser.add_argument('--state', help='State/province (optional with --city)')
    recommend_parser.add_argument('--radius', type=float, default=25,
                                 help='Search radius in km (default: 25)')
    recommend_parser.add_argument('--limit', type=int, default=10,
                                 help='Maximum number of recommendations (default: 10)')
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze user dining patterns')
    analyze_parser.add_argument('--user', '--user-id', dest='user_id', required=True,
                               help='User ID to analyze')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show system status')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    
    # Handle commands
    if args.command == 'import':
        import_restaurants(args)
    elif args.command == 'recommend':
        get_recommendations(args)
    elif args.command == 'analyze':
        analyze_user(args)
    elif args.command == 'status':
        system_status(args)
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()