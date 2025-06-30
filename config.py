"""
config.py
Configuration management for the Restaurant Recommendation System
"""

import os
import logging
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class Config:
    """Configuration management for the system"""
    
    def __init__(self):
        self.google_api_key = self._get_google_api_key()
        self.default_db_path = "restaurant_recommendations.db"
        self.rate_limit_delay = 0.1  # seconds between API requests
        self.batch_size = 50  # requests before longer pause
        
    def _get_google_api_key(self) -> Optional[str]:
        """Get Google API key from environment, .env file, or prompt user"""
        # First try environment variable
        api_key = os.getenv('GOOGLE_PLACES_API_KEY')
        
        if api_key:
            logger.info("Google Places API key loaded from environment variable")
            return api_key
        
        # Try alternative environment variable names
        api_key = os.getenv('GOOGLE_API_KEY')
        if api_key:
            logger.info("Google API key loaded from GOOGLE_API_KEY environment variable")
            return api_key
        
        # Try loading from .env file
        api_key = self._load_from_env_file()
        if api_key:
            return api_key
        
        # If no environment variable, provide helpful instructions
        logger.warning("No Google Places API key found")
        logger.info("To enable Google Places integration:")
        logger.info("1. Set GOOGLE_PLACES_API_KEY environment variable, or")
        logger.info("2. Run: python setup_google_api.py")
        
        return None
    
    def _load_from_env_file(self) -> Optional[str]:
        """Load API key from .env file"""
        env_file = Path('.env')
        if not env_file.exists():
            return None
        
        try:
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('GOOGLE_PLACES_API_KEY='):
                        api_key = line.split('=', 1)[1].strip()
                        # Remove quotes if present
                        if api_key.startswith('"') and api_key.endswith('"'):
                            api_key = api_key[1:-1]
                        if api_key.startswith("'") and api_key.endswith("'"):
                            api_key = api_key[1:-1]
                        
                        if api_key:
                            logger.info("Google Places API key loaded from .env file")
                            return api_key
        except Exception as e:
            logger.warning(f"Error reading .env file: {e}")
        
        return None
    
    def set_google_api_key(self, api_key: str) -> None:
        """Manually set Google API key"""
        self.google_api_key = api_key
        logger.info("Google Places API key set manually")
    
    def has_google_api_key(self) -> bool:
        """Check if Google API key is available"""
        return self.google_api_key is not None
    
    def get_google_api_key(self) -> Optional[str]:
        """Get the Google API key"""
        return self.google_api_key

# Global configuration instance
config = Config()