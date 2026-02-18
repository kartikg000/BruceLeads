"""
Google Maps Scraper Worker
Standalone script that runs Playwright scraping in a separate process.
This bypasses event loop issues on Windows.
"""

import sys
import json
import time
import random
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
import config
from models import Lead, LeadSource
from utils import clean_business_name, normalize_url


def scrape_google_maps(query: str, location: str, max_results: int = 20, headless: bool = True) -> dict:
    """
    Scrape Google Maps and return results as a dict.
    """
    leads = []
    errors = []
    
    full_query = f"{query} in {location}" if location else query
    search_url = f"https://www.google.com/maps/search/{full_query.replace(' ', '+')}"
    
    playwright = None
    browser = None
    
    try:
        print(f"Starting Playwright...", file=sys.stderr)
        playwright = sync_playwright().start()
        
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
        time.sleep(3)
        
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
        
        # Wait for results
        try:
            page.wait_for_selector('[role="feed"]', timeout=10000)
        except PlaywrightTimeout:
            errors.append("Could not find results - try a different search")
            return {"success": False, "leads": [], "errors": errors, "total_found": 0}
        
        time.sleep(2)
        
        # Scroll to load more
        try:
            container = page.locator('[role="feed"]').first
            if container.count() > 0:
                for _ in range(5):
                    container.evaluate('node => node.scrollTop = node.scrollHeight')
                    time.sleep(1)
        except Exception:
            pass
        
        # Get result links
        links = page.locator('a[href*="/maps/place/"]').all()
        seen = set()
        unique_urls = []
        
        for link in links:
            try:
                href = link.get_attribute('href')
                if href and '/maps/place/' in href:
                    base = href.split('?')[0]
                    if base not in seen:
                        seen.add(base)
                        unique_urls.append(href)
            except Exception:
                continue
        
        unique_urls = unique_urls[:max_results]
        total = len(unique_urls)
        
        if total == 0:
            errors.append("No results found for this search")
            return {"success": False, "leads": [], "errors": errors, "total_found": 0}
        
        print(f"Found {total} results", file=sys.stderr)
        
        # Extract each business
        for i, url in enumerate(unique_urls):
            try:
                print(f"Processing {i+1}/{total}...", file=sys.stderr)
                
                page.goto(url, wait_until='domcontentloaded', timeout=15000)
                time.sleep(1.5)
                
                lead_data = {"source": LeadSource.GOOGLE_MAPS.value}
                
                # Business name
                for selector in ['h1', '.DUwDvf']:
                    try:
                        elem = page.locator(selector).first
                        if elem.count() > 0:
                            text = elem.inner_text()
                            if text and len(text) > 1:
                                lead_data['business_name'] = clean_business_name(text)
                                break
                    except Exception:
                        continue
                
                if not lead_data.get('business_name'):
                    continue
                
                # Phone
                try:
                    for selector in ['button[data-item-id*="phone"] .Io6YTe', 'a[href^="tel:"]']:
                        elem = page.locator(selector).first
                        if elem.count() > 0:
                            if 'href' in selector:
                                href = elem.get_attribute('href')
                                if href:
                                    lead_data['phone'] = href.replace('tel:', '')
                            else:
                                lead_data['phone'] = elem.inner_text()
                            if lead_data.get('phone'):
                                break
                except Exception:
                    pass
                
                # Website
                try:
                    elem = page.locator('a[data-item-id="authority"]').first
                    if elem.count() > 0:
                        href = elem.get_attribute('href')
                        if href and 'google.com' not in href:
                            lead_data['website'] = normalize_url(href)
                except Exception:
                    pass
                
                # Address
                try:
                    elem = page.locator('button[data-item-id="address"] .Io6YTe').first
                    if elem.count() > 0:
                        lead_data['address'] = elem.inner_text()
                except Exception:
                    pass
                
                leads.append(lead_data)
                print(f"  [{i+1}] {lead_data['business_name']}", file=sys.stderr)
                
                time.sleep(random.uniform(1, 2))
                
            except Exception as e:
                errors.append(f"Error on {i+1}: {str(e)[:50]}")
        
        return {
            "success": True,
            "leads": leads,
            "errors": errors,
            "total_found": total
        }
        
    except Exception as e:
        errors.append(f"Scraping failed: {str(e)}")
        return {"success": False, "leads": [], "errors": errors, "total_found": 0}
        
    finally:
        try:
            if browser:
                browser.close()
            if playwright:
                playwright.stop()
        except Exception:
            pass


if __name__ == "__main__":
    # Read args from command line
    if len(sys.argv) < 3:
        print(json.dumps({"success": False, "leads": [], "errors": ["Usage: worker.py <query> <location> [max_results] [headless]"], "total_found": 0}))
        sys.exit(1)
    
    query = sys.argv[1]
    location = sys.argv[2]
    max_results = int(sys.argv[3]) if len(sys.argv) > 3 else 20
    headless = sys.argv[4].lower() == 'true' if len(sys.argv) > 4 else True
    
    result = scrape_google_maps(query, location, max_results, headless)
    
    # Output JSON to stdout
    print(json.dumps(result))
