#!/usr/bin/env python3
"""
setup_google_api.py
Helper script to set up Google Places API integration
"""

import os
import sys
from pathlib import Path

def main():
    """Interactive setup for Google Places API"""
    
    print("=" * 60)
    print("GOOGLE PLACES API SETUP")
    print("=" * 60)
    
    # Check if API key is already set
    current_key = os.getenv('GOOGLE_PLACES_API_KEY')
    if current_key:
        print(f"✓ Google Places API key is already configured")
        print(f"  Current key: {current_key[:8]}...{current_key[-4:] if len(current_key) > 12 else '***'}")
        
        try:
            response = input("\nDo you want to update it? (y/N): ").strip().lower()
            if response not in ['y', 'yes']:
                print("Setup cancelled. Existing API key will be used.")
                return
        except (EOFError, KeyboardInterrupt):
            print("\nNon-interactive mode detected.")
            print("To set up your API key:")
            print("1. Copy .env.example to .env")
            print("2. Edit .env and add your Google Places API key")
            print("3. Or run: export GOOGLE_PLACES_API_KEY='your_key_here'")
            return
    
    print("\nTo enable Google Places API integration, you need:")
    print("1. A Google Cloud Platform account")
    print("2. Places API enabled in your project")
    print("3. An API key with Places API permissions")
    print()
    print("Setup instructions:")
    print("1. Go to: https://console.cloud.google.com/")
    print("2. Create or select a project")
    print("3. Enable the Places API")
    print("4. Create credentials (API Key)")
    print("5. Restrict the API key to Places API for security")
    print()
    
    try:
        api_key = input("Enter your Google Places API key: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nNon-interactive mode detected.")
        print("\nTo set up your API key manually:")
        print("1. Copy .env.example to .env:")
        print("   cp .env.example .env")
        print("2. Edit .env and uncomment/add your API key:")
        print("   GOOGLE_PLACES_API_KEY=your_actual_api_key_here")
        print("3. Or set environment variable:")
        print("   export GOOGLE_PLACES_API_KEY='your_actual_api_key_here'")
        return
    
    if not api_key:
        print("No API key provided. Setup cancelled.")
        return
    
    if len(api_key) < 30 or not api_key.startswith('AIza'):
        print("⚠ Warning: This doesn't look like a valid Google API key")
        print("  Google API keys typically start with 'AIza' and are ~40 characters long")
        
        response = input("Continue anyway? (y/N): ").strip().lower()
        if response not in ['y', 'yes']:
            print("Setup cancelled.")
            return
    
    # Method 1: Create .env file
    env_file = Path('.env')
    env_content = f"GOOGLE_PLACES_API_KEY={api_key}\n"
    
    if env_file.exists():
        # Read existing content and update/add the API key
        with open(env_file, 'r') as f:
            lines = f.readlines()
        
        updated = False
        for i, line in enumerate(lines):
            if line.startswith('GOOGLE_PLACES_API_KEY='):
                lines[i] = env_content
                updated = True
                break
        
        if not updated:
            lines.append(env_content)
        
        with open(env_file, 'w') as f:
            f.writelines(lines)
    else:
        with open(env_file, 'w') as f:
            f.write(env_content)
    
    print(f"✓ API key saved to .env file")
    
    # Method 2: Environment variable instructions
    print("\nEnvironment Variable Setup:")
    print("=" * 40)
    print("For permanent setup, add this to your shell profile:")
    print()
    
    shell = os.getenv('SHELL', '').split('/')[-1]
    if shell in ['bash', 'zsh']:
        profile_file = f"~/.{shell}rc" if shell == 'bash' else "~/.zshrc"
        print(f"echo 'export GOOGLE_PLACES_API_KEY=\"{api_key}\"' >> {profile_file}")
        print(f"source {profile_file}")
    else:
        print(f"export GOOGLE_PLACES_API_KEY=\"{api_key}\"")
    
    print()
    print("Or for this session only:")
    print(f"export GOOGLE_PLACES_API_KEY=\"{api_key}\"")
    
    # Test the setup
    print("\nTesting API key...")
    try:
        from config import config
        # Reload config to pick up new environment
        config.__init__()
        
        if config.has_google_api_key():
            print("✓ API key configuration successful!")
            print("  Google Places integration is now enabled")
        else:
            print("⚠ API key not detected. You may need to restart your shell or run:")
            print(f"  export GOOGLE_PLACES_API_KEY=\"{api_key}\"")
    
    except ImportError:
        print("✓ API key saved. Run the application to test integration.")
    
    print("\n" + "=" * 60)
    print("SETUP COMPLETE!")
    print("=" * 60)
    print("Your restaurant recommendations will now include:")
    print("• Enhanced location data from Google Places")
    print("• Google ratings and reviews")
    print("• Improved restaurant matching")
    print("• More accurate coordinates")

if __name__ == "__main__":
    main()