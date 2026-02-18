
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Any
from models import LeadsDatabase, Lead, LeadStatus
from backend.dependencies import get_db
import io
import csv

router = APIRouter()

class ManualLeadRequest(BaseModel):
    business_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    owner_name: Optional[str] = None
    address: Optional[str] = None
    source: str = "Manual"

@router.post("/add")
def add_lead_manually(request: ManualLeadRequest, db: LeadsDatabase = Depends(get_db)):
    """Add a lead manually."""
    lead = Lead(
        business_name=request.business_name,
        email=request.email or "",
        phone=request.phone or "",
        website=request.website or "",
        owner_name=request.owner_name or "",
        address=request.address or "",
        source=request.source
    )
    db.add_lead(lead)
    return {"status": "success", "id": lead.id}

class LeadModel(BaseModel):
    id: str
    business_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    owner_name: Optional[str] = None
    source: str
    status: str
    email_framework: Optional[str] = None
    email_subject: Optional[str] = None
    email_body: Optional[str] = None
    intent_score: int = 0
    intent_signal: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    sent_at: Optional[str] = None
    notes: Optional[str] = None

@router.get("/", response_model=List[LeadModel])
def get_leads(db: LeadsDatabase = Depends(get_db)):
    """Get all leads."""
    leads = db.get_all_leads()
    return [l.to_dict() for l in leads]

@router.get("/{lead_id}", response_model=LeadModel)
def get_lead(lead_id: str, db: LeadsDatabase = Depends(get_db)):
    """Get a single lead by ID."""
    lead = db.get_lead(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead.to_dict()

@router.delete("/{lead_id}")
def delete_lead(lead_id: str, db: LeadsDatabase = Depends(get_db)):
    """Delete a lead."""
    db.delete_lead(lead_id)
    return {"status": "deleted", "id": lead_id}

class BatchRequest(BaseModel):
    lead_ids: List[str]

@router.post("/enrich")
def batch_enrich(request: BatchRequest, db: LeadsDatabase = Depends(get_db)):
    """Enrich multiple leads by finding email/owner info."""
    from scrapers import LeadEnricher
    enricher = LeadEnricher()
    enriched_count = 0
    
    for lead_id in request.lead_ids:
        lead = db.get_lead(lead_id)
        if lead:
            try:
                enriched_list = enricher.enrich_leads_sync([lead])
                if enriched_list:
                    enriched = enriched_list[0]
                    enriched.update_status(LeadStatus.ENRICHED)
                    db.update_lead(enriched)
                    enriched_count += 1
            except Exception as e:
                print(f"Enrichment error for {lead_id}: {e}")
                
    return {"status": "success", "enriched": enriched_count}

@router.post("/delete")
def batch_delete(request: BatchRequest, db: LeadsDatabase = Depends(get_db)):
    """Delete multiple leads."""
    deleted_count = 0
    for lead_id in request.lead_ids:
        try:
            db.delete_lead(lead_id)
            deleted_count += 1
        except Exception:
            pass
    return {"status": "success", "deleted": deleted_count}

@router.post("/clear")
def clear_all_leads(db: LeadsDatabase = Depends(get_db)):
    """Delete all leads from the database."""
    db.clear_all()
    return {"status": "success", "message": "All leads deleted"}


class UpdateLeadRequest(BaseModel):
    business_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    owner_name: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None
    email_subject: Optional[str] = None
    email_body: Optional[str] = None


@router.put("/{lead_id}")
def update_lead(lead_id: str, request: UpdateLeadRequest, db: LeadsDatabase = Depends(get_db)):
    """Update a lead's fields."""
    lead = db.get_lead(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    update_data = request.model_dump(exclude_none=True)
    for key, value in update_data.items():
        if hasattr(lead, key):
            setattr(lead, key, value)

    db.update_lead(lead)
    return {"status": "success", "lead": lead.to_dict()}


@router.get("/export/csv")
def export_csv(db: LeadsDatabase = Depends(get_db)):
    """Export all leads as CSV download."""
    leads = db.get_all_leads()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Business Name', 'Owner', 'Email', 'Phone', 'Website', 'Address', 'Source', 'Status', 'Intent Score'])
    for lead in leads:
        writer.writerow([
            lead.business_name, lead.owner_name, lead.email, lead.phone,
            lead.website, lead.address, lead.source, lead.status, lead.intent_score
        ])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=leads_export.csv"}
    )


@router.post("/import/csv")
async def import_csv(file: UploadFile = File(...), db: LeadsDatabase = Depends(get_db)):
    """Import leads from a CSV file."""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a .csv")

    content = await file.read()
    text = content.decode('utf-8')
    reader = csv.DictReader(io.StringIO(text))

    imported = 0
    for row in reader:
        lead = Lead(
            business_name=row.get('Business Name', row.get('business_name', '')),
            owner_name=row.get('Owner', row.get('owner_name', '')),
            email=row.get('Email', row.get('email', '')),
            phone=row.get('Phone', row.get('phone', '')),
            website=row.get('Website', row.get('website', '')),
            address=row.get('Address', row.get('address', '')),
            source=row.get('Source', row.get('source', 'CSV Import')),
        )
        if lead.business_name:
            db.add_lead(lead)
            imported += 1

    return {"status": "success", "imported": imported}

