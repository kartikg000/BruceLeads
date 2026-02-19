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

from utils.validators import validate_email, extract_emails_from_text, score_email_quality, normalize_url, validate_phone, clean_phone

# Pages to check for contact info (expanded list)
CONTACT_PAGES = [
    '/contact', '/contact-us', '/about', '/about-us', '/team',
    '/our-team', '/people', '/leadership', '/staff', '/meet-the-team',
    '/who-we-are', '/company', '/founders', '/management',
    '/get-in-touch', '/reach-us', '/connect', '/info',
    '/locations', '/hours', '/support', '/help',
]

# Phone number patterns (US-centric + international)
PHONE_PATTERNS = [
    r'\(?\d{3}\)?[\s.\-]?\d{3}[\s.\-]?\d{4}',              # (555) 123-4567, 555-123-4567, 555.123.4567
    r'\+?1?[\s.\-]?\(?\d{3}\)?[\s.\-]?\d{3}[\s.\-]?\d{4}', # +1 (555) 123-4567
    r'\d{3}[\s.\-]\d{4}',                                     # 123-4567 (local)
    r'\+\d{1,3}[\s.\-]?\d{1,4}[\s.\-]?\d{3,4}[\s.\-]?\d{3,4}',  # International
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

def _deobfuscate_emails(text: str) -> list:
    """Find obfuscated emails like 'name [at] domain [dot] com'."""
    patterns = [
        r'([a-zA-Z0-9._%+-]+)\s*\[?\s*(?:at|AT)\s*\]?\s*([a-zA-Z0-9.-]+)\s*\[?\s*(?:dot|DOT)\s*\]?\s*([a-zA-Z]{2,})',
        r'([a-zA-Z0-9._%+-]+)\s*\(at\)\s*([a-zA-Z0-9.-]+)\s*\(dot\)\s*([a-zA-Z]{2,})',
        r'([a-zA-Z0-9._%+-]+)\s*@\s*([a-zA-Z0-9.-]+)\s*\.\s*([a-zA-Z]{2,})',
    ]
    found = []
    for pat in patterns:
        for m in re.finditer(pat, text):
            email = f"{m.group(1)}@{m.group(2)}.{m.group(3)}".strip().lower()
            if validate_email(email):
                found.append(email)
    return found


def extract_phones_from_html(html: str) -> list:
    """Extract phone numbers from HTML."""
    phones = []
    try:
        soup = BeautifulSoup(html, 'html.parser')

        # 1. tel: links (most reliable)
        for link in soup.find_all('a', href=True):
            href = link['href']
            if href.startswith('tel:'):
                raw = href.replace('tel:', '').strip()
                cleaned = clean_phone(raw)
                if validate_phone(cleaned) and cleaned not in phones:
                    phones.append(cleaned)

        # 2. JSON-LD structured data
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string or '')
                items = [data] if isinstance(data, dict) else (data if isinstance(data, list) else [])
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    for key in ('telephone', 'phone', 'faxNumber'):
                        val = item.get(key)
                        if isinstance(val, str):
                            cleaned = clean_phone(val)
                            if validate_phone(cleaned) and cleaned not in phones:
                                phones.append(cleaned)
                    # contactPoint
                    cp = item.get('contactPoint')
                    cps = [cp] if isinstance(cp, dict) else (cp if isinstance(cp, list) else [])
                    for c in cps:
                        if isinstance(c, dict):
                            t = c.get('telephone', '')
                            cleaned = clean_phone(t)
                            if validate_phone(cleaned) and cleaned not in phones:
                                phones.append(cleaned)
            except Exception:
                pass

        # 3. Itemprop="telephone" elements
        for el in soup.find_all(attrs={'itemprop': re.compile(r'telephone|phone', re.I)}):
            text = el.get_text(strip=True)
            cleaned = clean_phone(text)
            if validate_phone(cleaned) and cleaned not in phones:
                phones.append(cleaned)

        # 4. Regex on visible text
        text = soup.get_text(separator=' ')
        for pattern in PHONE_PATTERNS:
            for match in re.finditer(pattern, text):
                raw = match.group(0).strip()
                cleaned = clean_phone(raw)
                if validate_phone(cleaned) and cleaned not in phones:
                    phones.append(cleaned)

    except Exception:
        pass
    return phones


