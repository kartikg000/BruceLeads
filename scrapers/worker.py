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


# ── helpers ────────────────────────────────────────────────────


async def _extract_place(page, url: str, index: int, total: int) -> dict | None:
    """Visit a single Google Maps place URL and extract business data."""
    try:
        print(f"Processing {index + 1}/{total}...", file=sys.stderr)
        await page.goto(url, wait_until='domcontentloaded', timeout=15000)
        await asyncio.sleep(1.2)

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


async def scrape_google_maps(
    query: str, location: str, max_results: int = 20, headless: bool = True
) -> dict:
    """Scrape Google Maps with parallel tab extraction."""
    leads = []
    errors = []

    full_query = f"{query} in {location}" if location else query
    search_url = f"https://www.google.com/maps/search/{full_query.replace(' ', '+')}"

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=headless,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox'],
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={'width': 1920, 'height': 1080},
            locale='en-US',
        )

        # ── Phase 1: search + scroll (sequential, one page) ──────
        page = await context.new_page()
        print(f"Navigating to: {search_url}", file=sys.stderr)
        await page.goto(search_url, wait_until='load', timeout=45000)
        await asyncio.sleep(3)

        # Accept cookies
        try:
            for sel in ['button:has-text("Accept all")', 'button:has-text("I agree")']:
                btn = page.locator(sel)
                if await btn.count() > 0:
                    await btn.first.click()
                    await asyncio.sleep(1)
                    break
        except Exception:
            pass

        try:
            await page.wait_for_selector('[role="feed"]', timeout=10000)
        except PlaywrightTimeout:
            errors.append("Could not find results - try a different search")
            await browser.close()
            return {"success": False, "leads": [], "errors": errors, "total_found": 0}

        await asyncio.sleep(2)

        # Scroll to load more results
        try:
            container = page.locator('[role="feed"]').first
            if await container.count() > 0:
                for _ in range(5):
                    await container.evaluate('node => node.scrollTop = node.scrollHeight')
                    await asyncio.sleep(1)
        except Exception:
            pass

        # Collect unique place URLs
        links = await page.locator('a[href*="/maps/place/"]').all()
        seen = set()
        unique_urls = []
        for link in links:
            try:
                href = await link.get_attribute('href')
                if href and '/maps/place/' in href:
                    base = href.split('?')[0]
                    if base not in seen:
                        seen.add(base)
                        unique_urls.append(href)
            except Exception:
                continue

        await page.close()  # done with search page

        unique_urls = unique_urls[:max_results]
        total = len(unique_urls)

        if total == 0:
            errors.append("No results found for this search")
            await browser.close()
            return {"success": False, "leads": [], "errors": errors, "total_found": 0}

        print(f"Found {total} results — extracting with {CONCURRENCY} tabs", file=sys.stderr)

        # ── Phase 2: visit each place in parallel tabs ────────────
        sem = asyncio.Semaphore(CONCURRENCY)

        async def _tab_task(idx: int, url: str):
            async with sem:
                tab = await context.new_page()
                try:
                    return await _extract_place(tab, url, idx, total)
                finally:
                    await tab.close()
                    # tiny stagger to avoid hammering
                    await asyncio.sleep(random.uniform(0.2, 0.6))

        results = await asyncio.gather(
            *[_tab_task(i, u) for i, u in enumerate(unique_urls)]
        )

        leads = [r for r in results if r is not None]
        await browser.close()

    return {
        "success": True,
        "leads": leads,
        "errors": errors,
        "total_found": total,
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
