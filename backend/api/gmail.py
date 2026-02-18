
from fastapi import APIRouter, HTTPException, Depends
from typing import List
from pydantic import BaseModel
from models import LeadsDatabase, LeadStatus
from emailer import GmailClient
from backend.dependencies import get_db

router = APIRouter()

@router.get("/status")
def get_gmail_status():
    """Check if Gmail is properly configured."""
    try:
        gmail = GmailClient()
        if gmail.is_oauth_active:
            email = gmail._get_user_email()
            return {"connected": True, "message": f"Connected as {email}" if email else "Gmail is connected"}
        elif gmail.user and gmail.password:
            return {"connected": True, "message": f"SMTP configured ({gmail.user})"}
        else:
            return {"connected": False, "message": "Gmail not configured. Run OAuth setup or set SMTP credentials."}
    except Exception as e:
        return {"connected": False, "message": str(e)}

class DraftRequest(BaseModel):
    lead_ids: List[str]

@router.post("/create-drafts")
async def create_drafts(request: DraftRequest, db: LeadsDatabase = Depends(get_db)):
    """Create Gmail drafts for multiple leads."""
    gmail = GmailClient()
    
    try:
        gmail.authenticate()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gmail connection failed: {str(e)}")
    
    created_count = 0
    errors = []
    
    for lead_id in request.lead_ids:
        lead = db.get_lead(lead_id)
        if not lead or not lead.email or not lead.email_body:
            continue
            
        try:
            result = gmail.create_draft_for_lead(lead)
            if result.success:
                lead.update_status(LeadStatus.DRAFT)
                db.update_lead(lead)
                created_count += 1
            else:
                errors.append({"lead_id": lead_id, "error": result.error})
        except Exception as e:
            errors.append({"lead_id": lead_id, "error": str(e)})
    
    return {"status": "success", "created": created_count, "errors": errors}


# ── OAuth Endpoints (for React frontend) ───────────────────────


@router.get("/oauth-status")
def get_oauth_status():
    """
    Return detailed OAuth status: connected / disconnected / needs_setup.
    """
    gmail = GmailClient()
    return gmail.get_oauth_status()


@router.post("/connect")
def connect_gmail():
    """
    Trigger the OAuth consent flow.
    Opens a browser window for the user to authorise the app.
    """
    gmail = GmailClient()
    result = gmail.run_oauth_flow()
    return result


@router.post("/disconnect")
def disconnect_gmail():
    """Remove the saved OAuth token."""
    gmail = GmailClient()
    gmail.disconnect()
    return {"success": True, "message": "Gmail disconnected"}
