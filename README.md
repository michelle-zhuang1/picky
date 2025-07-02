# 🍽️ Picky - Personal Restaurant Recommendation System

**Picky** is an intelligent restaurant recommendation system that learns your dining preferences from your restaurant history and provides personalized recommendations based on location, cuisine preferences, and past dining patterns.

## ✨ What Picky Does

- **📊 Analyzes Your Dining History**: Import your restaurant data from CSV and discover your dining patterns
- **🎯 Personalized Recommendations**: Get restaurant suggestions tailored to your taste preferences
- **📍 Location-Based Search**: Find great restaurants near any location or in specific cities
- **🧠 Smart Learning**: The more data you provide, the better the recommendations become
- **🌟 Google Places Integration**: Enhanced with Google ratings, reviews, and location data
- **📈 Dining Analytics**: Understand your food preferences, price comfort zones, and dining personality
- **➕ Restaurant Management**: Add individual restaurants from Apple Maps guides or other sources
- **🔄 Interactive Sessions**: Get recommendations with real-time feedback and preference refinement

## 🚀 Quick Start

### 1. Installation

```bash
# Clone or download the repository
cd picky

# Install dependencies
pip install -r requirements.txt
```

### 2. Command Line Interface

**Picky includes a simple command line interface for easy use:**

```bash
# Check system status
python picky.py status

# Import your restaurant CSV
python picky.py import your_restaurants.csv --user your_name

# Get recommendations near a location
python picky.py recommend --user your_name --lat 40.7589 --lng -73.9851

# Get recommendations for a city
python picky.py recommend --user your_name --city "San Francisco" --state CA

# Interactive recommendations with feedback
python picky.py interactive --user your_name --city "Seattle" --state WA

# Add individual restaurants (from Apple Maps guides, etc.)
python picky.py add --name "Restaurant Name" --city "City" --user your_name --wishlist

# Add multiple restaurants interactively
python picky.py add --interactive --user your_name

# Analyze your dining patterns
python picky.py analyze --user your_name
```

### 3. Prepare Your Restaurant Data

Create a CSV file with your restaurant history. The system expects these columns:

**Required columns:**
- `restaurant_name` - Name of the restaurant
- `city` or `location` - City where restaurant is located

**Optional but recommended columns:**
- `cuisine` - Type of cuisine (e.g., "Italian", "Mexican")
- `rating` - Your rating (1-5 stars or ⭐⭐⭐⭐⭐ format)
- `vibes` - Restaurant atmosphere (e.g., "casual", "romantic", "family-friendly")
- `price_range` - Price level ($, $$, $$$, $$$$)
- `notes` - Your personal notes about the restaurant
- `revisit` - Would you go back? (Y/N)
- `neighborhood` - Specific area/neighborhood
- `state` - State/province

**Example CSV format:**
```csv
Restaurant,City,State,Cuisine Type,Rating,Vibes,Cost,Extra Notes:,Revisit ?
"Joe's Pizza","New York","NY","Italian",4,"casual","$$","Great thin crust","Y"
"Le Bernardin","New York","NY","French",5,"fine dining","$$$$","Amazing seafood","Y"
"Chipotle","Boston","MA","Mexican",3,"fast casual","$","Quick lunch option","N"
```

**Important:** Use the exact column names shown above for best results. The system expects `Restaurant` and `City` as minimum required columns.

### 4. Set Up Google Places API (Optional but Recommended)

For enhanced recommendations with Google ratings and location data:

```bash
# Interactive setup
python setup_google_api.py

# Or set environment variable
export GOOGLE_PLACES_API_KEY="your_api_key_here"

# Or create .env file
echo "GOOGLE_PLACES_API_KEY=your_api_key_here" > .env
```

**How to get a Google Places API key:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create or select a project
3. Enable the Places API
4. Create credentials (API Key)
5. Restrict the API key to Places API for security

### 5. Start Using Picky!

**Simple Command Line Usage:**

