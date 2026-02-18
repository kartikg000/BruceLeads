"""
Social Media Scraper
Wrapper that runs social media scraping in a subprocess.
"""

import subprocess
import sys
import json
from typing import List, Optional, Callable
from pathlib import Path

from models import Lead, LeadSource
from utils import get_python_executable
from scrapers.session_manager import get_profile_path, get_session_status, get_session_browser


class SocialMediaScraper:
    """
    Scrapes leads from social media platforms via Google X-Ray search.
    Uses a subprocess to avoid event loop conflicts.
    """
    
    def __init__(
        self,
        headless: bool = True,
        max_results: int = 20
    ):
        self.headless = headless
        self.max_results = max_results
    
    def search_sync(
        self,
        query: str,
        platform: str,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> dict:
        """
        Search social media.
        """
        worker_path = Path(__file__).parent / "social_worker.py"
        
        if not worker_path.exists():
            return {"success": False, "leads": [], "errors": ["Worker not found"]}
        
        cmd = get_python_executable() + [
            str(worker_path),
            query,
            platform,
            str(self.max_results),
            str(self.headless).lower()
        ]
        
        # If user has a saved browser profile for this platform, use it
        if get_session_status(platform) == "logged_in":
            profile_path = get_profile_path(platform)
            browser_type = get_session_browser(platform)
            cmd.extend(['--profile-dir', str(profile_path)])
            cmd.extend(['--browser', browser_type])
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                cwd=str(Path(__file__).parent.parent)
            )
            
            stdout_lines = result.stdout.strip().split('\n')
            if not stdout_lines:
                return {"success": False, "leads": [], "errors": [f"No output: {result.stderr[:200]}"]}
            
            try:
                data = json.loads(stdout_lines[-1])
            except json.JSONDecodeError:
                return {"success": False, "leads": [], "errors": ["Invalid JSON output"]}
            
            # Convert to Lead objects
            leads = []
            for item in data.get('leads', []):
                lead = Lead(
                    business_name=item.get('business_name', ''),
                    source=item.get('source', 'Social Media'),
                    website=item.get('website', ''),
                    email=item.get('email'),
                    owner_name=item.get('owner_name'),
                    notes=item.get('notes')
                )
                leads.append(lead)
            
            return {
                "success": data.get("success", False),
                "leads": leads,
                "errors": data.get("errors", []),
                "total_found": data.get("total_found", 0)
            }
            
        except Exception as e:
            return {"success": False, "leads": [], "errors": [str(e)]}
