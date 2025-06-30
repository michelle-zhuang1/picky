#!/usr/bin/env python3
"""
validate_csv.py
Debug and validate CSV files for Picky
"""

import pandas as pd
import sys
import argparse

def validate_csv(csv_path):
    """Validate and debug CSV file"""
    
    print(f"🔍 Validating CSV file: {csv_path}")
    print("=" * 50)
    
    try:
        # Read the CSV file
        df = pd.read_csv(csv_path)
        print(f"✅ CSV file loaded successfully")
        print(f"📊 Total rows: {len(df)}")
        
        # Show original column names
        print(f"\n📋 Your CSV columns:")
        for i, col in enumerate(df.columns, 1):
            print(f"   {i}. '{col}'")
        
        # Clean column names (same as system does)
        df.columns = df.columns.str.strip()
        
        print(f"\n📋 Cleaned column names:")
        for i, col in enumerate(df.columns, 1):
            print(f"   {i}. '{col}'")
        
        # Check required columns
        required_columns = ['Restaurant', 'City']
        print(f"\n✅ Required columns:")
        for col in required_columns:
            if col in df.columns:
                print(f"   ✓ '{col}' - Found")
            else:
                print(f"   ❌ '{col}' - MISSING")
        
        # Check optional columns
        optional_columns = ['Rating', 'Cuisine Type', 'Vibes', 'Cost', 'Neighborhood', 
                          'Revisit ?', 'Menu Items Tried:', 'Extra Notes:', 'State']
        
        print(f"\n📝 Optional columns found:")
        found_optional = []
        for col in optional_columns:
            if col in df.columns:
                found_optional.append(col)
                print(f"   ✓ '{col}'")
        
        if not found_optional:
            print("   (none found)")
        
        # Show sample data
        print(f"\n📋 Sample data (first 3 rows):")
        if len(df) > 0:
            print(df.head(3).to_string(index=False))
        else:
            print("   (no data rows)")
        
        # Validation result
        missing_required = [col for col in required_columns if col not in df.columns]
        
        print(f"\n🎯 VALIDATION RESULT:")
        if not missing_required:
            print("   ✅ CSV format is VALID")
            print("   ✅ Ready for import!")
        else:
            print("   ❌ CSV format is INVALID")
            print(f"   ❌ Missing required columns: {missing_required}")
            
            print(f"\n🔧 TO FIX YOUR CSV:")
            print("   1. Make sure you have these exact column names:")
            print("      - 'Restaurant' (not 'restaurant_name' or 'name')")
            print("      - 'City' (not 'city' or 'location')")
            print("   2. Check for extra spaces or special characters")
            print("   3. Save as CSV format")
            
            print(f"\n📝 Example of correct format:")
            print("Restaurant,City,State,Cuisine Type,Rating")
            print("\"Joe's Pizza\",\"New York\",\"NY\",\"Italian\",4")
    
    except FileNotFoundError:
        print(f"❌ Error: File '{csv_path}' not found")
        return False
    
    except pd.errors.EmptyDataError:
        print(f"❌ Error: CSV file is empty")
        return False
    
    except Exception as e:
        print(f"❌ Error reading CSV: {e}")
        return False
    
    return len([col for col in required_columns if col not in df.columns]) == 0

def main():
    parser = argparse.ArgumentParser(description="Validate CSV files for Picky")
    parser.add_argument('csv_file', help='Path to CSV file to validate')
    args = parser.parse_args()
    
    valid = validate_csv(args.csv_file)
    
    if valid:
        print(f"\n🎉 Your CSV is ready! You can now run:")
        print(f"   python picky.py import {args.csv_file} --user your_name")
    else:
        print(f"\n🔧 Please fix your CSV and try again")
        sys.exit(1)

if __name__ == "__main__":
    main()