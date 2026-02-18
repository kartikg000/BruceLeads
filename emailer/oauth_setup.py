#!/usr/bin/env python3
"""
Gmail OAuth Setup Script
Guides users through the Gmail API authentication process.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from emailer.gmail_client import GmailClient
import config


def main():
    print("""
╔═══════════════════════════════════════════════════════════════════╗
║                    BruceLeads Gmail Setup                         ║
╠═══════════════════════════════════════════════════════════════════╣
║  This script will help you connect your Gmail account.            ║
║                                                                   ║
║  Before running this script, you need to:                         ║
║                                                                   ║
║  1. Go to https://console.cloud.google.com                        ║
║  2. Create a new project (or select existing)                     ║
║  3. Enable the Gmail API:                                         ║
║     - Go to "APIs & Services" > "Library"                         ║
║     - Search for "Gmail API" and enable it                        ║
║  4. Configure OAuth consent screen:                               ║
║     - Go to "APIs & Services" > "OAuth consent screen"            ║
║     - Select "External" user type                                 ║
║     - Fill in app name and your email                             ║
║     - Add scopes: gmail.compose, gmail.send                       ║
║     - Add your email as a test user                               ║
║  5. Create OAuth credentials:                                     ║
║     - Go to "APIs & Services" > "Credentials"                     ║
║     - Click "Create Credentials" > "OAuth client ID"              ║
║     - Select "Desktop app" as application type                    ║
║     - Download the JSON file                                      ║
║  6. Save the JSON file to:                                        ║
║     {credentials_path}
╚═══════════════════════════════════════════════════════════════════╝
""".format(credentials_path=config.GMAIL_CREDENTIALS_FILE))
    
    # Check if credentials file exists
    if not config.GMAIL_CREDENTIALS_FILE.exists():
        print(f"\n❌ Credentials file not found: {config.GMAIL_CREDENTIALS_FILE}")
        print("\nPlease download your OAuth credentials from Google Cloud Console")
        print("and save them to the path shown above.")
        
        # Create credentials directory if it doesn't exist
        config.CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)
        print(f"\nThe credentials folder has been created at: {config.CREDENTIALS_DIR}")
        
        input("\nPress Enter to exit...")
        return
    
    print("✅ Credentials file found!")
    print("\nStarting OAuth flow...")
    print("A browser window will open for you to authorize the application.")
    print("")
    
    try:
        client = GmailClient()
        is_configured = client.authenticate()
        
        if is_configured:
            print("\n" + "="*50)
            print("✅ SUCCESS! Gmail authentication complete!")
            print("="*50)
            print(f"\nGmail user: {client.user}")
            print("\nYou can now use BruceLeads to send emails.")
        else:
            print("\n❌ Gmail credentials not configured.")
            print("Set GMAIL_USER and GMAIL_APP_PASSWORD in your .env file.")
        
    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
    except Exception as e:
        print(f"\n❌ Authentication failed: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure you downloaded the correct credentials file")
        print("2. Ensure your email is added as a test user in OAuth consent screen")
        print("3. Try deleting the token file and running this script again")
    
    input("\nPress Enter to exit...")


if __name__ == "__main__":
    main()