def extract_emails_from_html(html: str, business_name: str = "") -> list:
    """Extract and score emails from HTML."""
    emails = extract_emails_from_text(html)
    
    try:
        soup = BeautifulSoup(html, 'html.parser')

        # mailto links
        for link in soup.find_all('a', href=True):
            href = link['href']
            if href.startswith('mailto:'):
                email = href.replace('mailto:', '').split('?')[0].strip()
                if validate_email(email) and email not in emails:
                    emails.append(email)
        
        # JSON-LD structured data
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string or '')
                items = [data] if isinstance(data, dict) else (data if isinstance(data, list) else [])
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    for key in ('email', 'contactPoint'):
                        val = item.get(key)
                        if isinstance(val, str) and validate_email(val):
                            if val not in emails:
                                emails.append(val)
                        elif isinstance(val, dict):
                            e = val.get('email', '')
                            if validate_email(e) and e not in emails:
                                emails.append(e)
                        elif isinstance(val, list):
                            for sub in val:
                                if isinstance(sub, dict):
                                    e = sub.get('email', '')
                                    if validate_email(e) and e not in emails:
                                        emails.append(e)
            except Exception:
                pass

        # Meta tags
        for meta in soup.find_all('meta'):
            content = meta.get('content', '')
            if content and '@' in content:
                found = extract_emails_from_text(content)
                for e in found:
                    if e not in emails:
                        emails.append(e)

        # Obfuscated emails in visible text
        text = soup.get_text(separator=' ')
        for e in _deobfuscate_emails(text):
            if e not in emails:
                emails.append(e)

        # itemprop="email" elements
        for el in soup.find_all(attrs={'itemprop': re.compile(r'email', re.I)}):
            txt = el.get_text(strip=True)
            if validate_email(txt) and txt not in emails:
                emails.append(txt)
                        
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


def _extract_social_links(html: str, base_url: str) -> list:
    """Extract social media profile URLs from a page (for further scraping)."""
    links = []
    try:
        soup = BeautifulSoup(html, 'html.parser')
        social_domains = ['facebook.com', 'linkedin.com', 'instagram.com', 'twitter.com', 'x.com', 'yelp.com']
        for a in soup.find_all('a', href=True):
            href = a['href']
            for domain in social_domains:
                if domain in href:
                    if href not in links:
                        links.append(href)
                    break
    except Exception:
        pass
    return links


def _discover_contact_links(html: str, base_url: str) -> list:
    """Find links on the page that likely lead to contact / about pages."""
    found = []
    keywords = ['contact', 'about', 'team', 'staff', 'people', 'leadership',
                'get-in-touch', 'reach', 'connect', 'meet', 'company']
    try:
        soup = BeautifulSoup(html, 'html.parser')
        for a in soup.find_all('a', href=True):
            href = a['href'].lower()
            text = (a.get_text(strip=True) or '').lower()
            if any(k in href or k in text for k in keywords):
                full = urljoin(base_url, a['href'])
                parsed = urlparse(full)
                base_parsed = urlparse(base_url)
                # Same domain only
                if parsed.netloc == base_parsed.netloc and full not in found:
                    found.append(full)
    except Exception:
        pass
    return found


