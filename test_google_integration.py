#!/usr/bin/env python3
"""
test_google_integration.py
Test Google Places API integration
"""

import logging
from config import config
from api import RestaurantRecommendationAPI

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def test_google_integration():
    """Test Google Places API integration"""
    
    print("=" * 50)
    print("GOOGLE PLACES API INTEGRATION TEST")
    print("=" * 50)
    
    # Test configuration
    print("\n1. Configuration Test:")
    print("-" * 25)
    
    if config.has_google_api_key():
        key = config.get_google_api_key()
        print(f"✓ Google API key detected: {key[:8]}...{key[-4:] if len(key) > 12 else '***'}")
        print("✓ Google Places integration is ENABLED")
    else:
        print("✗ No Google API key found")
        print("⚠ Google Places integration is DISABLED")
        print("\nTo enable:")
        print("1. Run: python setup_google_api.py")
        print("2. Or set: export GOOGLE_PLACES_API_KEY='your_key'")
    
    # Test API initialization
    print("\n2. API Initialization Test:")
    print("-" * 30)
    
    try:
        api = RestaurantRecommendationAPI()
        print("✓ Restaurant Recommendation API initialized successfully")
        
        # Test Google service availability
        if hasattr(api.system, 'google_service') and api.system.google_service:
            print("✓ Google Places service is available")
            print("✓ Ready for location enrichment")
        else:
            print("⚠ Google Places service is not available")
            print("  Recommendations will work but without Google enrichment")
    
    except Exception as e:
        print(f"✗ Error initializing API: {e}")
    
    # Test system stats
    print("\n3. System Status:")
    print("-" * 20)
    
    try:
        stats = api.get_system_stats()
        if stats["success"]:
            s = stats["stats"]
            print(f"✓ System operational")
            print(f"  Total restaurants: {s['total_restaurants']}")
            print(f"  Google enriched: {s['google_enriched']}")
            
            if 'google_api_usage' in s:
                print(f"  API requests made: {s['google_api_usage']['total_requests']}")
        else:
            print("⚠ System status check failed")
    
    except Exception as e:
        print(f"✗ Error getting system stats: {e}")
    
    print("\n" + "=" * 50)
    print("INTEGRATION TEST COMPLETE")
    print("=" * 50)
    
    # Provide next steps based on results
    if config.has_google_api_key():
        print("\n✅ Google Places integration is ready!")
        print("Next steps:")
        print("1. Import your restaurant data: api.upload_csv('your_data.csv', 'user_id')")
        print("2. Get recommendations: api.get_recommendations('user_id', lat, lng)")
        print("3. Run full examples: python example_usage.py")
    else:
        print("\n⚠ Google Places integration is not configured")
        print("The system will work but with limited functionality.")
        print("To enable full features, set up your Google API key.")

if __name__ == "__main__":
    test_google_integration()