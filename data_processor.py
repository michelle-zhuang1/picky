"""
data_processor.py
Data processing and CSV import functionality
"""

import pandas as pd
import re
import hashlib
import logging
from typing import List, Optional, Tuple
from models import Restaurant
from database import DatabaseManager

logger = logging.getLogger(__name__)

class DataProcessor:
    """Handles data cleaning and standardization"""
    
    @staticmethod
    def clean_restaurant_name(name_input) -> str:
        """Clean and standardize restaurant name"""
        # Handle NaN, None, or empty values
        if name_input is None or (isinstance(name_input, float) and pd.isna(name_input)):
            return ""
        
        name = str(name_input).strip()
        if not name or name.lower() == 'nan':
            return ""
        
        # Remove common suffixes and clean
        name = re.sub(r'\s+(restaurant|cafe|bar|grill|kitchen|bistro|eatery)$', '', name, flags=re.IGNORECASE)
        name = re.sub(r'[^\w\s&\'-]', '', name)  # Remove special chars except &, ', -
        name = ' '.join(name.split())  # Normalize whitespace
        return name.strip()
    
    @staticmethod
    def parse_city_state(city_input) -> Tuple[str, str]:
        """Parse 'City, State' format into separate components"""
        # Handle NaN, None, or empty values
        if city_input is None or (isinstance(city_input, float) and pd.isna(city_input)):
            return "", ""
        
        city_str = str(city_input).strip()
        if not city_str or city_str.lower() == 'nan':
            return "", ""
        
        # Handle format like "Philadelphia, PA"
        if ',' in city_str:
            parts = city_str.split(',')
            city = parts[0].strip()
            state = parts[1].strip() if len(parts) > 1 else ""
            return city, state
        
        return city_str.strip(), ""
    
    @staticmethod
    def parse_star_rating(rating_input) -> Optional[float]:
        """Convert star emoji rating or numeric value to float"""
        if rating_input is None or rating_input == '-' or rating_input == '':
            return None
        
        # Handle numeric input directly
        if isinstance(rating_input, (int, float)):
            return float(rating_input)
        
        # Handle string input
        rating_str = str(rating_input).strip()
        if not rating_str or rating_str == '-':
            return None
        
        # Count star emojis
        star_count = rating_str.count('⭐') + rating_str.count('⭐️')
        if star_count > 0:
            return float(star_count)
        
        # Try to parse as numeric
        try:
            return float(rating_str)
        except ValueError:
            return None
    
    @staticmethod
    def parse_price_level(cost_input) -> Optional[int]:
        """Convert cost string to numeric price level"""
        # Handle NaN, None, or empty values
        if cost_input is None or (isinstance(cost_input, float) and pd.isna(cost_input)):
            return None
        
        cost_str = str(cost_input).strip()
        if not cost_str or cost_str == '-' or cost_str.lower() == 'nan':
            return None
        
        dollar_count = cost_str.count('$')
        if dollar_count > 0:
            return min(dollar_count, 4)  # Cap at 4
        
        # Handle other formats
        cost_map = {'cheap': 1, 'budget': 1, 'moderate': 2, 'expensive': 3, 'luxury': 4}
        cost_lower = cost_str.lower()
        for key, value in cost_map.items():
            if key in cost_lower:
                return value
        
        return None
    
    @staticmethod
    def parse_cuisine_types(cuisine_input) -> List[str]:
        """Parse cuisine type string into list"""
        # Handle NaN, None, or empty values
        if cuisine_input is None or (isinstance(cuisine_input, float) and pd.isna(cuisine_input)):
            return []
        
        cuisine_str = str(cuisine_input).strip()
        if not cuisine_str or cuisine_str.lower() == 'nan':
            return []
        
        # Split on common delimiters
        cuisines = re.split(r'[,;/&]', cuisine_str)
        return [c.strip() for c in cuisines if c.strip()]
    
    @staticmethod
    def parse_vibes(vibes_input) -> List[str]:
        """Parse vibes string into list"""
        # Handle NaN, None, or empty values
        if vibes_input is None or (isinstance(vibes_input, float) and pd.isna(vibes_input)):
            return []
        
        vibes_str = str(vibes_input).strip()
        if not vibes_str or vibes_str.lower() == 'nan':
            return []
        
        # Split on common delimiters
        vibes = re.split(r'[,;/]', vibes_str)
        return [v.strip() for v in vibes if v.strip()]
    
    @staticmethod
    def parse_menu_items(menu_input) -> List[str]:
        """Parse menu items string into list"""
        # Handle NaN, None, or empty values
        if menu_input is None or (isinstance(menu_input, float) and pd.isna(menu_input)):
            return []
        
        menu_str = str(menu_input).strip()
        if not menu_str or menu_str == '-' or menu_str.lower() == 'nan':
            return []
        
        # Split by common delimiters and clean
        items = re.split(r'[,;]', menu_str)
        menu_items = []
        for item in items:
            item = item.strip()
            if item and item != '-':
                # Clean up the item text
                item = re.sub(r'\s+', ' ', item)  # Normalize whitespace
                menu_items.append(item)
        
        return menu_items

