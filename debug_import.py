#!/usr/bin/env python3
"""
debug_import.py
Debug CSV import issues and show what's actually stored in the database
"""

import pandas as pd
import sqlite3
import sys
import argparse

def debug_csv_and_db(csv_path, db_path="restaurant_recommendations.db"):
    """Debug CSV import vs database storage"""
    
    print("🔍 CSV vs Database Debug Analysis")
    print("=" * 60)
    
    # 1. Check CSV structure
    print(f"\n📋 1. CSV FILE ANALYSIS: {csv_path}")
    print("-" * 40)
    try:
        df = pd.read_csv(csv_path)
        print(f"✅ CSV loaded: {len(df)} rows")
        
        print(f"\n📊 CSV Columns:")
        for i, col in enumerate(df.columns, 1):
            print(f"   {i}. '{col}'")
        
        print(f"\n📋 Sample CSV data (first row):")
        if len(df) > 0:
            first_row = df.iloc[0]
            for col in df.columns:
                value = first_row[col]
                print(f"   {col}: '{value}' (type: {type(value).__name__})")
    
    except Exception as e:
        print(f"❌ Error reading CSV: {e}")
        return
    
    # 2. Check database content
    print(f"\n🗄️  2. DATABASE ANALYSIS: {db_path}")
    print("-" * 40)
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get restaurant count
        cursor.execute("SELECT COUNT(*) FROM restaurants")
        db_count = cursor.fetchone()[0]
        print(f"✅ Database connected: {db_count} restaurants stored")
        
        if db_count > 0:
            # Get database schema
            cursor.execute("PRAGMA table_info(restaurants)")
            columns = cursor.fetchall()
            
            print(f"\n📊 Database Columns:")
            for col in columns:
                print(f"   {col[1]} ({col[2]})")
            
            # Get sample restaurant
            cursor.execute("SELECT * FROM restaurants LIMIT 1")
            sample_row = cursor.fetchone()
            
            if sample_row:
                print(f"\n📋 Sample database row:")
                column_names = [col[1] for col in columns]
                for i, (col_name, value) in enumerate(zip(column_names, sample_row)):
                    if value is not None and value != '':
                        print(f"   ✅ {col_name}: '{value}'")
                    else:
                        print(f"   ❌ {col_name}: NULL/EMPTY")
        
        conn.close()
    
    except Exception as e:
        print(f"❌ Error reading database: {e}")
        return
    
    # 3. Column mapping analysis
    print(f"\n🔄 3. COLUMN MAPPING ANALYSIS")
    print("-" * 40)
    
    # Expected column mappings
    column_mappings = {
        'Restaurant': ['name', 'restaurant_name', 'restaurant'],
        'City': ['city', 'location', 'city_name'],
        'State': ['state', 'state_name', 'province'],
        'Cuisine Type': ['cuisine', 'cuisine_type', 'food_type', 'type'],
        'Rating': ['rating', 'user_rating', 'stars', 'score'],
        'Vibes': ['vibes', 'atmosphere', 'ambiance', 'mood'],
        'Cost': ['cost', 'price', 'price_level', 'price_range', '$'],
        'Extra Notes:': ['notes', 'extra_notes', 'comments', 'description'],
        'Revisit ?': ['revisit', 'return', 'would_return', 'go_back']
    }
    
    csv_columns = list(df.columns)
    
    print("Expected → Your CSV:")
    for expected, alternatives in column_mappings.items():
        found = False
        for col in csv_columns:
            if col == expected:
                print(f"   ✅ '{expected}' → '{col}' (EXACT MATCH)")
                found = True
                break
            elif col.lower().strip() in [alt.lower() for alt in alternatives]:
                print(f"   ⚠️  '{expected}' → '{col}' (CLOSE MATCH - might need renaming)")
                found = True
                break
        
        if not found:
            matching_cols = [col for col in csv_columns if any(alt.lower() in col.lower() for alt in alternatives)]
            if matching_cols:
                print(f"   🤔 '{expected}' → Possible matches: {matching_cols}")
            else:
                print(f"   ❌ '{expected}' → NOT FOUND")
    
    # 4. Recommendations
    print(f"\n💡 4. RECOMMENDATIONS")
    print("-" * 40)
    
    required_exact = ['Restaurant', 'City']
    missing_exact = []
    
    for req in required_exact:
        if req not in csv_columns:
            missing_exact.append(req)
    
    if missing_exact:
        print(f"🔧 REQUIRED FIXES:")
        print(f"   Your CSV needs these EXACT column names:")
        for req in missing_exact:
            # Find closest match
            closest = None
            for col in csv_columns:
                if any(word in col.lower() for word in req.lower().split()):
                    closest = col
                    break
            
            if closest:
                print(f"   • Rename '{closest}' → '{req}'")
            else:
                print(f"   • Add column '{req}'")
        
        print(f"\n📝 Quick fix - change your CSV header row to:")
        suggested_header = csv_columns.copy()
        
        # Suggest replacements
        for i, col in enumerate(suggested_header):
            for expected, alternatives in column_mappings.items():
                if col.lower().strip() in [alt.lower() for alt in alternatives]:
                    suggested_header[i] = expected
                    break
        
        print(f"   {','.join(suggested_header)}")
    
    else:
        print(f"✅ Your CSV column names look good!")
        print(f"   The issue might be with data formatting or parsing.")
        
        # Check for data issues
        print(f"\n🔍 Data Quality Check:")
        required_data_cols = ['Restaurant', 'City']
        for col in required_data_cols:
            if col in df.columns:
                null_count = df[col].isna().sum()
                empty_count = (df[col] == '').sum()
                print(f"   {col}: {null_count} null, {empty_count} empty out of {len(df)} total")

def main():
    parser = argparse.ArgumentParser(description="Debug CSV import issues")
    parser.add_argument('csv_file', help='Path to CSV file')
    parser.add_argument('--database', '-d', default='restaurant_recommendations.db',
                       help='Database file path')
    args = parser.parse_args()
    
    debug_csv_and_db(args.csv_file, args.database)

if __name__ == "__main__":
    main()