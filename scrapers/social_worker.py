"""
Social Media Scraper Worker
Runs in a subprocess to find leads via Google X-Ray search on social platforms.
"""

import sys
import json
import time
import random
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from models import Lead, LeadSource
from utils.validators import extract_emails_from_text

def scrape_social_search(query: str, platform: str, max_results: int = 20, headless: bool = True, profile_dir: str = None, browser_type: str = None) -> dict:
    """
    Search for leads on social media via Google.
    
    Platforms:
    - linkedin: site:linkedin.com/in/ [query]
    - twitter: site:twitter.com [query]
    - reddit: site:reddit.com [query]
    - instagram: site:instagram.com [query]
    """
    leads = []
    errors = []
    
    # Construct Google X-Ray query
    site_operators = {
        'linkedin': 'site:linkedin.com/in/',
        'twitter': 'site:twitter.com',
        'reddit': 'site:reddit.com',
        'instagram': 'site:instagram.com',
        'facebook': 'site:facebook.com'
    }
    
    site_op = site_operators.get(platform.lower(), '')
    if not site_op:
        return {"success": False, "leads": [], "errors": [f"Unknown platform: {platform}"], "total_found": 0}
        
    full_query = f"{site_op} {query}"
    search_url = f"https://www.google.com/search?q={full_query.replace(' ', '+')}"
    
    playwright = None
    browser = None
    context = None
    
    try:
        print(f"Starting Playwright for {platform} search...", file=sys.stderr)
        playwright = sync_playwright().start()
        
        if profile_dir:
            # Use persistent context — reuses saved login session
            print(f"Using saved browser profile: {profile_dir}", file=sys.stderr)
            launch_args = {
                'user_data_dir': profile_dir,
                'headless': headless,
                'args': ['--disable-blink-features=AutomationControlled', '--no-sandbox'],
                'viewport': {'width': 1920, 'height': 1080},
                'user_agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                'locale': 'en-US',
                'ignore_default_args': ['--enable-automation']
            }
            # Use the same browser channel as was used during login
            if browser_type and browser_type.lower() in ('chrome', 'msedge'):
                launch_args['channel'] = browser_type.lower()
                print(f"Using browser channel: {browser_type}", file=sys.stderr)
            
            context = playwright.chromium.launch_persistent_context(**launch_args)
            page = context.pages[0] if context.pages else context.new_page()
        else:
            # Anonymous mode — fresh browser
            browser = playwright.chromium.launch(
                headless=headless,
                args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
            )
            
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={'width': 1920, 'height': 1080},
                locale='en-US'
            )
            
            page = context.new_page()
        
        print(f"Navigating to: {search_url}", file=sys.stderr)
        page.goto(search_url, wait_until='load', timeout=45000)
        time.sleep(random.uniform(2, 4))
        
        # Accept cookies
        try:
            for selector in ['button:has-text("Accept all")', 'button:has-text("I agree")']:
                btn = page.locator(selector)
                if btn.count() > 0:
                    btn.first.click()
                    time.sleep(1)
                    break
        except Exception:
            pass
        
        # Wait for results - maintain robust selectors
        try:
            # Wait for any of these common result containers
            page.wait_for_selector('#search, #rso, .g', timeout=15000)
        except PlaywrightTimeout:
            # If standard selectors fail, check if we hit a captcha or empty page
            content = page.content().lower()
            captcha_keywords = ["verify it's you", "captcha", "unusual traffic", "not a robot", "recaptcha", "challenge-form", "verify you are a human"]
            if any(kw in content for kw in captcha_keywords):
                errors.append("Google CAPTCHA detected — Try: 1) Uncheck 'Headless Mode' to solve manually, 2) Log into your Google account in the platform login browser")
                return {"success": False, "leads": [], "errors": errors, "total_found": 0}
            
            errors.append("Could not find results (selector timeout)")
            return {"success": False, "leads": [], "errors": errors, "total_found": 0}
        
        # Scroll logic
        results_found = 0
        scrolls = 0
        while results_found < max_results and scrolls < 3:
            page.keyboard.press('End')
            time.sleep(1.0)
            scrolls += 1
            
        # Parse results using multiple possible selectors
        # .g is the standard class for a search result container
        result_elements = page.locator('.g').all()
        
        if not result_elements:
            # Try fallback selector
            result_elements = page.locator('[data-header-feature]').all()
        
        print(f"Found {len(result_elements)} raw results", file=sys.stderr)
        
        for i, el in enumerate(result_elements):
            if len(leads) >= max_results:
                break
                
            try:
                title_el = el.locator('h3').first
                link_el = el.locator('a').first
                snippet_el = el.locator('.VwiC3b, .IsZvec').first  # Common Google snippet classes
                
                if title_el.count() > 0 and link_el.count() > 0:
                    title = title_el.inner_text()
                    url = link_el.get_attribute('href')
                    snippet = snippet_el.inner_text() if snippet_el.count() > 0 else ""
                    
                    if not url or 'google.com' in url:
                        continue
                        
                    # Extract info based on platform
                    lead_data = {
                        "source": f"Social - {platform.title()}",
                        "website": url,
                        "business_name": title,  # Default
                        "notes": snippet
                    }
                    
                    # Attempt to extract email from snippet
                    emails = extract_emails_from_text(snippet + " " + title)
                    if emails:
                        lead_data["email"] = emails[0]
                    
                    # Platform specific parsing
                    if platform == 'linkedin':
                        # "Name - Title - Company | LinkedIn"
                        parts = title.split(' - ')
                        if len(parts) >= 2:
                            lead_data['owner_name'] = parts[0]
                            lead_data['business_name'] = parts[-1].replace('| LinkedIn', '').strip()
                        elif '|' in title:
                            # "Name | Title | LinkedIn"
                            parts = title.split('|')
                            lead_data['owner_name'] = parts[0].strip()
                            
                    elif platform == 'twitter':
                        # "Name (@handle) / X"
                        parts = title.split('(')
                        if len(parts) >= 2:
                            lead_data['business_name'] = parts[0].strip()
                            # Handle extraction could go here
                            
                    elif platform == 'reddit':
                        # "Title of post : r/subreddit"
                        if ':' in title:
                            lead_data['business_name'] = title.split(':')[0].strip()
                    
                    leads.append(lead_data)
                    print(f"  [{len(leads)}] {lead_data['business_name']}", file=sys.stderr)
                    
            except Exception as e:
                continue
        
        return {
            "success": True,
            "leads": leads,
            "errors": errors,
            "total_found": len(leads)
        }
        
    except Exception as e:
        errors.append(f"Scraping failed: {str(e)}")
        return {"success": False, "leads": [], "errors": errors, "total_found": 0}
        
    finally:
        try:
            if context:
                context.close()
            if browser:
                browser.close()
            if playwright:
                playwright.stop()
        except Exception:
            pass


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(json.dumps({"success": False, "leads": [], "errors": ["Usage: social_worker.py <query> <platform> [max_results] [headless] [--profile-dir DIR]"]}))
        sys.exit(1)
    
    query = sys.argv[1]
    platform = sys.argv[2]
    max_results = int(sys.argv[3]) if len(sys.argv) > 3 else 20
    headless = sys.argv[4].lower() == 'true' if len(sys.argv) > 4 else True
    
    # Parse optional --profile-dir argument
    profile_dir = None
    browser_type = None
    for i, arg in enumerate(sys.argv):
        if arg == '--profile-dir' and i + 1 < len(sys.argv):
            profile_dir = sys.argv[i + 1]
        if arg == '--browser' and i + 1 < len(sys.argv):
            browser_type = sys.argv[i + 1]
    
    result = scrape_social_search(query, platform, max_results, headless, profile_dir, browser_type)
    print(json.dumps(result))
