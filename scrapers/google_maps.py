"""
Google Maps Scraper
Wrapper that runs Playwright in a subprocess to avoid event loop issues.
"""

import subprocess
import sys
import json
from typing import List, Optional, Callable
from dataclasses import dataclass
from pathlib import Path

from models import Lead, LeadSource
from utils import get_python_executable
import config


@dataclass
class ScrapingResult:
    """Result of a scraping operation."""
    leads: List[Lead]
    total_found: int
    errors: List[str]
    success: bool


class GoogleMapsScraper:
    """
    Scrapes business information from Google Maps search results.
    Uses a subprocess to avoid Playwright event loop conflicts.
    """
    
    def __init__(
        self,
        headless: bool = True,
        max_results: int = None
    ):
        self.headless = headless
        self.max_results = max_results or 20
    
    def search_sync(
        self,
        query: str,
        location: str = "",
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> ScrapingResult:
        """
        Search Google Maps and extract businesses.
        Runs Playwright in a separate subprocess for Windows compatibility.
        """
        # Get path to worker script
        worker_path = Path(__file__).parent / "worker.py"
        
        if not worker_path.exists():
            return ScrapingResult(
                leads=[],
                total_found=0,
                errors=[f"Worker script not found: {worker_path}"],
                success=False
            )
        
        # Build command
        cmd = get_python_executable() + [
            str(worker_path),
            query,
            location,
            str(self.max_results),
            str(self.headless).lower(),
            str(getattr(config, 'MAX_CONCURRENT_BROWSERS', 10)),
        ]
        
        try:
            # Run scraper in subprocess
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                cwd=str(Path(__file__).parent.parent)  # Project root
            )
            
            # Parse output (last line should be JSON)
            stdout_lines = result.stdout.strip().split('\n')
            if not stdout_lines:
                return ScrapingResult(
                    leads=[],
                    total_found=0,
                    errors=[f"No output from worker. stderr: {result.stderr[:500]}"],
                    success=False
                )
            
            try:
                data = json.loads(stdout_lines[-1])
            except json.JSONDecodeError as e:
                return ScrapingResult(
                    leads=[],
                    total_found=0,
                    errors=[f"Invalid JSON from worker: {e}", f"Output: {result.stdout[:500]}", f"Stderr: {result.stderr[:500]}"],
                    success=False
                )
            
            # Convert dict leads to Lead objects
            leads = []
            for lead_data in data.get('leads', []):
                lead = Lead(
                    business_name=lead_data.get('business_name', ''),
                    phone=lead_data.get('phone', ''),
                    website=lead_data.get('website', ''),
                    address=lead_data.get('address', ''),
                    source=lead_data.get('source', LeadSource.GOOGLE_MAPS.value)
                )
                leads.append(lead)
            
            return ScrapingResult(
                leads=leads,
                total_found=data.get('total_found', len(leads)),
                errors=data.get('errors', []),
                success=data.get('success', False)
            )
            
        except subprocess.TimeoutExpired:
            return ScrapingResult(
                leads=[],
                total_found=0,
                errors=["Scraping timed out after 5 minutes"],
                success=False
            )
        except Exception as e:
            return ScrapingResult(
                leads=[],
                total_found=0,
                errors=[f"Subprocess error: {str(e)}"],
                success=False
            )
    
    # Alias
    def search(self, *args, **kwargs):
        return self.search_sync(*args, **kwargs)


def scrape_google_maps(
    query: str,
    location: str = "",
    max_results: int = 20,
    headless: bool = True
) -> List[Lead]:
    scraper = GoogleMapsScraper(headless=headless, max_results=max_results)
    result = scraper.search_sync(query, location)
    return result.leads
