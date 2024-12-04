import sys
from gui import launch_gui
import os
import yaml
from datetime import datetime

def ensure_default_settings():
    """Create default settings.yml if it doesn't exist"""
    default_settings = {
        # Account Settings
        'api_id': '',  # Add your API ID
        'api_hash': '', # Add your API hash
        'app_short_name': '',
        'phone_number': '',
    }
    
    try:
        if not os.path.exists('settings.yml'):
            with open('settings.yml', 'w', encoding='utf8') as f:
                yaml.dump(default_settings, f, allow_unicode=True, sort_keys=False)
        else:
            # Validate existing settings
            with open('settings.yml', 'r', encoding='utf8') as f:
                yaml.safe_load(f)
    except Exception as e:
        print(f"Error with settings.yml: {str(e)}")
        with open('settings.yml', 'w', encoding='utf8') as f:
            yaml.dump(default_settings, f, allow_unicode=True, sort_keys=False)

def ensure_directories():
    """Create required directories"""
    directories = ['./sessions', './data']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

if __name__ == "__main__":
    # Create required directories
    ensure_directories()
    
    # Ensure settings.yml exists and is valid
    ensure_default_settings()
    
    # Launch GUI
    launch_gui() 