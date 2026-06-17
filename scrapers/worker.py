"""
Google Maps Scraper Worker  (async, multi-tab)
Standalone script that runs Playwright scraping in a separate process.
Uses up to CONCURRENCY browser tabs in parallel for speed.
"""

import sys
import json
import asyncio
import random
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
import config
from models import Lead, LeadSource
from utils import clean_business_name, normalize_url

# Max concurrent tabs for visiting place pages (overridden via CLI)
CONCURRENCY = 10

# Stealth JS — masks navigator.webdriver and other automation signals
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
    "Chrome/133.0.0.0 Safari/537.36"
)


# ── helpers ────────────────────────────────────────────────────


async def _extract_place(page, url: str, index: int, total: int) -> dict | None:
    """Visit a single Google Maps place URL and extract business data."""
    try:
        print(f"Processing {index + 1}/{total}...", file=sys.stderr)
        await page.goto(url, wait_until='domcontentloaded', timeout=15000)
        await asyncio.sleep(random.uniform(config.SCRAPE_MIN_DELAY, config.SCRAPE_MAX_DELAY))

        lead_data = {"source": LeadSource.GOOGLE_MAPS.value}

        # Business name
        for selector in ['h1', '.DUwDvf']:
            try:
                elem = page.locator(selector).first
                if await elem.count() > 0:
                    text = await elem.inner_text()
                    if text and len(text) > 1:
                        lead_data['business_name'] = clean_business_name(text)
                        break
            except Exception:
                continue

        if not lead_data.get('business_name'):
            return None

        # Phone
        try:
            for selector in ['button[data-item-id*="phone"] .Io6YTe', 'a[href^="tel:"]']:
                elem = page.locator(selector).first
                if await elem.count() > 0:
                    if 'href' in selector:
                        href = await elem.get_attribute('href')
                        if href:
                            lead_data['phone'] = href.replace('tel:', '')
                    else:
                        lead_data['phone'] = await elem.inner_text()
                    if lead_data.get('phone'):
                        break
        except Exception:
            pass

        # Website
        try:
            elem = page.locator('a[data-item-id="authority"]').first
            if await elem.count() > 0:
                href = await elem.get_attribute('href')
                if href and 'google.com' not in href:
                    lead_data['website'] = normalize_url(href)
        except Exception:
            pass

        # Address
        try:
            elem = page.locator('button[data-item-id="address"] .Io6YTe').first
            if await elem.count() > 0:
                lead_data['address'] = await elem.inner_text()
        except Exception:
            pass

        print(f"  [{index + 1}] {lead_data['business_name']}", file=sys.stderr)
        return lead_data

    except Exception as e:
        print(f"  Error on {index + 1}: {str(e)[:80]}", file=sys.stderr)
        return None


# ── main scraper ───────────────────────────────────────────────


async def _extract_from_panel(page) -> dict | None:
    """Extract business data from the currently open place detail panel."""
    lead_data = {"source": LeadSource.GOOGLE_MAPS.value}

    try:
        # Business name — from the detail panel header
        for selector in ['h1.DUwDvf', 'h1', 'div.tAiQdd h1', '[data-attrid="title"]']:
            try:
                elem = page.locator(selector).first
                if await elem.count() > 0:
                    text = await elem.inner_text()
                    if text and len(text.strip()) > 1:
                        lead_data['business_name'] = clean_business_name(text.strip())
                        break
            except Exception:
                continue

        if not lead_data.get('business_name'):
            return None

        # Phone
        try:
            phone_selectors = [
                'button[data-item-id*="phone"] .Io6YTe',
                'button[data-tooltip*="phone"] .Io6YTe',
                'a[href^="tel:"]',
                '[data-item-id*="phone"]',
            ]
            for selector in phone_selectors:
                elem = page.locator(selector).first
                if await elem.count() > 0:
                    if 'href' in selector:
                        href = await elem.get_attribute('href')
                        if href:
                            lead_data['phone'] = href.replace('tel:', '')
                    else:
                        lead_data['phone'] = (await elem.inner_text()).strip()
                    if lead_data.get('phone'):
                        break
        except Exception:
            pass

        # Website
        try:
            website_selectors = [
                'a[data-item-id="authority"]',
                'a[data-tooltip*="website"]',
                'a[aria-label*="website" i]',
            ]
            for selector in website_selectors:
                elem = page.locator(selector).first
                if await elem.count() > 0:
                    href = await elem.get_attribute('href')
                    if href and 'google.com' not in href:
                        lead_data['website'] = normalize_url(href)
                        break
        except Exception:
            pass

        # Address
        try:
            addr_selectors = [
                'button[data-item-id="address"] .Io6YTe',
                'button[data-tooltip*="address"] .Io6YTe',
                '[data-item-id="address"]',
            ]
            for selector in addr_selectors:
                elem = page.locator(selector).first
                if await elem.count() > 0:
                    lead_data['address'] = (await elem.inner_text()).strip()
                    if lead_data['address']:
                        break
        except Exception:
            pass

        return lead_data

    except Exception as e:
        print(f"  Panel extraction error: {str(e)[:80]}", file=sys.stderr)
        return None


