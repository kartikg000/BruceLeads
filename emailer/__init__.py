"""BruceLeads Email Modules"""

from .composer import EmailComposer, generate_email
from .templates import AIDA_TEMPLATE, PAS_TEMPLATE, get_template
from .gmail_client import GmailClient

__all__ = [
    "EmailComposer", 
    "generate_email",
    "AIDA_TEMPLATE",
    "PAS_TEMPLATE",
    "get_template",
    "GmailClient"
]
