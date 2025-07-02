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
            limit=args.limit,
            include_live_search=True  # Enable live search by default
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
            limit=args.limit,
            include_live_search=True,  # Enable live search by default
            use_learning=args.use_learning
        )
    
    else:
        print("❌ Error: Must specify either --lat/--lng or --city")
        sys.exit(1)
    
    # Display results
    if recommendations and recommendations["success"]:
        recs = recommendations['recommendations']
        if recs:
            # Show learning status
            if recommendations.get('learning_applied'):
                print(f"\n🧠 Applied learning from previous session: {recommendations.get('session_id', '')[:8]}...")
            
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

def interactive_recommendations(args):
    """Interactive recommendation session with feedback"""
    api = RestaurantRecommendationAPI(db_path=args.database)
    
    print("🎯 Starting Interactive Recommendation Session")
    print("=" * 50)
    print(f"👤 User: {args.user_id}")
    
    # Start session
    if args.city:
        print(f"🏙️  Location: {args.city}")
        if args.state:
            print(f"🗺️  State: {args.state}")
        
        session_result = api.start_interactive_session(
            user_id=args.user_id,
            city=args.city,
            state=args.state
        )
    elif args.latitude and args.longitude:
        print(f"📍 Location: {args.latitude}, {args.longitude}")
        
        session_result = api.start_interactive_session(
            user_id=args.user_id,
            latitude=args.latitude,
            longitude=args.longitude
        )
    else:
        print("❌ Error: Must specify either --city or --lat/--lng")
        sys.exit(1)
    
    if not session_result["success"]:
        print(f"❌ Error starting session: {session_result.get('error')}")
        sys.exit(1)
    
    session_id = session_result["session_id"]
    print(f"✅ Session started: {session_id[:8]}...")
    
    round_num = 1
    
    while True:
        print(f"\n🔄 Round {round_num} - Getting recommendations...")
        print("-" * 40)
        
        # Get recommendations
        recommendations = api.get_session_recommendations(session_id, limit=args.limit)
        
        if not recommendations["success"]:
            print(f"❌ Error: {recommendations.get('error')}")
            break
        
        if recommendations["count"] == 0:
            print("😞 No more recommendations found.")
            print("All restaurants in this area have been shown or filtered out.")
            break
        
        # Display recommendations
        recs = recommendations['recommendations']
        print(f"🎯 Found {len(recs)} recommendations:")
        print("=" * 60)
        
        for i, rec in enumerate(recs, 1):
            restaurant = rec['restaurant']
            score = rec['recommendation_score']
            reasoning = rec['reasoning']
            
            print(f"\n{i}. 🍽️  {restaurant['name']}")
            print(f"   📍 {restaurant['location'].get('city', 'Unknown')}")
            print(f"   🍜 {', '.join(restaurant['cuisine_type'])}")
            
            if restaurant.get('rating'):
                print(f"   ⭐ Rating: {restaurant['rating']}/5")
            else:
                print(f"   ⭐ Rating: Not rated")
            
            match_percentage = score * 100
            print(f"   🎯 Match: {match_percentage:.0f}%")
            print(f"   💭 Why: {reasoning}")
            
            if rec.get('distance_km'):
                print(f"   📏 Distance: {rec['distance_km']:.1f} km")
            
            if restaurant.get('price_level'):
                price_symbols = '$' * restaurant['price_level']
                print(f"   💰 Price: {price_symbols}")
        
        # Get user feedback
        print(f"\n💬 Feedback (Round {round_num})")
        print("-" * 30)
        
        try:
            liked_input = input("👍 Enter liked restaurants (numbers, comma-separated): ").strip()
            disliked_input = input("👎 Enter disliked restaurants (numbers, comma-separated): ").strip()
            
            # Parse liked/disliked restaurant IDs
            liked_ids = []
            disliked_ids = []
            
            if liked_input:
                for num_str in liked_input.split(','):
                    try:
                        idx = int(num_str.strip()) - 1
                        if 0 <= idx < len(recs):
                            liked_ids.append(recs[idx]['restaurant']['id'])
                    except ValueError:
                        print(f"⚠️  Ignoring invalid input: {num_str}")
            
            if disliked_input:
                for num_str in disliked_input.split(','):
                    try:
                        idx = int(num_str.strip()) - 1
                        if 0 <= idx < len(recs):
                            disliked_ids.append(recs[idx]['restaurant']['id'])
                    except ValueError:
                        print(f"⚠️  Ignoring invalid input: {num_str}")
            
            # Get preference refinements
            cuisine_prefs = None
            vibe_prefs = None
            
            if round_num == 1 or input("\n🎛️  Want to specify cuisine preferences? (y/n): ").lower().startswith('y'):
                cuisine_input = input("🍜 Enter preferred cuisines (comma-separated): ").strip()
                if cuisine_input:
                    cuisine_prefs = [c.strip() for c in cuisine_input.split(',')]
            
            if round_num == 1 or input("🎭 Want to specify vibe preferences? (y/n): ").lower().startswith('y'):
                vibe_input = input("✨ Enter preferred vibes (comma-separated): ").strip()
                if vibe_input:
                    vibe_prefs = [v.strip() for v in vibe_input.split(',')]
            
            # Provide feedback
            feedback_result = api.provide_session_feedback(
                session_id=session_id,
                liked_restaurant_ids=liked_ids,
                disliked_restaurant_ids=disliked_ids,
                cuisine_preferences=cuisine_prefs,
                vibe_preferences=vibe_prefs
            )
            
            if feedback_result["success"]:
                print(f"✅ {feedback_result['message']}")
                if cuisine_prefs:
                    print(f"🍜 Cuisine preferences: {', '.join(cuisine_prefs)}")
                if vibe_prefs:
                    print(f"✨ Vibe preferences: {', '.join(vibe_prefs)}")
            else:
                print(f"❌ Error collecting feedback: {feedback_result.get('error')}")
            
            # Ask if user wants to continue
            continue_input = input("\n🔄 Get more recommendations? (y/n): ").strip().lower()
            if not continue_input.startswith('y'):
                print("👋 Thanks for using interactive recommendations!")
                break
                
            round_num += 1
            
        except KeyboardInterrupt:
            print("\n\n👋 Session ended by user.")
            break
        except EOFError:
            print("\n\n👋 Session ended.")
            break