async def enrich_single_lead(lead_data: dict, context, use_google: bool = True) -> dict:
    """Enrich a single lead (async) — find email, phone, and owner."""
    website = lead_data.get('website', '')
    business_name = lead_data.get('business_name', '')
    address = lead_data.get('address', '')
    page = await context.new_page()

    best_email = None
    best_score = 0
    best_phone = lead_data.get('phone') or ''
    owner_name = lead_data.get('owner_name') or ''
    social_links = []

    try:
        # ── Phase 1: Scrape Business Website ──────────────────
        if website:
            website = normalize_url(website)
            parsed = urlparse(website)
            base_url = f"{parsed.scheme}://{parsed.netloc}"

            # Build URL list: homepage first, then known contact paths
            check_urls = [website]
            for p in CONTACT_PAGES:
                candidate = urljoin(base_url, p)
                if candidate not in check_urls:
                    check_urls.append(candidate)

            pages_checked = 0
            for url in check_urls[:10]:  # Up to 10 pages
                try:
                    resp = await page.goto(url, wait_until='domcontentloaded', timeout=10000)
                    if resp and resp.status >= 400:
                        continue
                    await asyncio.sleep(0.5)
                    html = await page.content()
                    pages_checked += 1

                    # On homepage, discover additional contact links and social links
                    if pages_checked == 1:
                        discovered = _discover_contact_links(html, base_url)
                        for u in discovered:
                            if u not in check_urls:
                                check_urls.append(u)
                        social_links = _extract_social_links(html, base_url)

                    # Emails
                    scored = extract_emails_from_html(html, business_name)
                    if scored and scored[0][1] > best_score:
                        best_email = scored[0][0]
                        best_score = scored[0][1]

                    # Phone
                    if not best_phone:
                        phones = extract_phones_from_html(html)
                        if phones:
                            best_phone = phones[0]

                    # Owner
                    if not owner_name:
                        owner_name = extract_owner_name(html)

                    # Stop early if we have everything
                    if best_score >= 7 and owner_name and best_phone:
                        break
                except Exception:
                    continue

            if best_email:
                lead_data['email'] = best_email
            if best_phone:
                lead_data['phone'] = best_phone
            if owner_name:
                lead_data['owner_name'] = owner_name

        # ── Phase 2: Check social media pages for email/phone ──
        if (not lead_data.get('email') or not best_phone) and social_links:
            for soc_url in social_links[:3]:
                try:
                    resp = await page.goto(soc_url, wait_until='domcontentloaded', timeout=10000)
                    if resp and resp.status >= 400:
                        continue
                    await asyncio.sleep(1)
                    html = await page.content()

                    if not lead_data.get('email'):
                        scored = extract_emails_from_html(html, business_name)
                        if scored and scored[0][1] >= 4:
                            lead_data['email'] = scored[0][0]

                    if not best_phone:
                        phones = extract_phones_from_html(html)
                        if phones:
                            best_phone = phones[0]
                            lead_data['phone'] = best_phone

                    if lead_data.get('email') and best_phone:
                        break
                except Exception:
                    continue

        # ── Phase 3: Google Search (broader query set) ────────
        if use_google and (not lead_data.get('email') or not best_phone):
            # Build a list of queries from most specific to broad
            location = address.split(',')[-2].strip() if address and ',' in address else ''
            queries = []
            if not lead_data.get('email'):
                queries.append(f'"{business_name}" email contact')
                queries.append(f'"{business_name}" "@" email')
                if location:
                    queries.append(f'"{business_name}" {location} email')
                queries.append(f'site:yelp.com "{business_name}"')
                queries.append(f'site:bbb.org "{business_name}"')
                queries.append(f'"{business_name}" owner founder email')
            if not best_phone:
                queries.append(f'"{business_name}" phone number')
                if location:
                    queries.append(f'"{business_name}" {location} phone')

            for query in queries[:5]:  # Max 5 Google searches
                search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}&num=10"
                try:
                    await page.goto(search_url, wait_until='domcontentloaded', timeout=12000)
                    await asyncio.sleep(1.5 + random.random())
                    html = await page.content()

                    # Emails
                    if not lead_data.get('email'):
                        emails = extract_emails_from_text(html)
                        # Also try obfuscated
                        soup = BeautifulSoup(html, 'html.parser')
                        text = soup.get_text(separator=' ')
                        emails += _deobfuscate_emails(text)
                        scored = list({e: score_email_quality(e, business_name) for e in emails}.items())
                        scored = [x for x in scored if x[1] >= 4]
                        if scored:
                            scored.sort(key=lambda x: x[1], reverse=True)
                            lead_data['email'] = scored[0][0]

                    # Phone
                    if not best_phone:
                        phones = extract_phones_from_html(html)
                        if phones:
                            best_phone = phones[0]
                            lead_data['phone'] = best_phone

                    # Owner
                    if not lead_data.get('owner_name'):
                        owner = extract_owner_name(html)
                        if owner:
                            lead_data['owner_name'] = owner

                    # If we found both email + phone, stop searching
                    if lead_data.get('email') and best_phone:
                        break
                except Exception:
                    continue

        # ── Phase 4: Yelp / directory page scrape ─────────────
        if not lead_data.get('email') or not best_phone:
            yelp_links = [l for l in social_links if 'yelp.com' in l]
            if not yelp_links and use_google:
                # Try to find a Yelp page via Google
                try:
                    q = f'site:yelp.com "{business_name}"'
                    await page.goto(f"https://www.google.com/search?q={q.replace(' ', '+')}",
                                    wait_until='domcontentloaded', timeout=10000)
                    await asyncio.sleep(1)
                    html = await page.content()
                    soup = BeautifulSoup(html, 'html.parser')
                    for a in soup.find_all('a', href=True):
                        href = a['href']
                        if 'yelp.com/biz/' in href:
                            # Extract clean URL from Google redirect
                            if '/url?q=' in href:
                                href = href.split('/url?q=')[1].split('&')[0]
                            yelp_links.append(href)
                            break
                except Exception:
                    pass

            for yelp_url in yelp_links[:1]:
                try:
                    await page.goto(yelp_url, wait_until='domcontentloaded', timeout=12000)
                    await asyncio.sleep(1)
                    html = await page.content()

                    if not lead_data.get('email'):
                        scored = extract_emails_from_html(html, business_name)
                        if scored and scored[0][1] >= 4:
                            lead_data['email'] = scored[0][0]

                    if not best_phone:
                        phones = extract_phones_from_html(html)
                        if phones:
                            best_phone = phones[0]
                            lead_data['phone'] = best_phone
                except Exception:
                    pass

        # ── Phase 5: Owner search (if still missing) ─────────
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
