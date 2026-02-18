"""
Lead Data Model
Defines the core Lead dataclass with validation and serialization.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Optional
import json
import re
import uuid


class LeadStatus(str, Enum):
    """Status of a lead in the pipeline."""
    PENDING = "pending"
    ENRICHED = "enriched"
    GENERATED = "generated"
    DRAFT = "draft"
    SENT = "sent"
    FAILED = "failed"


class LeadSource(str, Enum):
    """Source where the lead was discovered."""
    GOOGLE_MAPS = "Google Maps"
    TWITTER = "X/Twitter"
    LINKEDIN = "LinkedIn"
    MANUAL = "Manual"


@dataclass
class Lead:
    """
    Represents a business lead with contact information and outreach status.
    """
    # Core identification
    id: str = ""
    business_name: str = ""
    owner_name: str = ""
    
    # Contact information
    email: str = ""
    phone: str = ""
    website: str = ""
    address: str = ""
    
    # Discovery metadata
    source: str = LeadSource.GOOGLE_MAPS.value
    intent_signal: str = ""  # The phrase/context that indicated intent
    intent_score: int = 5  # 1-10 score based on intent strength
    
    # Status tracking
    status: str = LeadStatus.PENDING.value
    
    # Email content
    email_subject: str = ""
    email_body: str = ""
    email_framework: str = "AIDA"  # AIDA or PAS
    
    # Timestamps
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    sent_at: Optional[str] = None
    
    # Additional notes
    notes: str = ""
    
    def __post_init__(self):
        """Generate ID if not provided and sanitize None values."""
        if not self.id:
            self.id = str(uuid.uuid4())[:8]
        # Sanitize None values to empty strings for string fields
        for field_name in ['business_name', 'owner_name', 'email', 'phone',
                           'website', 'address', 'source', 'intent_signal',
                           'email_subject', 'email_body', 'email_framework',
                           'notes']:
            if getattr(self, field_name) is None:
                setattr(self, field_name, '')
    
    def update_status(self, new_status: LeadStatus):
        """Update the lead status and timestamp."""
        self.status = new_status.value
        self.updated_at = datetime.now().isoformat()
        if new_status == LeadStatus.SENT:
            self.sent_at = datetime.now().isoformat()
    
    def set_email_content(self, subject: str, body: str, framework: str = "AIDA"):
        """Set the generated email content."""
        self.email_subject = subject
        self.email_body = body
        self.email_framework = framework
        self.update_status(LeadStatus.GENERATED)
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Basic email format validation."""
        if not email:
            return False
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_url(url: str) -> bool:
        """Basic URL format validation."""
        if not url:
            return False
        pattern = r'^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        return bool(re.match(pattern, url))
    
    def is_enriched(self) -> bool:
        """Check if lead has been enriched with email."""
        return bool(self.email) and self.validate_email(self.email)
    
    def has_email_content(self) -> bool:
        """Check if email has been generated."""
        return bool(self.email_subject and self.email_body)
    
    def to_dict(self) -> dict:
        """Convert lead to dictionary."""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert lead to JSON string."""
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_dict(cls, data: dict) -> "Lead":
        """Create Lead from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
    
    @classmethod
    def from_json(cls, json_str: str) -> "Lead":
        """Create Lead from JSON string."""
        return cls.from_dict(json.loads(json_str))
    
    def summary(self) -> str:
        """Return a brief summary of the lead."""
        email_status = "✅" if self.is_enriched() else "❌"
        return f"{self.business_name} ({self.source}) - Email: {email_status} - Status: {self.status}"
    
    def __repr__(self):
        return f"Lead(id={self.id}, business={self.business_name}, status={self.status})"