```bash
# 1. Import your restaurant data
python picky.py import my_restaurants.csv --user my_name

# 2. Get recommendations for a city (great for trip planning)
python picky.py recommend --user my_name --city "Portland" --state OR --limit 5

# 3. Get recommendations near a specific location
python picky.py recommend --user my_name --lat 45.5152 --lng -122.6784 --radius 15

# 4. Add restaurants from Apple Maps guides or other sources
python picky.py add --name "Canlis" --city "Seattle" --state "WA" --user my_name --wishlist --auto-confirm

# 5. Interactive recommendations with real-time feedback
python picky.py interactive --user my_name --city "Portland" --state OR

# 6. Analyze your dining preferences
python picky.py analyze --user my_name

# 7. Check system status anytime
python picky.py status
```

**Or use the Python API directly:**

```python
from api import RestaurantRecommendationAPI

# Initialize the system
api = RestaurantRecommendationAPI()

# Import your restaurant data
result = api.upload_csv("my_restaurants.csv", user_id="your_name")
print(f"Imported {result['imported_count']} restaurants!")

# Get recommendations near a location (latitude, longitude)
recommendations = api.get_recommendations(
    user_id="your_name",
    latitude=40.7589,  # Times Square, NYC
    longitude=-73.9851,
    radius_km=10,
    limit=5
)

# Show results
for rec in recommendations['recommendations']:
    restaurant = rec['restaurant']
    print(f"🍽️ {restaurant['name']}")
    print(f"   📍 {restaurant['location'].get('city')}")
    print(f"   🍜 {', '.join(restaurant['cuisine_type'])}")
    print(f"   ⭐ Score: {rec['recommendation_score']:.2f}")
    print(f"   💭 Why: {rec['reasoning']}")
    print()
```

## 📖 Usage Examples

### Get Recommendations for a Specific City

```python
# Perfect for trip planning
city_recs = api.get_city_recommendations(
    user_id="your_name",
    city="San Francisco",
    state="CA",
    limit=10
)
```

### Analyze Your Dining Patterns

```python
# Discover your food personality
analysis = api.get_user_analysis("your_name")

print(f"Your dining personality: {analysis['personality']}")
print(f"Favorite cuisines: {[c['name'] for c in analysis['top_cuisines'][:3]]}")
print(f"Price comfort zone: {analysis['price_comfort_zone']}")
```

### Find Similar Restaurants

```python
# Find restaurants similar to one you love
similar = api.find_similar_restaurants(
    restaurant_name="Joe's Pizza",
    city="New York",
    user_id="your_name",
    limit=5
)
```

### Get Your Wishlist Recommendations

```python
# Restaurants you marked as "want to visit"
wishlist = api.get_wishlist_recommendations("your_name")
```

### Add Individual Restaurants

```python
# Add restaurants from Apple Maps guides or other sources
result = api.add_restaurant_by_name(
    name="Canlis",
    city="Seattle", 
    state="WA",
    user_id="your_name",
    notes="Fine dining for special occasions",
    is_wishlist=True
)

# Confirm the addition
if result["success"] and not result.get("duplicate"):
    confirm_result = api.confirm_restaurant_addition(result["temp_id"])
    print(f"Added: {confirm_result['message']}")
```

### Interactive Recommendation Sessions

```python
# Start an interactive session
session = api.start_interactive_session(
    user_id="your_name",
    city="Seattle",
    state="WA"
)

# Get recommendations
recommendations = api.get_session_recommendations(session["session_id"])

# Provide feedback  
feedback = api.provide_session_feedback(
    session_id=session["session_id"],
    liked_restaurant_ids=["rest_1", "rest_3"],
    disliked_restaurant_ids=["rest_2"],
    cuisine_preferences=["Italian", "Japanese"],
    vibe_preferences=["romantic", "upscale"]
)

# Get refined recommendations
refined_recs = api.get_session_recommendations(session["session_id"])
```

## 🛠️ Advanced Usage

### Running the Complete Example

```bash
# See full workflow in action
python example_usage.py
```

### Testing Your Setup

```bash
# Verify everything is working
python test_google_integration.py
```

### Batch Processing Multiple Users

