"""BruceLeads Data Models"""

from .lead import Lead, LeadStatus, LeadSource
from .database import LeadsDatabase

__all__ = ["Lead", "LeadStatus", "LeadSource", "LeadsDatabase"]