class CSVImporter:
    """Handles importing restaurant data from CSV files"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.data_processor = DataProcessor()
    
    def import_from_csv(self, csv_path: str, user_id: str = "default") -> List[Restaurant]:
        """Import restaurants from CSV file"""
        try:
            # Read CSV with pandas
            df = pd.read_csv(csv_path)
            logger.info(f"Loaded {len(df)} rows from CSV")
            
            # Clean column names
            df.columns = df.columns.str.strip()
            
            restaurants = []
            
            for _, row in df.iterrows():
                try:
                    restaurant = self._row_to_restaurant(row, user_id)
                    if restaurant:
                        restaurants.append(restaurant)
                        self.db_manager.save_restaurant(restaurant)
                except Exception as e:
                    logger.warning(f"Failed to process row: {e}")
                    continue
            
            logger.info(f"Successfully imported {len(restaurants)} restaurants")
            return restaurants
            
        except Exception as e:
            logger.error(f"Failed to import CSV: {e}")
            return []
    
    def _row_to_restaurant(self, row: pd.Series, user_id: str) -> Optional[Restaurant]:
        """Convert CSV row to Restaurant object"""
        # Helper function to safely get string values from pandas row
        def safe_get(column_name, default=''):
            value = row.get(column_name, default)
            if pd.isna(value):
                return default
            return str(value).strip() if value is not None else default
        
        # Required fields
        name = safe_get('Restaurant')
        if not name:
            return None
        
        # Generate unique ID
        city_for_id = safe_get('City')
        restaurant_id = hashlib.md5(f"{name}_{city_for_id}".encode()).hexdigest()
        
        # Parse location
        city_str = row.get('City', '')
        
        # If there's a separate State column, use it; otherwise parse from city
        if 'State' in row and pd.notna(row.get('State')):
            city = safe_get('City')
            state = safe_get('State')
        else:
            # Fallback to parsing "City, State" format
            city, state = self.data_processor.parse_city_state(city_str)
        
        # Parse other fields
        cuisine_types = self.data_processor.parse_cuisine_types(row.get('Cuisine Type', ''))
        vibes = self.data_processor.parse_vibes(row.get('Vibes', ''))
        rating = self.data_processor.parse_star_rating(row.get('Rating', ''))
        price_level = self.data_processor.parse_price_level(row.get('Cost', ''))
        
        # Parse menu items
        menu_items = self.data_processor.parse_menu_items(row.get('Menu Items Tried:', ''))
        
        return Restaurant(
            id=restaurant_id,
            name=self.data_processor.clean_restaurant_name(name),
            cuisine_type=cuisine_types,
            vibes=vibes,
            location={
                'city': city,
                'state': state,
                'lat': None,  # Will be populated by GooglePlacesService
                'lng': None,
                'address': None
            },
            neighborhood=safe_get('Neighborhood') or None,
            user_rating=rating,
            price_level=price_level,
            revisit_preference=safe_get('Revisit ?') or None,
            notes=safe_get('Extra Notes:') or None,
            menu_items=menu_items
        )
    
    def validate_csv_format(self, csv_path: str) -> dict:
        """Validate CSV format and return analysis"""
        try:
            df = pd.read_csv(csv_path)
            df.columns = df.columns.str.strip()
            
            required_columns = ['Restaurant', 'City']
            optional_columns = ['Rating', 'Cuisine Type', 'Vibes', 'Cost', 'Neighborhood', 
                              'Revisit ?', 'Menu Items Tried:', 'Extra Notes:']
            
            missing_required = [col for col in required_columns if col not in df.columns]
            available_optional = [col for col in optional_columns if col in df.columns]
            
            # Sample data analysis
            non_empty_restaurants = df['Restaurant'].notna().sum()
            restaurants_with_ratings = 0
            if 'Rating' in df.columns:
                restaurants_with_ratings = df['Rating'].notna().sum()
            
            return {
                'valid': len(missing_required) == 0,
                'total_rows': len(df),
                'columns': list(df.columns),
                'missing_required_columns': missing_required,
                'available_optional_columns': available_optional,
                'non_empty_restaurants': non_empty_restaurants,
                'restaurants_with_ratings': restaurants_with_ratings,
                'sample_data': df.head(3).to_dict('records') if len(df) > 0 else []
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': str(e)
            }