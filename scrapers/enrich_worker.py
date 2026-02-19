"""
Lead Enrichment Worker (Async)
Runs in a subprocess to find emails from business websites and web search.
"""

import sys
import json
import asyncio
import random
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

sys.path.insert(0, str(Path(__file__).parent.parent))

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from bs4 import BeautifulSoup

from utils.validators import validate_email, extract_emails_from_text, score_email_quality, normalize_url

# Pages to check for contact info (expanded list)
CONTACT_PAGES = [
    '/contact', '/contact-us', '/about', '/about-us', '/team',
    '/our-team', '/people', '/leadership', '/staff', '/meet-the-team',
    '/who-we-are', '/company', '/founders', '/management',
]

# Patterns for owner names (expanded)
OWNER_PATTERNS = [
    r'(?:CEO|Founder|Co-Founder|Owner|President|Director|Principal|Managing\s+Director)[:\s]+([A-Z][a-z]+ (?:[A-Z]\.?\s)?[A-Z][a-z]+)',
    r'([A-Z][a-z]+ (?:[A-Z]\.?\s)?[A-Z][a-z]+)[,\s]+(?:CEO|Founder|Co-Founder|Owner|President|Director|Principal)',
    r'(?:Meet|About)\s+([A-Z][a-z]+ [A-Z][a-z]+)[,\s]*(?:the\s+)?(?:founder|owner|ceo|president)',
    r'(?:Founded|Started|Created|Established)\s+by\s+([A-Z][a-z]+ [A-Z][a-z]+)',
    r'<(?:h[1-3]|strong|b)[^>]*>\s*([A-Z][a-z]+ [A-Z][a-z]+)\s*</(?:h[1-3]|strong|b)>\s*.*?(?:Founder|Owner|CEO|President)',
]

# Max concurrent tabs — overridden via CLI arg or config
CONCURRENCY = 3

def extract_emails_from_html(html: str, business_name: str = "") -> list:
    """Extract and score emails from HTML."""
    emails = extract_emails_from_text(html)
    
    # Check mailto links
    try:
        soup = BeautifulSoup(html, 'html.parser')
        for link in soup.find_all('a', href=True):
            href = link['href']
            if href.startswith('mailto:'):
                email = href.replace('mailto:', '').split('?')[0].strip()
                if validate_email(email) and email not in emails:
                    emails.append(email)
        
        # Check structured data (JSON-LD) for emails
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                import json as _json
                data = _json.loads(script.string or '')
                if isinstance(data, dict):
                    for key in ('email', 'contactPoint'):
                        val = data.get(key)
                        if isinstance(val, str) and validate_email(val):
                            if val not in emails:
                                emails.append(val)
                        elif isinstance(val, dict):
                            e = val.get('email', '')
                            if validate_email(e) and e not in emails:
                                emails.append(e)
                        elif isinstance(val, list):
                            for item in val:
                                if isinstance(item, dict):
                                    e = item.get('email', '')
                                    if validate_email(e) and e not in emails:
                                        emails.append(e)
            except Exception:
                pass
        
        # Check meta tags for contact info
        for meta in soup.find_all('meta'):
            content = meta.get('content', '')
            if content and '@' in content:
                found = extract_emails_from_text(content)
                for e in found:
                    if e not in emails:
                        emails.append(e)
                        
    except Exception:
        pass
    
    # Score emails
    scored = [(email, score_email_quality(email, business_name)) for email in emails]
    return sorted(scored, key=lambda x: x[1], reverse=True)


def extract_owner_name(html: str) -> str:
    """Try to find owner/founder name from HTML."""
    try:
        soup = BeautifulSoup(html, 'html.parser')
        text = soup.get_text(separator=' ')
        
        # Try structured data first (most reliable)
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                import json as _json
                data = _json.loads(script.string or '')
                if isinstance(data, dict):
                    # Check for founder/owner in structured data
                    for key in ('founder', 'author', 'employee'):
                        person = data.get(key)
                        if isinstance(person, dict):
                            name = person.get('name', '')
                            if name and 1 < len(name.split()) <= 4:
                                return name
                        elif isinstance(person, list) and person:
                            name = person[0].get('name', '') if isinstance(person[0], dict) else ''
                            if name and 1 < len(name.split()) <= 4:
                                return name
            except Exception:
                pass
        
        # Try regex patterns on page text
        for pattern in OWNER_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                # Validate: 2-4 words, starts with uppercase
                words = name.split()
                if 1 < len(words) <= 4 and all(w[0].isupper() for w in words if w):
                    return name
        
        # Look for title-based headings (e.g., "John Smith, Owner" in headers)
        for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'strong', 'b']):
            heading_text = heading.get_text(strip=True)
            for title_word in ['Founder', 'Owner', 'CEO', 'President', 'Director', 'Principal']:
                if title_word.lower() in heading_text.lower():
                    # Extract the name part
                    name_match = re.search(r'([A-Z][a-z]+ (?:[A-Z]\.?\s)?[A-Z][a-z]+)', heading_text)
                    if name_match:
                        return name_match.group(1).strip()
                        
    except Exception:
        pass
    return ""


