
import os
from pathlib import Path
import config

# File to store the validated license key locally
LICENSE_FILE = Path(__file__).parent.parent / ".license_key"

def get_stored_license():
    """Retrieve the stored license key if it exists."""
    if LICENSE_FILE.exists():
        return LICENSE_FILE.read_text().strip()
    return None

def verify_license_key(key: str) -> bool:
    """
    Verify the license key against LemonSqueezy API.
    
    Args:
        key: The license key entered by the user
        
    Returns:
        True if valid, False otherwise
    """
    if not key:
        return False
        
    # TODO: Replace with actual LemonSqueezy API call
    # API_URL = "https://api.lemonsqueezy.com/v1/licenses/validate"
    # response = requests.post(API_URL, data={"license_key": key})
    # return response.json().get('valid', False)
    
    # MOCK VALIDATION FOR DEVELOPMENT
    # Accepts any key that starts with "BRUCE-"
    return key.strip().upper().startswith("BRUCE-")

def save_license_key(key: str):
    """Save the validated license key locally."""
    LICENSE_FILE.write_text(key.strip())

def check_access():
    """
    Check if the user has a valid license.
    Returns True if access granted, False if activation needed.
    """
    key = get_stored_license()
    if key and verify_license_key(key):
        return True
    return False
