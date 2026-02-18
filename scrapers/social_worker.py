"""
Social Media Scraper Worker
Runs in a subprocess to find leads via Google X-Ray search on social platforms.
Applies stealth evasions to avoid bot-detection by Google and social platforms.
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

# ── Same stealth JS used by login_worker ──
STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
if (!window.chrome) window.chrome = {};
if (!window.chrome.runtime) window.chrome.runtime = { connect: () => {}, sendMessage: () => {} };
const origQuery = window.navigator.permissions.query.bind(window.navigator.permissions);
window.navigator.permissions.query = (params) =>
    params.name === 'notifications'
        ? Promise.resolve({ state: Notification.permission })
        : origQuery(params);
Object.defineProperty(navigator, 'plugins', {
    get: () => {
        const a = [
            { name: 'Chrome PDF Plugin',  filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
            { name: 'Chrome PDF Viewer',   filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '' },
            { name: 'Native Client',       filename: 'internal-nacl-plugin', description: '' },
        ];
        a.refresh = () => {};
        return a;
    }
});
Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
"""

MODERN_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


def _apply_stealth(context):
    """Apply stealth evasions to a browser context."""
    context.add_init_script(STEALTH_JS)
    try:
        from playwright_stealth import Stealth
        Stealth().apply_stealth_sync(context)
    except Exception:
        pass  # init-script fallback is already active


def scrape_social_search(
    query: str,
    platform: str,
    max_results: int = 20,
    headless: bool = True,
    profile_dir: str = None,
    browser_type: str = None,
) -> dict:
    """
    Search for leads on social media via Google X-Ray search.
    If headless mode hits a CAPTCHA, automatically retries with a visible browser.

    Platforms: linkedin, twitter, reddit, instagram, facebook
    """
    result = _do_google_search(query, platform, max_results, headless, profile_dir, browser_type)

    # If headless CAPTCHA, retry with visible browser
    if not result.get("success") and headless:
        has_captcha = any("captcha" in e.lower() for e in result.get("errors", []))
        if has_captcha:
            print(f"Headless CAPTCHA detected for {platform} — retrying with visible browser...", file=sys.stderr)
            result = _do_google_search(query, platform, max_results, False, profile_dir, browser_type)
            if result.get("success"):
                # Clear the original captcha error since retry worked
                result["errors"] = [e for e in result.get("errors", []) if "captcha" not in e.lower()]

    return result