def add_restaurant(args):
    """Add individual restaurant to database"""
    api = RestaurantRecommendationAPI(db_path=args.database)
    
    # Validate arguments - either interactive mode OR name/city required
    if not args.interactive and (not args.name or not args.city):
        print("❌ Error: Either use --interactive mode OR provide both --name and --city")
        print("Examples:")
        print("  python picky.py add --interactive --user mzhuang")
        print("  python picky.py add --name 'Restaurant Name' --city 'City' --user mzhuang")
        return
    
    if args.interactive:
        # Interactive mode for adding multiple restaurants
        print("🍽️  Interactive Restaurant Addition")
        print("=" * 40)
        print(f"👤 User: {args.user_id}")
        
        while True:
            try:
                print("\n➕ Add New Restaurant")
                print("-" * 20)
                
                name = input("Restaurant name: ").strip()
                if not name:
                    print("❌ Restaurant name is required")
                    continue
                
                city = input("City: ").strip()
                if not city:
                    print("❌ City is required")
                    continue
                
                state = input("State (optional): ").strip() or None
                notes = input("Notes (optional): ").strip() or None
                
                wishlist_input = input("Mark as wishlist item? (y/n): ").strip().lower()
                is_wishlist = wishlist_input.startswith('y')
                
                # Add the restaurant
                result = add_single_restaurant(api, name, city, state, args.user_id, notes, is_wishlist, auto_confirm=False)
                
                if result:
                    continue_input = input("\n➕ Add another restaurant? (y/n): ").strip().lower()
                    if not continue_input.startswith('y'):
                        print("👋 Finished adding restaurants!")
                        break
                else:
                    retry_input = input("\n🔄 Try again? (y/n): ").strip().lower()
                    if not retry_input.startswith('y'):
                        break
                        
            except KeyboardInterrupt:
                print("\n\n👋 Addition stopped by user.")
                break
            except EOFError:
                print("\n\n👋 Addition finished.")
                break
    
    else:
        # Single restaurant addition
        print("🍽️  Add Restaurant to Database")
        print("=" * 30)
        print(f"👤 User: {args.user_id}")
        print(f"🏷️  Restaurant: {args.name}")
        print(f"📍 Location: {args.city}" + (f", {args.state}" if args.state else ""))
        
        if args.notes:
            print(f"📝 Notes: {args.notes}")
        if args.wishlist:
            print("⭐ Marked as wishlist item")
        
        add_single_restaurant(api, args.name, args.city, args.state, args.user_id, args.notes, args.wishlist, args.auto_confirm)