# ── main scraper ───────────────────────────────────────────────


async def scrape_google_maps(
    query: str, location: str, max_results: int = 20, headless: bool = True
) -> dict:
    """
    Scrape Google Maps search results.
    
    Strategy:
      Phase 1 — Navigate to Maps search, scroll the results feed.
      Phase 2a — If classic /maps/place/ links are found, open them in parallel tabs.
      Phase 2b — If no place links (new Maps layout), click each listing in the
                 feed sequentially and extract from the detail panel.
    """
    leads = []
    errors = []

    full_query = f"{query} in {location}" if location else query
    search_url = f"https://www.google.com/maps/search/{full_query.replace(' ', '+')}"

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=headless,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox',
                  '--disable-infobars', '--disable-dev-shm-usage'],
        )
        context = await browser.new_context(
            user_agent=MODERN_UA,
            viewport={'width': 1920, 'height': 1080},
            locale='en-US',
        )

        # Apply stealth evasions
        await context.add_init_script(STEALTH_JS)
        try:
            from playwright_stealth import Stealth
            await Stealth().apply_stealth_async(context)
        except Exception:
            pass  # init-script fallback is already active

        # ── Phase 1: search + scroll ─────────────────────────────
        page = await context.new_page()
        print(f"Navigating to: {search_url}", file=sys.stderr)
        await page.goto(search_url, wait_until='load', timeout=45000)
        # Short pause after load — use runtime-configured scrape delays
        await asyncio.sleep(random.uniform(config.SCRAPE_MIN_DELAY, config.SCRAPE_MAX_DELAY))

        # Accept cookies / consent banners
        try:
            consent_selectors = [
                'button:has-text("Accept all")',
                'button:has-text("I agree")',
                'button:has-text("Accept")',
                'button:has-text("Reject all")',
                'form[action*="consent"] button',
                '#L2AGLb',
                'button[aria-label="Accept all"]',
            ]
            for sel in consent_selectors:
                btn = page.locator(sel)
                if await btn.count() > 0:
                    await btn.first.click()
                    print(f"Clicked consent button: {sel}", file=sys.stderr)
                    await asyncio.sleep(random.uniform(config.SCRAPE_MIN_DELAY, config.SCRAPE_MAX_DELAY))
                    break
        except Exception:
            pass

        # Check if redirected to a single place page
        if '/maps/place/' in page.url:
            print("Redirected to a single place page — extracting directly", file=sys.stderr)
            result = await _extract_from_panel(page)
            await browser.close()
            if result:
                return {"success": True, "leads": [result], "errors": [], "total_found": 1}
            return {"success": False, "leads": [], "errors": ["Could not extract from place page"], "total_found": 0}

        # Wait for the results feed
        feed_selectors = [
            '[role="feed"]',
            'div[aria-label*="Results for"]',
            '.m6QErb[aria-label]',
            'div.m6QErb.DxyBCb',
        ]
        
        feed_found = False
        feed_selector_used = None
        for sel in feed_selectors:
            try:
                await page.wait_for_selector(sel, timeout=8000)
                feed_found = True
                feed_selector_used = sel
                print(f"Found results feed via: {sel}", file=sys.stderr)
                break
            except PlaywrightTimeout:
                continue

        if not feed_found:
            await asyncio.sleep(random.uniform(config.SCRAPE_MIN_DELAY, config.SCRAPE_MAX_DELAY))
            # Last check for any feed content
            for sel in feed_selectors:
                if await page.locator(sel).count() > 0:
                    feed_found = True
                    feed_selector_used = sel
                    break
            
            if not feed_found:
                try:
                    debug_path = str(Path(__file__).parent.parent / "data" / "debug_maps.png")
                    await page.screenshot(path=debug_path)
                    print(f"Debug screenshot saved to {debug_path}", file=sys.stderr)
                except Exception:
                    pass
                errors.append("Could not find results - Google Maps may have changed or is blocking the request. Try unchecking 'Run in background'.")
                await browser.close()
                return {"success": False, "leads": [], "errors": errors, "total_found": 0}

        await asyncio.sleep(random.uniform(config.SCRAPE_MIN_DELAY, config.SCRAPE_MAX_DELAY))

        # Scroll the feed to load more results
        try:
            container = page.locator(feed_selector_used).first
            if await container.count() > 0:
                scroll_count = max(5, (max_results // 3) + 3)
                prev_items = 0
                stall_count = 0
                for i in range(scroll_count):
                    await container.evaluate('node => node.scrollTop = node.scrollHeight')
                    await asyncio.sleep(random.uniform(config.SCRAPE_MIN_DELAY, config.SCRAPE_MAX_DELAY))
                    
                    # Count listing items in the feed
                    cur_items = await page.locator(f'{feed_selector_used} > div > div > a, {feed_selector_used} > div > a').count()
                    if cur_items == 0:
                        # Fallback: count any clickable items
                        cur_items = await page.locator(f'{feed_selector_used} a[aria-label]').count()

                    if cur_items >= max_results:
                        break
                    if cur_items == prev_items:
                        stall_count += 1
                        if stall_count >= 3 and i >= 4:
                            break
                    else:
                        stall_count = 0
                    prev_items = cur_items
                print(f"After scrolling: ~{prev_items} items visible", file=sys.stderr)
        except Exception as e:
            print(f"Scroll error: {e}", file=sys.stderr)

        # ── Check for classic /maps/place/ links (Phase 2a) ──────
        classic_links = await page.locator('a[href*="/maps/place/"]').all()
        if classic_links:
            seen = set()
            unique_urls = []
            for link in classic_links:
                try:
                    href = await link.get_attribute('href')
                    if href and '/maps/place/' in href:
                        base = href.split('?')[0]
                        if base not in seen:
                            seen.add(base)
                            unique_urls.append(href)
                except Exception:
                    continue

            unique_urls = unique_urls[:max_results]
            total = len(unique_urls)
            
            if total > 0:
                print(f"Classic mode: found {total} place URLs — extracting with {CONCURRENCY} tabs", file=sys.stderr)
                await page.close()

                sem = asyncio.Semaphore(CONCURRENCY)

                async def _tab_task(idx: int, url: str):
                    async with sem:
                        tab = await context.new_page()
                        try:
                            return await _extract_place(tab, url, idx, total)
                        finally:
                            await tab.close()
                            await asyncio.sleep(random.uniform(max(0.1, config.SCRAPE_MIN_DELAY/5), max(0.3, config.SCRAPE_MIN_DELAY/2)))

                results = await asyncio.gather(
                    *[_tab_task(i, u) for i, u in enumerate(unique_urls)]
                )
                leads = [r for r in results if r is not None]
                await browser.close()
                return {"success": True, "leads": leads, "errors": errors, "total_found": total}

        # ── Phase 2b: Click-through mode (new Maps layout) ───────
        # Google Maps no longer embeds /maps/place/ links in the feed.
        # Instead, click each listing to open the detail panel and extract.
        print("Using click-through extraction (new Maps layout)...", file=sys.stderr)

        # Find clickable listing items in the feed
        listing_selectors = [
            f'{feed_selector_used} a[aria-label]',
            f'{feed_selector_used} > div > div > a',
            '.m6QErb a[aria-label]',
            '.Nv2PK',  # Google Maps card class
        ]
        
        listing_elements = []
        for sel in listing_selectors:
            found = await page.locator(sel).all()
            if found:
                print(f"Found {len(found)} listing items via: {sel}", file=sys.stderr)
                listing_elements = found
                break

        if not listing_elements:
            # Fallback: try to find any elements with business-like aria labels
            all_labeled = await page.locator('[aria-label]').all()
            for el in all_labeled:
                try:
                    label = await el.get_attribute('aria-label')
                    tag = await el.evaluate('el => el.tagName.toLowerCase()')
                    if label and tag == 'a' and len(label) > 3:
                        # Filter out non-listing items
                        skip_keywords = ['search', 'menu', 'google', 'directions', 'zoom', 'layers', 'map']
                        if not any(kw in label.lower() for kw in skip_keywords):
                            listing_elements.append(el)
                except Exception:
                    continue
            if listing_elements:
                print(f"Found {len(listing_elements)} listings via aria-label fallback", file=sys.stderr)

        total = min(len(listing_elements), max_results)
        if total == 0:
            try:
                debug_path = str(Path(__file__).parent.parent / "data" / "debug_maps_noresults.png")
                await page.screenshot(path=debug_path, full_page=True)
                print(f"Debug screenshot: {debug_path}", file=sys.stderr)
            except Exception:
                pass
            errors.append("No results found for this search")
            await browser.close()
            return {"success": False, "leads": [], "errors": errors, "total_found": 0}

        print(f"Extracting {total} listings via click-through...", file=sys.stderr)

        prev_name = None  # track last extracted name to detect stale panels
        for i in range(total):
            try:
                # Re-fetch listing elements each time (DOM may have changed after back-nav)
                current_listings = []
                for sel in listing_selectors:
                    current_listings = await page.locator(sel).all()
                    if current_listings:
                        break
                
                if i >= len(current_listings):
                    print(f"  Only {len(current_listings)} listings available, stopping at {i}", file=sys.stderr)
                    break

                el = current_listings[i]
                
                # Get the aria-label which usually contains the business name
                aria_label = None
                try:
                    aria_label = await el.get_attribute('aria-label')
                except Exception:
                    pass
                
                print(f"Clicking listing {i + 1}/{total} [{aria_label or '?'}]...", file=sys.stderr)
                
                # Scroll element into view, then click
                try:
                    await el.scroll_into_view_if_needed()
                    await asyncio.sleep(random.uniform(max(0.05, config.SCRAPE_MIN_DELAY/10), max(0.3, config.SCRAPE_MIN_DELAY/3)))
                except Exception:
                    pass
                await el.click()
                await asyncio.sleep(random.uniform(config.SCRAPE_MIN_DELAY, config.SCRAPE_MAX_DELAY))

                # Wait for the detail panel h1 to appear (and be different from previous)
                detail_ready = False
                for _wait in range(6):
                    try:
                        h1 = page.locator('h1.DUwDvf').first
                        if await h1.count() > 0:
                            name = (await h1.inner_text()).strip()
                            if name and name != prev_name:
                                detail_ready = True
                                break
                    except Exception:
                        pass
                    await asyncio.sleep(random.uniform(max(0.1, config.SCRAPE_MIN_DELAY/5), max(0.5, config.SCRAPE_MIN_DELAY/2)))
                
                if not detail_ready:
                    # Maybe the panel loaded but name didn't change (same name listing)
                    await asyncio.sleep(random.uniform(max(0.2, config.SCRAPE_MIN_DELAY/4), max(0.8, config.SCRAPE_MIN_DELAY)))

                # Extract data from the panel
                result = await _extract_from_panel(page)
                if result:
                    prev_name = result.get('business_name')
                    # Deduplicate by business name
                    if not any(l.get('business_name') == result['business_name'] for l in leads):
                        leads.append(result)
                        print(f"  [{len(leads)}] {result['business_name']} | {result.get('phone','-')} | {result.get('website','-')}", file=sys.stderr)
                else:
                    # Use aria-label as fallback for business name
                    if aria_label:
                        fallback = {"source": LeadSource.GOOGLE_MAPS.value, "business_name": clean_business_name(aria_label)}
                        if not any(l.get('business_name') == fallback['business_name'] for l in leads):
                            leads.append(fallback)
                            print(f"  [{len(leads)}] {fallback['business_name']} (name only, from aria-label)", file=sys.stderr)

                # Go back to the list — try back button, escape, then browser back
                navigated_back = False
                back_btn = page.locator('button[aria-label="Back"]').first
                if await back_btn.count() > 0:
                    await back_btn.click()
                    navigated_back = True
                
                if not navigated_back:
                    await page.keyboard.press('Escape')
                
                # Wait for the feed to be visible again before next click
                await asyncio.sleep(random.uniform(max(0.2, config.SCRAPE_MIN_DELAY/4), max(0.8, config.SCRAPE_MIN_DELAY)))
                try:
                    await page.wait_for_selector(feed_selector_used, timeout=4000)
                except PlaywrightTimeout:
                    # Feed might still be there, just try continuing
                    await asyncio.sleep(random.uniform(max(0.2, config.SCRAPE_MIN_DELAY/4), max(0.8, config.SCRAPE_MIN_DELAY)))

            except Exception as e:
                print(f"  Error on listing {i + 1}: {str(e)[:80]}", file=sys.stderr)
                # Try to recover
                try:
                    await page.keyboard.press('Escape')
                    await asyncio.sleep(random.uniform(max(0.2, config.SCRAPE_MIN_DELAY/4), max(0.8, config.SCRAPE_MIN_DELAY)))
                except Exception:
                    pass

        await browser.close()

    return {
        "success": len(leads) > 0,
        "leads": leads,
        "errors": errors,
        "total_found": len(leads),
    }


# ── CLI entry-point ────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(json.dumps({
            "success": False, "leads": [], "total_found": 0,
            "errors": ["Usage: worker.py <query> <location> [max_results] [headless] [concurrency]"],
        }))
        sys.exit(1)

    query = sys.argv[1]
    location = sys.argv[2]
    max_results = int(sys.argv[3]) if len(sys.argv) > 3 else 20
    headless = sys.argv[4].lower() == 'true' if len(sys.argv) > 4 else True

    if len(sys.argv) > 5:
        try:
            CONCURRENCY = max(1, min(20, int(sys.argv[5])))
        except ValueError:
            pass

    try:
        result = asyncio.run(scrape_google_maps(query, location, max_results, headless))
        print(json.dumps(result))
    except Exception as e:
        print(json.dumps({
            "success": False, "leads": [], "total_found": 0,
            "errors": [f"Worker crashed: {str(e)}"],
        }))
