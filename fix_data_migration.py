#!/usr/bin/env python3
"""
fix_data_migration.py
Script to fix wishlist migration and parse city/state for existing restaurants
"""

import sqlite3
import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_address(formatted_address: str) -> dict:
    """Parse formatted address to extract city and state"""
    if not formatted_address:
        return {'city': '', 'state': ''}
    
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

def fix_wishlist_migration():
    """Fix wishlist migration for manually added restaurants"""
    with sqlite3.connect('restaurant_recommendations.db') as conn:
        cursor = conn.cursor()
        
        # Mark manually added restaurants with Google Place IDs as wishlist items
        # These would have been added via the CLI add command
        cursor.execute("""
            UPDATE restaurants 
            SET is_wishlist = 1 
            WHERE google_place_id IS NOT NULL 
            AND id LIKE 'gp_%'
            AND (revisit_preference = 'Yes' OR revisit_preference IS NULL)
            AND user_rating IS NULL
        """)
        
        updated_count = cursor.rowcount
        logger.info(f"Marked {updated_count} restaurants as wishlist items")
        
        # Also mark restaurants that were added with wishlist intention but had different criteria
        cursor.execute("""
            SELECT id, name, google_place_id, revisit_preference, notes 
            FROM restaurants 
            WHERE google_place_id IS NOT NULL 
            AND id LIKE 'gp_%'
            AND user_rating IS NULL
        """)
        
        candidates = cursor.fetchall()
        for restaurant_id, name, place_id, revisit_pref, notes in candidates:
            # If it's clearly a manually added restaurant (has specific notes or wishlist markers)
            if (notes and len(notes) > 10) or revisit_pref == 'Yes':
                cursor.execute("UPDATE restaurants SET is_wishlist = 1 WHERE id = ?", (restaurant_id,))
                logger.info(f"Marked {name} as wishlist item")
        
        conn.commit()

def fix_city_state_parsing():
    """Parse city and state for restaurants with NULL values"""
    with sqlite3.connect('restaurant_recommendations.db') as conn:
        cursor = conn.cursor()
        
        # Get restaurants with NULL city or state but have addresses
        cursor.execute("""
            SELECT id, name, address, city, state 
            FROM restaurants 
            WHERE (city IS NULL OR city = '' OR state IS NULL OR state = '') 
            AND address IS NOT NULL 
            AND address != ''
        """)
        
        restaurants_to_update = cursor.fetchall()
        logger.info(f"Found {len(restaurants_to_update)} restaurants needing address parsing")
        
        for restaurant_id, name, address, current_city, current_state in restaurants_to_update:
            parsed = parse_address(address)
            
            # Only update if we found better values
            new_city = parsed['city'] if parsed['city'] else (current_city or '')
            new_state = parsed['state'] if parsed['state'] else (current_state or '')
            
            if new_city != (current_city or '') or new_state != (current_state or ''):
                cursor.execute("""
                    UPDATE restaurants 
                    SET city = ?, state = ? 
                    WHERE id = ?
                """, (new_city, new_state, restaurant_id))
                
                logger.info(f"Updated {name}: city='{new_city}', state='{new_state}'")
        
        conn.commit()

def main():
    """Run both migrations"""
    logger.info("Starting data migration fixes...")
    
    logger.info("1. Fixing wishlist migration...")
    fix_wishlist_migration()
    
    logger.info("2. Parsing city/state from addresses...")
    fix_city_state_parsing()
    
    logger.info("Migration fixes completed!")
    
    # Show results
    with sqlite3.connect('restaurant_recommendations.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM restaurants WHERE is_wishlist = 1")
        wishlist_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM restaurants WHERE city != '' AND state != ''")
        parsed_count = cursor.fetchone()[0]
        
        logger.info(f"Final results: {wishlist_count} wishlist items, {parsed_count} restaurants with city/state")

if __name__ == "__main__":
    main()