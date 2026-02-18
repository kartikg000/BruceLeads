
from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel
from typing import List, Optional
from scrapers import GoogleMapsScraper, LeadEnricher
from models import LeadsDatabase
from backend.dependencies import get_db
import asyncio

router = APIRouter()

class ScrapeRequest(BaseModel):
    query: str
    location: str
    max_results: int = 20
    headless: bool = True
    auto_enrich: bool = True
    use_google_search: bool = True

class SocialScrapeRequest(BaseModel):
    query: str
    platforms: List[str]
    max_results: int = 10
    headless: bool = True

@router.post("/start")
async def start_scrape(request: ScrapeRequest, background_tasks: BackgroundTasks, db: LeadsDatabase = Depends(get_db)):
    """Start a Google Maps scraping job."""
    scraper = GoogleMapsScraper(
        headless=request.headless,
        max_results=request.max_results
    )
    
    # Run scraping synchronously for simpler response
    try:
        result = scraper.search_sync(request.query, request.location)
        
        if result.success:
            lead_ids = []
            for lead in result.leads:
                db.add_lead(lead)
                lead_ids.append(lead.id)
            
            # Auto-enrich if requested
            if request.auto_enrich and result.leads:
                enricher = LeadEnricher(
                    headless=request.headless,
                    use_google_search=request.use_google_search
                )
                enriched = enricher.enrich_leads_sync(result.leads)
                for lead in enriched:
                    db.update_lead(lead)
            
            return {
                "status": "success", 
                "leads_found": len(lead_ids),
                "lead_ids": lead_ids,
                "message": f"Found {len(lead_ids)} leads"
            }
        else:
            return {
                "status": "error",
                "leads_found": 0,
                "message": ", ".join(result.errors)
            }
    except Exception as e:
        return {
            "status": "error",
            "leads_found": 0,
            "message": str(e)
        }

@router.post("/social")
async def start_social_scrape(request: SocialScrapeRequest, background_tasks: BackgroundTasks, db: LeadsDatabase = Depends(get_db)):
    """Start a social media intent scraping job."""
    from scrapers import SocialMediaScraper
    
    try:
        scraper = SocialMediaScraper(
            headless=request.headless,
            max_results=request.max_results
        )
        
        all_leads = []
        all_errors = []
        
        for platform in request.platforms:
            result = scraper.search_sync(request.query, platform)
            
            if result.get('success'):
                platform_leads = result.get('leads', [])
                all_leads.extend(platform_leads)
            
            if result.get('errors'):
                all_errors.extend([f"{platform}: {e}" for e in result.get('errors')])
        
        # Save to database
        leads_found = 0
        for lead in all_leads:
            db.add_lead(lead)
            leads_found += 1
        
        return {
            "status": "success" if leads_found > 0 else "error",
            "leads_found": leads_found,
            "errors": all_errors,
            "message": f"Found {leads_found} leads across {len(request.platforms)} platforms"
        }
    except Exception as e:
        return {
            "status": "error",
            "leads_found": 0,
            "message": str(e)
        }