def _do_google_search(
    query: str,
    platform: str,
    max_results: int,
    headless: bool,
    profile_dir: str = None,
    browser_type: str = None,
) -> dict:
    """Internal: perform a single Google X-Ray search attempt."""
    leads = []
    errors = []

    site_operators = {
        'linkedin':  'site:linkedin.com/in/',
        'twitter':   'site:x.com OR site:twitter.com',
        'reddit':    'site:reddit.com',
        'instagram': 'site:instagram.com',
        'facebook':  'site:facebook.com',
    }

    site_op = site_operators.get(platform.lower(), '')
    if not site_op:
        return {"success": False, "leads": [], "errors": [f"Unknown platform: {platform}"], "total_found": 0}

    full_query = f"{site_op} {query}"
    search_url = f"https://www.google.com/search?q={full_query.replace(' ', '+')}&num={min(max_results * 2, 40)}"

    playwright = None
    browser = None
    context = None

    try:
        print(f"Starting Playwright for {platform} search...", file=sys.stderr)
        playwright = sync_playwright().start()

        if profile_dir:
            print(f"Using saved browser profile: {profile_dir}", file=sys.stderr)
            launch_args = {
                'user_data_dir': profile_dir,
                'headless': headless,
                'args': [
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-infobars',
                    '--disable-dev-shm-usage',
                    '--lang=en-US,en',
                ],
                'viewport': {'width': 1920, 'height': 1080},
                'user_agent': MODERN_UA,
                'locale': 'en-US',
                'ignore_default_args': ['--enable-automation'],
            }
            if browser_type and browser_type.lower() in ('chrome', 'msedge'):
                launch_args['channel'] = browser_type.lower()
                print(f"Using browser channel: {browser_type}", file=sys.stderr)

            context = playwright.chromium.launch_persistent_context(**launch_args)
            _apply_stealth(context)
            page = context.pages[0] if context.pages else context.new_page()
        else:
            browser = playwright.chromium.launch(
                headless=headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-infobars',
                    '--disable-dev-shm-usage',
                ],
            )
            context = browser.new_context(
                user_agent=MODERN_UA,
                viewport={'width': 1920, 'height': 1080},
                locale='en-US',
            )
            _apply_stealth(context)
            page = context.new_page()

        # ── Human-like Google search flow ──
        # Step 1: Navigate to Google homepage first (not directly to search URL)
        print(f"Opening Google homepage...", file=sys.stderr)
        try:
            # Set consent cookie to skip cookie consent banner
            context.add_cookies([{
                'name': 'SOCS',
                'value': 'CAISHAgBEhJnd3NfMjAyNDA4MTUtMF9SQzIaAmVuIAEaBgiAo_C3Bg',
                'domain': '.google.com',
                'path': '/',
            }])
        except Exception:
            pass

        page.goto('https://www.google.com', wait_until='load', timeout=30000)
        time.sleep(random.uniform(1.5, 3.0))

        # Accept Google cookies banner if it appears
        try:
            for selector in ['button:has-text("Accept all")', 'button:has-text("I agree")', 'button:has-text("Accept")', '#L2AGLb']:
                btn = page.locator(selector)
                if btn.count() > 0:
                    btn.first.click()
                    time.sleep(random.uniform(0.5, 1.5))
                    break
        except Exception:
            pass

        # Step 2: Type the query into the search box like a human
        search_box = page.locator('textarea[name="q"], input[name="q"]').first
        if search_box.count() == 0:
            # Fallback: navigate directly if search box not found
            print(f"Search box not found, falling back to direct URL", file=sys.stderr)
            page.goto(search_url, wait_until='load', timeout=45000)
            time.sleep(random.uniform(2, 4))
        else:
            search_box.click()
            time.sleep(random.uniform(0.3, 0.8))
            # Type slowly like a human
            search_box.press_sequentially(full_query, delay=random.uniform(40, 90))
            time.sleep(random.uniform(0.5, 1.0))
            page.keyboard.press('Enter')
            print(f"Typed query: {full_query}", file=sys.stderr)

        time.sleep(random.uniform(2.0, 4.0))

        # Step 3: Check for CAPTCHA
        def _check_captcha():
            content = page.content().lower()
            captcha_keywords = [
                "verify it's you", "captcha", "unusual traffic",
                "not a robot", "recaptcha", "challenge-form",
                "verify you are a human", "before you continue",
                "detected unusual traffic",
            ]
            return any(kw in content for kw in captcha_keywords)

        if _check_captcha():
            if headless:
                errors.append(
                    "Google CAPTCHA blocked the search. "
                    "Uncheck 'Headless Mode' and try again."
                )
                return {"success": False, "leads": [], "errors": errors, "total_found": 0}
            else:
                # In visible mode, give user time to solve CAPTCHA
                print("CAPTCHA detected — waiting for user to solve it...", file=sys.stderr)
                for _ in range(60):  # wait up to 2 min
                    time.sleep(2)
                    if not _check_captcha():
                        break
                else:
                    errors.append("CAPTCHA was not solved in time.")
                    return {"success": False, "leads": [], "errors": errors, "total_found": 0}

        # Step 4: Wait for search results
        try:
            page.wait_for_selector('#search, #rso, .g', timeout=15000)
        except PlaywrightTimeout:
            if _check_captcha():
                errors.append(
                    "Google CAPTCHA blocked the search. "
                    "Uncheck 'Headless Mode' and try again."
                )
            else:
                errors.append("No results found (Google may be blocking automated searches)")
            return {"success": False, "leads": [], "errors": errors, "total_found": 0}

        # Step 5: Scroll to load more results (human-like)
        for i in range(3):
            page.keyboard.press('End')
            time.sleep(random.uniform(0.8, 1.5))

        # Parse results
        result_elements = page.locator('.g').all()
        if not result_elements:
            result_elements = page.locator('[data-header-feature]').all()

        print(f"Found {len(result_elements)} raw results", file=sys.stderr)

        for el in result_elements:
            if len(leads) >= max_results:
                break

            try:
                title_el = el.locator('h3').first
                link_el = el.locator('a').first
                snippet_el = el.locator('.VwiC3b, .IsZvec').first

                if title_el.count() == 0 or link_el.count() == 0:
                    continue

                title = title_el.inner_text()
                url = link_el.get_attribute('href')
                snippet = snippet_el.inner_text() if snippet_el.count() > 0 else ""

                if not url or 'google.com' in url:
                    continue

                lead_data = {
                    "source": f"Social - {platform.title()}",
                    "website": url,
                    "business_name": title,
                    "notes": snippet,
                }

                emails = extract_emails_from_text(snippet + " " + title)
                if emails:
                    lead_data["email"] = emails[0]

                # ── Platform-specific title parsing ──
                if platform == 'linkedin':
                    parts = title.split(' - ')
                    if len(parts) >= 2:
                        lead_data['owner_name'] = parts[0].strip()
                        lead_data['business_name'] = parts[-1].replace('| LinkedIn', '').strip()
                    elif '|' in title:
                        lead_data['owner_name'] = title.split('|')[0].strip()

                elif platform == 'twitter':
                    # "Name (@handle) / X"  or  "Name (@handle) on X"
                    m = re.match(r'^(.+?)\s*\(@?\w+\)', title)
                    if m:
                        lead_data['business_name'] = m.group(1).strip()

                elif platform == 'reddit':
                    if ':' in title:
                        lead_data['business_name'] = title.split(':')[0].strip()

                leads.append(lead_data)
                print(f"  [{len(leads)}] {lead_data['business_name']}", file=sys.stderr)

            except Exception:
                continue

        return {
            "success": True,
            "leads": leads,
            "errors": errors,
            "total_found": len(leads),
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
        print(json.dumps({
            "success": False, "leads": [], "total_found": 0,
            "errors": ["Usage: social_worker.py <query> <platform> [max_results] [headless] [--profile-dir DIR] [--browser TYPE]"],
        }))
        sys.exit(1)

    query = sys.argv[1]
    platform = sys.argv[2]
    max_results = int(sys.argv[3]) if len(sys.argv) > 3 else 20
    headless = sys.argv[4].lower() == 'true' if len(sys.argv) > 4 else True

    profile_dir = None
    browser_type = None
    for i, arg in enumerate(sys.argv):
        if arg == '--profile-dir' and i + 1 < len(sys.argv):
            profile_dir = sys.argv[i + 1]
        if arg == '--browser' and i + 1 < len(sys.argv):
            browser_type = sys.argv[i + 1]

    result = scrape_social_search(query, platform, max_results, headless, profile_dir, browser_type)
    print(json.dumps(result))
