"""
Login Worker
Runs in a subprocess to open a visible browser for the user to log in.
Uses Playwright persistent context + stealth evasions so cookies are saved
to the profile directory and platforms don't flag the browser as automated.
"""

import sys
import json
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

# ── Stealth: mask navigator.webdriver + other automation fingerprints ──
# Applied via context.add_init_script() so it runs on every navigation.
STEALTH_JS = """
// 1. Hide navigator.webdriver
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

// 2. Fake Chrome runtime (missing in headless/automation mode)
if (!window.chrome) window.chrome = {};
if (!window.chrome.runtime) window.chrome.runtime = { connect: () => {}, sendMessage: () => {} };

// 3. Fix permissions.query for notifications
const origQuery = window.navigator.permissions.query.bind(window.navigator.permissions);
window.navigator.permissions.query = (params) =>
    params.name === 'notifications'
        ? Promise.resolve({ state: Notification.permission })
        : origQuery(params);

// 4. Spoof plugins array (headless Chrome reports 0 plugins)
Object.defineProperty(navigator, 'plugins', {
    get: () => {
        const arr = [
            { name: 'Chrome PDF Plugin',       filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
            { name: 'Chrome PDF Viewer',        filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '' },
            { name: 'Native Client',            filename: 'internal-nacl-plugin', description: '' },
        ];
        arr.refresh = () => {};
        return arr;
    }
});

// 5. Spoof languages
Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });

// 6. Fix broken iframe contentWindow (Playwright leaks)
try {
    const orig = HTMLIFrameElement.prototype.__lookupGetter__('contentWindow');
    if (orig) {
        Object.defineProperty(HTMLIFrameElement.prototype, 'contentWindow', {
            get: function () {
                const w = orig.call(this);
                if (w && !w.chrome) w.chrome = window.chrome;
                return w;
            }
        });
    }
} catch (_) {}
"""

# Modern user-agent (Chrome 131, late-2024 — realistic for installs through 2026)
MODERN_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

# ── Per-platform login-detection logic ──

# URL fragments that mean "the user is still on a login / challenge page"
LOGIN_PAGE_PATTERNS = [
    '/login', '/signin', '/sign-in', '/sign_in',
    '/flow/login', '/oauth', '/authorize',
    '/checkpoint/', '/challenge/', '/challengesV2/',
    '/uas/', '/register', '/signup',
    '/two_factor', '/two-factor', '/2fa',
    '/verification', '/verify', '/consent',
    '/accounts/login', '/sessions/new',
    '/deactivated',
]

# Platform-specific URLs that *prove* login succeeded
SUCCESS_PATTERNS = {
    'linkedin': ['/feed', '/mynetwork', '/messaging', '/in/', '/notifications', '/jobs', '/search/results'],
    'twitter':  ['/home', '/compose', '/notifications', '/explore', '/messages', '/i/bookmarks'],
    'reddit':   ['reddit.com/?feed=', '/r/', '/user/', 'reddit.com/best', 'reddit.com/hot', 'reddit.com/new'],
    'instagram':['/accounts/onetap', '/explore', '/direct', '/reels', '/?variant='],
    'facebook': ['/home.php', '/?sk=', '/profile.php', '/groups', '/?ref='],
}

# Platform domain(s) — used for the "generic redirect away from login" check
PLATFORM_DOMAINS = {
    'linkedin':  ['linkedin.com'],
    'twitter':   ['x.com', 'twitter.com'],
    'reddit':    ['reddit.com'],
    'instagram': ['instagram.com'],
    'facebook':  ['facebook.com'],
}