```python
# Import data for multiple users
users = ["alice", "bob", "charlie"]
for user in users:
    result = api.upload_csv(f"{user}_restaurants.csv", user_id=user)
    print(f"Imported {result['imported_count']} restaurants for {user}")
```

## 📊 Understanding Your Results

### Recommendation Scores
- **Score 0.8-1.0**: Perfect match for your preferences
- **Score 0.6-0.8**: Great option, very likely you'll enjoy
- **Score 0.4-0.6**: Good option worth trying
- **Score 0.2-0.4**: Decent option, might be worth exploring
- **Score 0.0-0.2**: Not well-matched to your preferences

### Dining Personalities
- **Adventurous Eater**: Loves trying new cuisines and experimental restaurants
- **Comfort Food Lover**: Prefers familiar, cozy dining experiences
- **Fine Dining Enthusiast**: Gravitates toward upscale, high-quality establishments
- **Casual Explorer**: Enjoys diverse options in relaxed settings
- **Consistent Rater**: Has well-defined preferences and rates predictably

## 💡 Tips for Better Recommendations

1. **Include Ratings**: Your personal ratings help the system learn your preferences
2. **Add Notes**: Detailed notes improve understanding of what you like/dislike
3. **Use Vibes**: Atmosphere preferences (casual, romantic, family-friendly) matter
4. **Mark Revisit Preferences**: Helps identify truly memorable places
5. **Include Price Information**: Helps match recommendations to your budget
6. **Geographic Diversity**: Include restaurants from different cities for better location matching
7. **Enable Google Places API**: This dramatically expands the restaurant database beyond just your visited places
8. **Add Wishlist Items**: Use `--wishlist` flag to mark restaurants you want to try
9. **Use Interactive Sessions**: Provide feedback to get progressively better recommendations
10. **Import Apple Maps Guides**: Use the `add` command to easily import restaurant lists from other sources

## 🔍 How Recommendations Work

**Important:** The system recommends restaurants you **haven't visited yet**. It learns from your dining history to suggest new places you'll likely enjoy. 

- **Without Google Places API**: Recommendations limited to restaurants in your CSV that others have rated
- **With Google Places API**: Access to millions of restaurants worldwide with enhanced matching
- **Best Results**: Combine your personal data with Google Places for personalized recommendations from a vast database

## 🔍 Troubleshooting

### CSV Import Issues
```bash
# Validate your CSV format first
python -c "
from api import RestaurantRecommendationAPI
api = RestaurantRecommendationAPI()
result = api.validate_csv_format('your_file.csv')
print(result)
"
```

### No Recommendations Found
- Ensure your CSV has location data (city/state)
- Try increasing the search radius
- Check that you have restaurants in the database: `api.get_system_stats()`

### Google API Issues
- Verify your API key is set: `echo $GOOGLE_PLACES_API_KEY`
- Check API quotas in Google Cloud Console
- Ensure Places API is enabled in your project

## 📁 Project Structure

```
picky/
├── README.md                    # This file
├── picky.py                    # Command line interface
├── api.py                      # Main API interface
├── main_system.py              # Core system orchestrator
├── models.py                   # Data models
├── database.py                 # Database operations
├── recommendation_engine.py    # ML recommendation algorithms
├── preference_analyzer.py      # User preference analysis
├── google_places.py           # Google Places integration
├── data_processor.py          # CSV import and data cleaning
├── config.py                  # Configuration management
├── example_usage.py           # Complete usage examples
├── setup_google_api.py        # Google API setup helper
├── test_google_integration.py # Integration testing
├── requirements.txt           # Python dependencies
├── .env.example              # Environment variables template
└── CLAUDE.md                 # Developer documentation
```

## 🤝 Contributing

Have ideas for improving Picky? We'd love to hear them! Feel free to:
- Submit feature requests
- Report bugs
- Contribute code improvements
- Share your restaurant recommendation use cases

## 📄 License

This project is open source. Feel free to use, modify, and distribute according to your needs.

---

**Ready to discover your next favorite restaurant? Import your CSV and let Picky guide your culinary adventures! 🍴✨**