# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is "Picky" - a restaurant recommendation system that analyzes user dining preferences from CSV data and provides personalized restaurant recommendations based on location, cuisine preferences, and past dining patterns.

## Architecture

The system follows a modular architecture with clear separation of concerns:

- **models.py**: Core data models (Restaurant, UserProfile, Recommendation)
- **database.py**: SQLite database management and operations
- **data_processor.py**: CSV import and data cleaning functionality
- **google_places.py**: Google Places API integration for location enrichment
- **preference_analyzer.py**: User preference analysis and pattern recognition
- **recommendation_engine.py**: Core recommendation algorithms and similarity matching
- **main_system.py**: Main system orchestrator that coordinates all components
- **api.py**: API wrapper providing simple interface to the system
- **example_usage.py**: Comprehensive usage examples and testing scenarios

## Key Components

### Data Flow
1. CSV data import → Data cleaning → Database storage
2. Optional Google Places enrichment for location/rating data
3. User preference analysis based on rating patterns
4. Recommendation generation using similarity algorithms and user preferences

### Core Models
- **Restaurant**: Stores name, cuisine types, location, vibes, ratings, notes
- **UserProfile**: Tracks cuisine/price/vibe preferences, rating patterns, location history
- **Recommendation**: Contains restaurant + score + reasoning + distance

### Database Schema
Uses SQLite with JSON storage for complex fields (location, preferences). Database operations are centralized in DatabaseManager class.

## Development Commands

### Setup
```bash
pip install -r requirements.txt
```

### Google Places API Setup
```bash
python setup_google_api.py
```
Or set environment variable:
```bash
export GOOGLE_PLACES_API_KEY="your_api_key_here"
```

### Running Examples
```bash
python example_usage.py
```

### Core Dependencies
- pandas, numpy: Data processing
- scikit-learn: Machine learning similarity calculations  
- geopy: Geographic distance calculations
- fuzzywuzzy: Restaurant name matching
- requests: Google Places API integration

## Usage Patterns

### CSV Import Format
Expected CSV columns: restaurant name, cuisine, location data, user ratings, vibes, notes. See data_processor.py for validation logic.

### API Initialization
```python
from api import RestaurantRecommendationAPI
api = RestaurantRecommendationAPI(db_path="restaurants.db", google_api_key="optional")
```

### Main Operations
- `upload_csv()`: Import restaurant data from CSV
- `get_recommendations()`: Location-based recommendations  
- `get_city_recommendations()`: City-specific recommendations
- `get_user_analysis()`: Analyze user dining patterns
- `find_similar_restaurants()`: Find restaurants similar to a given one


## Integration Points

- Google Places API for location enrichment (optional)
- SQLite database for persistent storage
- Geospatial calculations using geodesic distance
- Machine learning similarity matching using sklearn

## Google Places API Integration

The system automatically detects and uses Google Places API keys from:
1. `GOOGLE_PLACES_API_KEY` environment variable  
2. `.env` file in project root
3. Manual configuration via `config.set_google_api_key()`

When enabled, provides:
- Enhanced location data and coordinates
- Google ratings and review summaries  
- Improved restaurant name matching
- Additional restaurant features (phone, website, hours)

Use `python setup_google_api.py` for interactive setup.

## Important Notes

- No existing test files - manual testing through example_usage.py
- Google API key is optional but strongly recommended for full functionality
- System supports multiple users through user_id parameter
- Recommendation scores combine similarity, distance, and user preference factors
- API keys are automatically loaded from environment or .env file