def run_login(platform: str, login_url: str, profile_dir: str, browser_type: str = "chrome") -> dict:
    """
    Open a visible browser with stealth evasions for manual login.
    The persistent context (profile_dir) saves all cookies / local-storage
    automatically so the session can be reused later.
    """
    playwright = None
    context = None

    try:
        print(f"Opening {platform.title()} login page...", file=sys.stderr)
        playwright = sync_playwright().start()

        launch_args = {
            'user_data_dir': profile_dir,
            'headless': False,
            'args': [
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--start-maximized',
                '--disable-infobars',
                '--disable-dev-shm-usage',
                '--lang=en-US,en',
            ],
            'viewport': {'width': 1280, 'height': 900},
            'user_agent': MODERN_UA,
            'locale': 'en-US',
            'ignore_default_args': ['--enable-automation'],
        }

        if browser_type.lower() in ('chrome', 'msedge'):
            launch_args['channel'] = browser_type.lower()

        context = playwright.chromium.launch_persistent_context(**launch_args)

        # Inject stealth BEFORE any navigation
        context.add_init_script(STEALTH_JS)

        # Also try the playwright-stealth library (belt & suspenders)
        try:
            from playwright_stealth import Stealth
            Stealth().apply_stealth_sync(context)
        except Exception:
            pass  # init-script fallback is already active

        page = context.pages[0] if context.pages else context.new_page()

        page.goto(login_url, wait_until='domcontentloaded', timeout=30000)

        print(f"Waiting for user to log in to {platform.title()}...", file=sys.stderr)
        print("The browser will close automatically when login is detected,", file=sys.stderr)
        print("or you can close it manually when done.", file=sys.stderr)

        login_confirmed = False
        browser_closed = False
        max_wait = 300  # 5 min
        start_time = time.time()

        platform_success = SUCCESS_PATTERNS.get(platform.lower(), [])
        platform_domains = PLATFORM_DOMAINS.get(platform.lower(), [])

        while time.time() - start_time < max_wait:
            try:
                if page.is_closed():
                    browser_closed = True
                    break

                current_url = page.url.lower()

                # A) Check for explicit success URLs
                if any(pat in current_url for pat in platform_success):
                    print(f"Login detected (success URL): {current_url}", file=sys.stderr)
                    login_confirmed = True
                    time.sleep(4)
                    break

                # B) If we are on the platform domain AND no longer on a login/challenge page
                on_platform = any(d in current_url for d in platform_domains)
                on_login_page = any(pat in current_url for pat in LOGIN_PAGE_PATTERNS)

                if on_platform and not on_login_page:
                    # Wait at least 12 s to avoid false positives (page redirects)
                    if time.time() - start_time > 12:
                        print(f"Login detected (left login page): {current_url}", file=sys.stderr)
                        login_confirmed = True
                        time.sleep(4)
                        break

            except Exception:
                browser_closed = True
                break

            time.sleep(2)

        # ── Write marker file ──
        if login_confirmed:
            marker_path = Path(profile_dir) / "login_success.json"
            with open(marker_path, 'w') as f:
                json.dump({
                    "platform": platform,
                    "timestamp": time.time(),
                    "browser": browser_type,
                }, f)
            return {"success": True, "message": f"Successfully logged in to {platform.title()}! Session saved."}

        if browser_closed:
            # If user closed browser, check if the profile has cookies
            # (they might have logged in and closed the window themselves)
            cookie_file = Path(profile_dir) / "Default" / "Cookies"
            if cookie_file.exists() and cookie_file.stat().st_size > 100:
                marker_path = Path(profile_dir) / "login_success.json"
                with open(marker_path, 'w') as f:
                    json.dump({
                        "platform": platform,
                        "timestamp": time.time(),
                        "browser": browser_type,
                        "manual_close": True,
                    }, f)
                return {"success": True, "message": f"Browser closed. Session data saved (assuming login succeeded)."}
            return {"success": False, "message": "Browser closed without confirmed login. Try again and complete the login."}

        return {"success": False, "message": "Login timed out (5 min). Please try again."}

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

    browser_type = "chrome"
    for i, arg in enumerate(sys.argv):
        if arg == '--browser' and i + 1 < len(sys.argv):
            browser_type = sys.argv[i + 1]
            break

    result = run_login(platform, login_url, profile_dir, browser_type)
    print(json.dumps(result))