async def enrich_single_lead(lead_data: dict, context, use_google: bool = True) -> dict:
    """Enrich a single lead (async)."""
    website = lead_data.get('website', '')
    business_name = lead_data.get('business_name', '')
    page = await context.new_page()
    
    try:
        # 1. Try Website — check main page + contact/about/team pages
        if website:
            website = normalize_url(website)
            parsed = urlparse(website)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            
            best_email = None
            best_score = 0
            owner_name = ""
            
            # Build list: homepage first, then contact-style pages
            check_urls = [website]
            for p in CONTACT_PAGES:
                candidate = urljoin(base_url, p)
                if candidate not in check_urls:
                    check_urls.append(candidate)
            
            for url in check_urls[:6]:  # Check up to 6 pages
                try:
                    resp = await page.goto(url, wait_until='domcontentloaded', timeout=10000)
                    if resp and resp.status >= 400:
                        continue
                    # Wait briefly for dynamic content
                    await asyncio.sleep(0.5)
                    html = await page.content()
                    
                    # Emails
                    scored = extract_emails_from_html(html, business_name)
                    if scored and scored[0][1] > best_score:
                        best_email = scored[0][0]
                        best_score = scored[0][1]
                    
                    # Owner
                    if not owner_name:
                        owner_name = extract_owner_name(html)
                        
                    # Stop early if we have a good email AND owner
                    if best_score >= 7 and owner_name:
                        break
                except Exception:
                    continue
            
            if best_email:
                lead_data['email'] = best_email
            if owner_name:
                lead_data['owner_name'] = owner_name

        # 2. Google Search Fallback (only if no email found from website)
        if not lead_data.get('email') and use_google:
            # Try multiple search queries
            queries = [
                f'"{business_name}" email contact',
                f'"{business_name}" owner founder email',
            ]
            if lead_data.get('address'):
                queries[0] += f' {lead_data["address"]}'
            
            for query in queries[:2]:
                search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
                try:
                    await page.goto(search_url, wait_until='domcontentloaded', timeout=12000)
                    await asyncio.sleep(1)
                    html = await page.content()
                    
                    # Extract emails from search results
                    emails = extract_emails_from_text(html)
                    scored = [(e, score_email_quality(e, business_name)) for e in emails]
                    scored = [x for x in scored if x[1] >= 4]
                    if scored:
                        scored.sort(key=lambda x: x[1], reverse=True)
                        lead_data['email'] = scored[0][0]
                        break
                    
                    # Also try to find owner name from search results
                    if not lead_data.get('owner_name'):
                        owner = extract_owner_name(html)
                        if owner:
                            lead_data['owner_name'] = owner
                except Exception:
                    continue

        # 3. Try to find owner from Google if still missing
        if not lead_data.get('owner_name') and use_google:
            try:
                query = f'"{business_name}" owner OR founder OR CEO'
                search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
                await page.goto(search_url, wait_until='domcontentloaded', timeout=10000)
                await asyncio.sleep(1)
                html = await page.content()
                owner = extract_owner_name(html)
                if owner:
                    lead_data['owner_name'] = owner
            except Exception:
                pass

    except Exception as e:
        print(f"Error enriching {business_name}: {e}", file=sys.stderr)
    finally:
        await page.close()
    
    return lead_data


async def enrich_leads_async(leads_json: str, headless: bool = True, use_google: bool = True) -> dict:
    """Enrich multiple leads concurrently."""
    leads = json.loads(leads_json)
    enriched_results = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless, args=['--no-sandbox'])
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        
        # Semaphore to limit concurrency
        sem = asyncio.Semaphore(CONCURRENCY)
        
        async def sem_task(lead):
            async with sem:
                print(f"Enriching: {lead.get('business_name')}", file=sys.stderr)
                result = await enrich_single_lead(lead, context, use_google)
                return result

        tasks = [sem_task(lead) for lead in leads]
        enriched_results = await asyncio.gather(*tasks)
        
        await browser.close()
    
    return {
        "success": True,
        "leads": enriched_results,
        "errors": [],
        "enriched_count": len([l for l in enriched_results if l.get('email')])
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"success": False, "leads": [], "errors": ["Usage: enrich_worker.py <leads_json>"]}))
        sys.exit(1)
    
    leads_json = sys.argv[1]
    headless = sys.argv[2].lower() == 'true' if len(sys.argv) > 2 else True
    use_google = sys.argv[3].lower() == 'true' if len(sys.argv) > 3 else True
    
    # Override concurrency from CLI arg (passed by enrichment.py wrapper)
    if len(sys.argv) > 4:
        try:
            CONCURRENCY = max(1, min(10, int(sys.argv[4])))
        except ValueError:
            pass
    
    try:
        # Run async loop
        result = asyncio.run(enrich_leads_async(leads_json, headless, use_google))
        print(json.dumps(result))
    except Exception as e:
        print(json.dumps({"success": False, "leads": [], "errors": [str(e)]}))
