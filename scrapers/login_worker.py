"""
Login Worker
Runs in a subprocess to open a visible browser for the user to log in.
Uses Playwright persistent context so cookies are saved to the profile directory.
"""

import sys
import json
import time
from pathlib import Path

from playwright.sync_api import sync_playwright


def run_login(platform: str, login_url: str, profile_dir: str, browser_type: str = "chrome") -> dict:
    """
    Open a visible browser for manual login.
    
    The browser uses a persistent context (profile_dir) so all cookies,
    local storage, and session data are saved automatically.
    
    The browser stays open until the user closes it or login is detected.
    """
    playwright = None
    context = None
    
    try:
        print(f"Opening {platform.title()} login page...", file=sys.stderr)
        playwright = sync_playwright().start()
        
        # Determine browser channel
        launch_args = {
            'user_data_dir': profile_dir,
            'headless': False,  # MUST be visible for user to interact
            'args': [
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--start-maximized'
            ],
            'viewport': {'width': 1280, 'height': 900},
            'user_agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            'locale': 'en-US',
            'ignore_default_args': ['--enable-automation']
        }
        
        # Use installed Chrome/Edge when specified
        if browser_type.lower() in ('chrome', 'msedge'):
            launch_args['channel'] = browser_type.lower()
        # else: use Playwright's built-in Chromium (no channel needed)
        
        context = playwright.chromium.launch_persistent_context(**launch_args)
        
        page = context.pages[0] if context.pages else context.new_page()
        
        # Navigate to login page
        page.goto(login_url, wait_until='domcontentloaded', timeout=30000)
        
        print(f"Waiting for user to log in to {platform.title()}...", file=sys.stderr)
        print("The browser will close automatically when login is detected,", file=sys.stderr)
        print("or you can close it manually when done.", file=sys.stderr)
        
        # Wait for the user to log in
        # We poll the current URL to detect if they've navigated away from the login page
        login_confirmed = False  # True only when URL redirect proves login
        browser_closed = False   # True when user manually closes browser
        max_wait = 300  # 5 minutes
        start_time = time.time()
        
        # URLs that indicate login is still in progress
        login_page_patterns = ['/login', '/signin', '/sign-in', '/flow/login', '/oauth', '/authorize', '/checkpoint/', '/uas/', '/register']
        
        # Platform-specific success URLs (if we land on any of these, login worked)
        success_patterns = {
            'linkedin': ['/feed', '/mynetwork', '/messaging', '/in/', '/notifications'],
            'twitter': ['/home', '/compose', '/notifications', '/explore'],
            'reddit': ['/r/', '/user/', '/?feed='],
            'instagram': ['/accounts/onetap', '/explore', '/direct'],
            'facebook': ['/home', '/?sk=', '/profile', '/groups'],
        }
        platform_success = success_patterns.get(platform.lower(), [])
        
        while time.time() - start_time < max_wait:
            try:
                # Check if page/context is still open
                if page.is_closed():
                    browser_closed = True
                    break
                
                current_url = page.url.lower()
                
                # Check for platform-specific success URLs first
                if any(pattern in current_url for pattern in platform_success):
                    print(f"Login detected! Redirected to: {current_url}", file=sys.stderr)
                    login_confirmed = True
                    time.sleep(3)  # Let cookies finalize
                    break
                
                # If URL changed away from any login-related page, login likely succeeded
                if not any(pattern in current_url for pattern in login_page_patterns):
                    if time.time() - start_time > 5:  # Give 5s for initial page load
                        print(f"Login detected! URL changed to: {current_url}", file=sys.stderr)
                        login_confirmed = True
                        time.sleep(3)
                        break
                    
            except Exception:
                # Page/context was closed by user
                browser_closed = True
                break
            
            time.sleep(2)
        
        # Write marker file ONLY when login was confirmed via URL
        if login_confirmed:
            marker_path = Path(profile_dir) / "login_success.json"
            import json as json_mod
            with open(marker_path, 'w') as f:
                json_mod.dump({"platform": platform, "timestamp": time.time(), "browser": browser_type}, f)
            result = {"success": True, "message": f"Successfully logged in to {platform.title()}! Session saved."}
        elif browser_closed:
            result = {"success": False, "message": f"Browser closed without confirmed login. Try again and complete the login."}
        else:
            result = {"success": False, "message": "Login timed out. Please try again."}
        
        return result
        
    except Exception as e:
        return {"success": False, "message": f"Login error: {str(e)}"}
        
    finally:
        try:
            if context:
                context.close()
            if playwright:
                playwright.stop()
        except Exception:
            pass


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(json.dumps({"success": False, "message": "Usage: login_worker.py <platform> <login_url> <profile_dir> [--browser chrome|msedge|chromium]"}))
        sys.exit(1)
    
    platform = sys.argv[1]
    login_url = sys.argv[2]
    profile_dir = sys.argv[3]
    
    # Parse optional --browser argument
    browser_type = "chrome"  # default
    for i, arg in enumerate(sys.argv):
        if arg == '--browser' and i + 1 < len(sys.argv):
            browser_type = sys.argv[i + 1]
            break
    
    result = run_login(platform, login_url, profile_dir, browser_type)
    print(json.dumps(result))
