# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is "Picky" - a restaurant recommendation system that analyzes user dining preferences from CSV data and provides personalized restaurant recommendations based on location, cuisine preferences, and past dining patterns.

## Architecture

The system follows a modular architecture with clear separation of concerns:

- **picky.py**: Command line interface with multiple subcommands (import, recommend, interactive, add, analyze, status)
- **models.py**: Core data models (Restaurant, UserProfile, Recommendation, RecommendationSession)
- **database.py**: SQLite database management and operations
- **data_processor.py**: CSV import and data cleaning functionality
- **google_places.py**: Google Places API integration for location enrichment
- **preference_analyzer.py**: User preference analysis and pattern recognition
- **recommendation_engine.py**: Core recommendation algorithms, similarity matching, and session management
- **main_system.py**: Main system orchestrator that coordinates all components
- **api.py**: API wrapper providing simple interface to the system
- **example_usage.py**: Comprehensive usage examples and testing scenarios

## Key Components

### Data Flow
1. CSV data import → Data cleaning → Database storage
2. Manual restaurant addition via Google Places API → Database storage
3. Optional Google Places enrichment for location/rating data
4. User preference analysis based on rating patterns
5. Recommendation generation using similarity algorithms and user preferences
6. Interactive sessions with feedback collection and preference learning

### Core Models
- **Restaurant**: Stores name, cuisine types, location, vibes, ratings, notes
- **UserProfile**: Tracks cuisine/price/vibe preferences, rating patterns, location history
- **Recommendation**: Contains restaurant + score + reasoning + distance
- **RecommendationSession**: Tracks interactive sessions with user feedback and learning

### Database Schema
Uses SQLite with JSON storage for complex fields (location, preferences). Database operations are centralized in DatabaseManager class.

Database tables:
- `restaurants`: Core restaurant data with Google Places integration
- `user_profiles`: User preference profiles and patterns
- `user_restaurant_interactions`: User ratings and visit history
- `recommendation_sessions`: Interactive session tracking
- `session_feedback`: Detailed feedback for machine learning

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

### Command Line Interface
```bash
# Import CSV data
python picky.py import data.csv --user username

# Get recommendations  
python picky.py recommend --user username --city "Seattle" --state WA

# Interactive recommendations with feedback
python picky.py interactive --user username --city "Seattle" --state WA

# Add individual restaurants
python picky.py add --name "Restaurant" --city "City" --user username --wishlist

# Interactive restaurant addition
python picky.py add --interactive --user username

# Analyze user patterns
python picky.py analyze --user username

# System status
python picky.py status
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
- `add_restaurant_by_name()`: Add individual restaurants via Google Places search
- `start_interactive_session()`: Begin interactive recommendation session
- `provide_session_feedback()`: Collect user feedback for learning
- `get_session_recommendations()`: Get recommendations with applied learning


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

- No existing test files - manual testing through example_usage.py and picky.py CLI
- Google API key is optional but strongly recommended for full functionality
- System supports multiple users through user_id parameter
- Recommendation scores combine similarity, distance, and user preference factors
- API keys are automatically loaded from environment or .env file
- Interactive sessions provide real-time learning and preference refinement
- Restaurant addition supports both single and batch operations via CLI
- Duplicate detection prevents restaurant duplication in database
- Session feedback is stored for future machine learning improvements

## CLI Usage Patterns

### Apple Maps Integration Workflow
1. Export restaurant list from Apple Maps guides
2. Use `python picky.py add --interactive --user username` to add restaurants
3. Mark wishlist items for restaurants you haven't tried
4. Use `python picky.py interactive --user username --city "City"` for recommendations
5. Provide feedback to improve future recommendations

### Recommendation Workflow
1. Import historical dining data: `python picky.py import data.csv --user username`
2. Get basic recommendations: `python picky.py recommend --user username --city "City"`
3. Use interactive mode for refined recommendations: `python picky.py interactive --user username --city "City"`
4. Add new restaurants as you discover them: `python picky.py add --name "Restaurant" --city "City" --user username`

### Command Line Arguments

**Global arguments:**
- `--database`: Database file path (default: restaurant_recommendations.db)
- `--verbose`: Enable verbose logging

**Import command:**
- `csv_file`: Path to CSV file (required)
- `--user`: User ID (default: default)

**Recommend command:**
- `--user`: User ID (required)
- `--lat`/`--lng`: Coordinates for location-based search
- `--city`/`--state`: City-based search
- `--radius`: Search radius in km (default: 25)
- `--limit`: Max recommendations (default: 10)

**Interactive command:**
- `--user`: User ID (required)
- `--lat`/`--lng`: Coordinates for location-based search
- `--city`/`--state`: City-based search
- `--limit`: Max recommendations per round (default: 5)

**Add command:**
- `--name`: Restaurant name (required for single mode)
- `--city`: City name (required for single mode)
- `--state`: State/province (optional)
- `--user`: User ID (required)
- `--notes`: Personal notes (optional)
- `--wishlist`: Mark as wishlist item
- `--interactive`: Interactive mode for multiple restaurants
- `--auto-confirm`: Auto-confirm additions (non-interactive)