"""
Lead Enrichment Module
Wrapper that runs enrichment in a subprocess.
"""

import subprocess
import sys
import json
from typing import List, Optional, Callable
from pathlib import Path

from models import Lead, LeadStatus
from utils import get_python_executable
import config


class LeadEnricher:
    """
    Enriches leads by finding emails from websites and web search.
    Uses a subprocess to avoid Playwright event loop conflicts.
    """
    
    def __init__(
        self,
        headless: bool = True,
        use_google_search: bool = True
    ):
        self.headless = headless
        self.use_google_search = use_google_search
    
    def enrich_leads_sync(
        self,
        leads: List[Lead],
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[Lead]:
        """
        Enrich multiple leads with email addresses.
        
        Args:
            leads: List of leads to enrich
            progress_callback: Optional callback for progress (not used in subprocess mode)
            
        Returns:
            List of enriched leads
        """
        if not leads:
            return []
        
        # Get path to worker script
        worker_path = Path(__file__).parent / "enrich_worker.py"
        
        if not worker_path.exists():
            print(f"Warning: Enrichment worker not found at {worker_path}")
            return leads
        
        # Convert leads to JSON
        leads_data = []
        for lead in leads:
            leads_data.append({
                'id': lead.id,
                'business_name': lead.business_name,
                'email': lead.email or '',
                'phone': lead.phone or '',
                'website': lead.website or '',
                'address': lead.address or '',
                'owner_name': lead.owner_name or '',
                'source': lead.source,
            })
        
        leads_json = json.dumps(leads_data)
        
        # Build command
        concurrency = getattr(config, 'MAX_CONCURRENT_BROWSERS', 3)
        cmd = get_python_executable() + [
            str(worker_path),
            leads_json,
            str(self.headless).lower(),
            str(self.use_google_search).lower(),
            str(concurrency)
        ]
        
        try:
            # Run enricher in subprocess
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout
                cwd=str(Path(__file__).parent.parent)
            )
            
            # Parse output
            stdout_lines = result.stdout.strip().split('\n')
            if not stdout_lines:
                print(f"No output from enricher. stderr: {result.stderr[:500]}")
                return leads
            
            try:
                data = json.loads(stdout_lines[-1])
            except json.JSONDecodeError as e:
                print(f"Invalid JSON from enricher: {e}")
                print(f"Output: {result.stdout[:500]}")
                return leads
            
            # Update original leads with enriched data
            enriched_map = {l['id']: l for l in data.get('leads', [])}
            
            for lead in leads:
                if lead.id in enriched_map:
                    enriched = enriched_map[lead.id]
                    if enriched.get('email'):
                        lead.email = enriched['email']
                    if enriched.get('phone'):
                        lead.phone = enriched['phone']
                    if enriched.get('owner_name'):
                        lead.owner_name = enriched['owner_name']
                    if lead.email:
                        lead.update_status(LeadStatus.ENRICHED)
            
            return leads
            
        except subprocess.TimeoutExpired:
            print("Enrichment timed out after 10 minutes")
            return leads
        except Exception as e:
            print(f"Enrichment error: {e}")
            return leads


def enrich_lead(lead: Lead, headless: bool = True) -> Lead:
    """Enrich a single lead."""
    enricher = LeadEnricher(headless=headless)
    results = enricher.enrich_leads_sync([lead])
    return results[0] if results else lead
