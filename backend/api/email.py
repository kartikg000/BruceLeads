
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel
from typing import List, Optional
from models import LeadsDatabase, LeadStatus
from emailer import EmailComposer
from backend.dependencies import get_db

router = APIRouter()
composer = EmailComposer()

class GenerateRequest(BaseModel):
    lead_ids: List[str]
    framework: str = "AIDA"  # AIDA or PAS
    custom_instructions: Optional[str] = None
    sender_name: Optional[str] = None
    service_description: Optional[str] = None
    temperature: Optional[float] = None
    max_words: Optional[int] = None
    tone: Optional[str] = None

class EmailDraft(BaseModel):
    lead_id: str
    subject: str
    body: str

@router.post("/generate")
async def generate_emails(request: GenerateRequest, db: LeadsDatabase = Depends(get_db)):
    """
    Generate emails for specific leads.
    Note: For a real production app, this should be a background task with SSE/WebSockets.
    For now, we'll do simpler synchronous generation or trivial background updates.
    """
    # Generation will use template fallback when Gemini is not configured

    results = []
    succeeded = 0
    failed = 0
    last_error = ""

    # Build custom composer — always use user-provided AI params
    gen_composer = EmailComposer(
        sender_name=request.sender_name or composer.sender_name,
        service_description=request.service_description or composer.service_description,
        temperature=request.temperature if request.temperature is not None else composer.temperature,
        max_words=request.max_words if request.max_words is not None else composer.max_words,
    )

    # Build custom context — tone is passed separately to the template
    custom_ctx = request.custom_instructions or ""
    tone = request.tone or ""
    
    for lead_id in request.lead_ids:
        lead = db.get_lead(lead_id)
        if not lead:
            continue
        
        try:
            # Use the compose method which returns EmailResult
            result = gen_composer.compose(
                lead, 
                framework=request.framework,
                custom_context=custom_ctx,
                tone=tone
            )
            
            if result.success:
                # Update lead with generated content
                lead.set_email_content(
                    subject=result.subject,
                    body=result.body,
                    framework=request.framework
                )
                db.update_lead(lead)
                succeeded += 1
                
                results.append({
                    "lead_id": lead.id,
                    "subject": result.subject,
                    "body": result.body
                })
            else:
                failed += 1
                last_error = result.error or "Unknown generation error"
                results.append({
                    "lead_id": lead.id,
                    "subject": "",
                    "body": "",
                    "error": result.error
                })
        except Exception as e:
            failed += 1
            last_error = str(e)
            results.append({
                "lead_id": lead.id,
                "subject": "",
                "body": "",
                "error": str(e)
            })
    
    # If all failed, return error status with the reason
    if succeeded == 0 and failed > 0:
        return {
            "status": "error",
            "generated": results,
            "succeeded": 0,
            "failed": failed,
            "error": last_error
        }
    
    return {
        "status": "success",
        "generated": results,
        "succeeded": succeeded,
        "failed": failed
    }

@router.post("/save")
async def save_draft(draft: EmailDraft, db: LeadsDatabase = Depends(get_db)):
    """Update the draft content for a lead."""
    lead = db.get_lead(draft.lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
        
    lead.email_subject = draft.subject
    lead.email_body = draft.body
    lead.update_status(LeadStatus.DRAFT)
    
    db.update_lead(lead)
    return {"status": "saved"}

@router.post("/send")
async def send_email(draft: EmailDraft, db: LeadsDatabase = Depends(get_db)):
    """Send an email via Gmail API."""
    from emailer import GmailClient
    from utils import validate_email as _validate_email
    
    lead = db.get_lead(draft.lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    if not lead.email:
        raise HTTPException(status_code=400, detail="Lead has no email address")

    # Validate email format before sending
    if not _validate_email(lead.email):
        raise HTTPException(status_code=400, detail="Invalid email address format")

    # Validate subject/body length
    if len(draft.subject) > 998:  # RFC 5322 max header line
        raise HTTPException(status_code=400, detail="Subject line too long")
    if len(draft.body) > 100_000:
        raise HTTPException(status_code=400, detail="Email body too large")
    
    try:
        gmail = GmailClient()
        result = gmail.send_email(
            to=lead.email,
            subject=draft.subject,
            body=draft.body
        )
        
        if result.success:
            lead.email_subject = draft.subject
            lead.email_body = draft.body
            lead.update_status(LeadStatus.SENT)
            db.update_lead(lead)
            return {"status": "sent", "to": lead.email}
        else:
            raise HTTPException(status_code=500, detail=result.error or "Gmail API error")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send: {str(e)}")

class BatchSendRequest(BaseModel):
    lead_ids: List[str]

@router.post("/send-batch")
async def send_batch_emails(request: BatchSendRequest, db: LeadsDatabase = Depends(get_db)):
    """Send emails to multiple leads using their generated content."""
    from emailer import GmailClient
    
    gmail = GmailClient()
    sent_count = 0
    errors = []
    
    for lead_id in request.lead_ids:
        lead = db.get_lead(lead_id)
        if not lead or not lead.email or not lead.email_body:
            continue
            
        try:
            result = gmail.send_email(
                to=lead.email,
                subject=lead.email_subject or "Hello",
                body=lead.email_body
            )
            
            if result.success:
                lead.update_status(LeadStatus.SENT)
                db.update_lead(lead)
                sent_count += 1
        except Exception as e:
            errors.append({"lead_id": lead_id, "error": str(e)})
        
        # Random delay between sends to avoid spam detection
        import time, random
        if lead_id != request.lead_ids[-1]:
            time.sleep(random.uniform(1, 7))
            
    return {"status": "success", "sent": sent_count, "errors": errors}


class CreateDraftsRequest(BaseModel):
    lead_ids: List[str]

@router.post("/create-drafts")
async def create_drafts(request: CreateDraftsRequest, db: LeadsDatabase = Depends(get_db)):
    """Create Gmail drafts for multiple leads."""
    from emailer import GmailClient

    gmail = GmailClient()

    if not gmail.is_oauth_active:
        raise HTTPException(
            status_code=400,
            detail="Creating Gmail drafts requires OAuth connection. Go to Settings → Connect Gmail. Alternatively, use 'Send Immediately' which works with SMTP."
        )

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