def add_single_restaurant(api, name: str, city: str, state: str, user_id: str, notes: str, is_wishlist: bool, auto_confirm: bool = False) -> bool:
    """Add a single restaurant and return success status"""
    
    print(f"\n🔍 Searching for '{name}' in {city}" + (f", {state}" if state else "") + "...")
    
    # Search for the restaurant using Google Places
    result = api.add_restaurant_by_name(
        name=name,
        city=city,
        state=state,
        user_id=user_id,
        notes=notes,
        is_wishlist=is_wishlist
    )
    
    if result["success"]:
        if result.get("duplicate"):
            print("⚠️  Restaurant already exists in database:")
            existing = result["existing_restaurant"]
            print(f"   🍽️  {existing['name']}")
            print(f"   📍 {existing.get('address', 'No address')}")
            
            if auto_confirm:
                print("\n🔄 Auto-updating existing restaurant...")
                update_existing = True
            else:
                update_input = input("\n🔄 Update existing restaurant? (y/n): ").strip().lower()
                update_existing = update_input.startswith('y')
            
            if update_existing:
                update_result = api.update_restaurant_notes(existing['id'], notes, is_wishlist)
                if update_result["success"]:
                    print("✅ Restaurant updated successfully!")
                else:
                    print(f"❌ Error updating restaurant: {update_result.get('error')}")
            return True
        
        else:
            restaurant = result["restaurant"]
            print("✅ Found match:")
            print(f"   🍽️  {restaurant['name']}")
            print(f"   📍 {restaurant.get('address', 'No address')}")
            if restaurant.get('google_rating'):
                print(f"   ⭐ Google Rating: {restaurant['google_rating']}/5")
            if restaurant.get('cuisine_type'):
                print(f"   🍜 Cuisine: {', '.join(restaurant['cuisine_type'])}")
            if restaurant.get('price_level'):
                price_symbols = '$' * restaurant['price_level']
                print(f"   💰 Price: {price_symbols}")
            
            if auto_confirm:
                print("\n✅ Auto-confirming restaurant addition...")
                confirm_add = True
            else:
                confirm_input = input("\n✅ Add this restaurant? (y/n): ").strip().lower()
                confirm_add = confirm_input.startswith('y')
            
            if confirm_add:
                add_result = api.confirm_restaurant_addition(result["temp_id"])
                if add_result["success"]:
                    print("🎉 Restaurant added successfully!")
                    if is_wishlist:
                        print("⭐ Marked as wishlist item")
                    return True
                else:
                    print(f"❌ Error adding restaurant: {add_result.get('error')}")
                    return False
            else:
                print("❌ Restaurant not added.")
                return False
    
    else:
        print(f"❌ Error: {result.get('error', 'Could not find restaurant')}")
        return False

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
        
        # Interactive recommendations with feedback
        python picky.py interactive --user john --city "Seattle" --state WA
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
    recommend_parser.add_argument('--use-learning', action='store_true',
                                 help='Apply learning from previous interactive sessions')
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze user dining patterns')
    analyze_parser.add_argument('--user', '--user-id', dest='user_id', required=True,
                               help='User ID to analyze')
    
    # Interactive command
    interactive_parser = subparsers.add_parser('interactive', help='Interactive recommendations with feedback')
    interactive_parser.add_argument('--user', '--user-id', dest='user_id', required=True,
                                   help='User ID to get recommendations for')
    interactive_parser.add_argument('--lat', '--latitude', dest='latitude', type=float,
                                   help='Latitude for location-based search')
    interactive_parser.add_argument('--lng', '--longitude', dest='longitude', type=float,
                                   help='Longitude for location-based search')
    interactive_parser.add_argument('--city', help='City name for city-based search')
    interactive_parser.add_argument('--state', help='State/province (optional with --city)')
    interactive_parser.add_argument('--limit', type=int, default=5,
                                   help='Maximum number of recommendations per round (default: 5)')
    
    # Add restaurant command
    add_parser = subparsers.add_parser('add', help='Add individual restaurant to database')
    add_parser.add_argument('--name', help='Restaurant name (required for single restaurant mode)')
    add_parser.add_argument('--city', help='City name (required for single restaurant mode)')
    add_parser.add_argument('--state', help='State/province (optional)')
    add_parser.add_argument('--user', '--user-id', dest='user_id', required=True,
                           help='User ID')
    add_parser.add_argument('--notes', help='Personal notes about the restaurant')
    add_parser.add_argument('--wishlist', action='store_true',
                           help='Mark as wishlist item (restaurant you want to try)')
    add_parser.add_argument('--interactive', action='store_true',
                           help='Interactive mode for adding multiple restaurants')
    add_parser.add_argument('--auto-confirm', action='store_true',
                           help='Auto-confirm restaurant addition (non-interactive mode)')
    
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
    elif args.command == 'interactive':
        interactive_recommendations(args)
    elif args.command == 'add':
        add_restaurant(args)
    elif args.command == 'analyze':
        analyze_user(args)
    elif args.command == 'status':
        system_status(args)
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()