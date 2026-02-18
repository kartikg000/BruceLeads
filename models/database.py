"""
Leads Database Module
Simple JSON-based storage for leads with CRUD operations.
"""

import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
import pandas as pd

from .lead import Lead, LeadStatus, LeadSource
import config


class LeadsDatabase:
    """
    JSON file-based database for storing and managing leads.
    Thread-safe JSON file database for single-user applications.
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """Initialize database with optional custom path."""
        self.db_path = db_path or config.LEADS_DB_FILE
        self._ensure_db_exists()
    
    def _ensure_db_exists(self):
        """Create database file if it doesn't exist."""
        if not self.db_path.exists():
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._save_leads([])
    
    def _load_leads(self) -> List[Dict[str, Any]]:
        """Load raw lead data from JSON file."""
        try:
            with open(self.db_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []
    
    def _save_leads(self, leads: List[Dict[str, Any]]):
        """Save lead data to JSON file."""
        with open(self.db_path, 'w', encoding='utf-8') as f:
            json.dump(leads, f, indent=2, ensure_ascii=False)
    
    # =========================================================================
    # CRUD Operations
    # =========================================================================
    
    def add_lead(self, lead: Lead) -> Lead:
        """Add a new lead to the database (skips duplicates by business name + source)."""
        leads = self._load_leads()
        # Duplicate check by business_name + source
        for existing in leads:
            if (existing.get('business_name', '').lower() == lead.business_name.lower()
                    and existing.get('source', '') == lead.source):
                # Return existing lead rather than adding duplicate
                return Lead.from_dict(existing)
        leads.append(lead.to_dict())
        self._save_leads(leads)
        return lead
    
    def add_leads(self, new_leads: List[Lead]) -> int:
        """Add multiple leads at once. Returns count of added leads."""
        if not new_leads:
            return 0
        leads = self._load_leads()
        for lead in new_leads:
            leads.append(lead.to_dict())
        self._save_leads(leads)
        return len(new_leads)
    
    def get_lead(self, lead_id: str) -> Optional[Lead]:
        """Get a specific lead by ID."""
        leads = self._load_leads()
        for lead_data in leads:
            if lead_data.get('id') == lead_id:
                return Lead.from_dict(lead_data)
        return None
    
    def get_all_leads(self) -> List[Lead]:
        """Get all leads from database."""
        leads = self._load_leads()
        return [Lead.from_dict(data) for data in leads]
    
    def update_lead(self, lead: Lead) -> bool:
        """Update an existing lead. Returns True if updated."""
        leads = self._load_leads()
        lead.updated_at = datetime.now().isoformat()
        
        for i, lead_data in enumerate(leads):
            if lead_data.get('id') == lead.id:
                leads[i] = lead.to_dict()
                self._save_leads(leads)
                return True
        return False
    
    def delete_lead(self, lead_id: str) -> bool:
        """Delete a lead by ID. Returns True if deleted."""
        leads = self._load_leads()
        original_count = len(leads)
        leads = [l for l in leads if l.get('id') != lead_id]
        
        if len(leads) < original_count:
            self._save_leads(leads)
            return True
        return False
    
    def delete_leads(self, lead_ids: List[str]) -> int:
        """Delete multiple leads. Returns count of deleted leads."""
        leads = self._load_leads()
        original_count = len(leads)
        leads = [l for l in leads if l.get('id') not in lead_ids]
        deleted_count = original_count - len(leads)
        
        if deleted_count > 0:
            self._save_leads(leads)
        return deleted_count
    
    def clear_all(self):
        """Delete all leads from database."""
        self._save_leads([])
    
    # =========================================================================
    # Filtering & Querying
    # =========================================================================
    
    def filter_by_status(self, status: LeadStatus) -> List[Lead]:
        """Get leads with a specific status."""
        return [lead for lead in self.get_all_leads() if lead.status == status.value]
    
    def filter_by_source(self, source: LeadSource) -> List[Lead]:
        """Get leads from a specific source."""
        return [lead for lead in self.get_all_leads() if lead.source == source.value]
    
    def filter_by_intent_score(self, min_score: int = 1, max_score: int = 10) -> List[Lead]:
        """Get leads within an intent score range."""
        return [
            lead for lead in self.get_all_leads()
            if min_score <= lead.intent_score <= max_score
        ]
    
    def get_enriched_leads(self) -> List[Lead]:
        """Get leads that have email addresses."""
        return [lead for lead in self.get_all_leads() if lead.is_enriched()]
    
    def get_ready_to_send(self) -> List[Lead]:
        """Get leads with generated emails ready to send."""
        return [
            lead for lead in self.get_all_leads()
            if lead.has_email_content() and lead.status in [
                LeadStatus.GENERATED.value, 
                LeadStatus.DRAFT.value
            ]
        ]
    
    def search(self, query: str) -> List[Lead]:
        """Search leads by business name, owner name, or email."""
        query = query.lower()
        return [
            lead for lead in self.get_all_leads()
            if query in lead.business_name.lower()
            or query in lead.owner_name.lower()
            or query in lead.email.lower()
        ]
    
    # =========================================================================
    # Statistics
    # =========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        leads = self.get_all_leads()
        
        if not leads:
            return {
                "total": 0,
                "by_status": {},
                "by_source": {},
                "enriched": 0,
                "emails_generated": 0,
                "emails_sent": 0
            }
        
        by_status = {}
        by_source = {}
        
        for lead in leads:
            by_status[lead.status] = by_status.get(lead.status, 0) + 1
            by_source[lead.source] = by_source.get(lead.source, 0) + 1
        
        return {
            "total": len(leads),
            "by_status": by_status,
            "by_source": by_source,
            "enriched": len([l for l in leads if l.is_enriched()]),
            "emails_generated": len([l for l in leads if l.has_email_content()]),
            "sent": len([l for l in leads if l.status == LeadStatus.SENT.value]),
            "emails_sent": len([l for l in leads if l.status == LeadStatus.SENT.value])
        }
    
    # =========================================================================
    # Export
    # =========================================================================
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert all leads to a pandas DataFrame."""
        leads = self._load_leads()
        if not leads:
            return pd.DataFrame()
        return pd.DataFrame(leads)
    
    def export_csv(self, filepath: Path) -> bool:
        """Export leads to CSV file."""
        try:
            df = self.to_dataframe()
            df.to_csv(filepath, index=False, encoding='utf-8')
            return True
        except Exception:
            return False
    
    def export_excel(self, filepath: Path) -> bool:
        """Export leads to Excel file."""
        try:
            df = self.to_dataframe()
            df.to_excel(filepath, index=False, engine='openpyxl')
            return True
        except Exception:
            return False
    
    def import_csv(self, filepath: Path) -> int:
        """Import leads from CSV. Returns count of imported leads."""
        try:
            df = pd.read_csv(filepath)
            new_leads = []
            for _, row in df.iterrows():
                lead = Lead.from_dict(row.to_dict())
                new_leads.append(lead)
            return self.add_leads(new_leads)
        except Exception:
            return 0
