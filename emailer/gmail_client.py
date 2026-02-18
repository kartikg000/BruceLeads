"""
Gmail Client
Handles email sending via SMTP (App Password) or OAuth2 (Gmail API).
"""

import smtplib
import ssl
import time
import random
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from pathlib import Path

import config
from models import Lead, LeadStatus

# Gmail API scopes
SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.compose',
    'https://www.googleapis.com/auth/gmail.readonly'
]

@dataclass
class SendResult:
    """Result of an email send operation."""
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None


class GmailClient:
    """
    Gmail client supporting both SMTP (App Password) and OAuth2 (Gmail API).
    
    Priority:
    1. OAuth2 (if token exists) — uses Gmail API
    2. SMTP (if GMAIL_USER + GMAIL_APP_PASSWORD set) — uses SMTP
    """
    
    def __init__(self):
        self.user = config.GMAIL_USER
        self.password = config.GMAIL_APP_PASSWORD
        
        # OAuth components (lazy loaded)
        self._service = None
        self._credentials = None
        self._oauth_user_email = None
    
    def _load_oauth_credentials(self):
        """Load saved OAuth credentials from token file."""
        if self._credentials is not None:
            return self._credentials
            
        token_path = config.GMAIL_TOKEN_FILE
        
        if not token_path.exists():
            return None
        
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
            
            # Refresh if expired
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                # Save refreshed token
                with open(token_path, 'w') as f:
                    f.write(creds.to_json())
            
            if creds and creds.valid:
                self._credentials = creds
                return creds
                
        except Exception:
            pass
        
        return None
    
    def _get_gmail_service(self):
        """Get or create Gmail API service."""
        if self._service is not None:
            return self._service
        
        creds = self._load_oauth_credentials()
        if not creds:
            return None
        
        try:
            from googleapiclient.discovery import build
            self._service = build('gmail', 'v1', credentials=creds)
            return self._service
        except Exception:
            return None
    
    def run_oauth_flow(self) -> dict:
        """
        Run the OAuth2 consent flow.
        Opens a browser for the user to authorize the app.
        
        Returns:
            dict with 'success', 'message', and optionally 'email'
        """
        credentials_path = config.GMAIL_CREDENTIALS_FILE
        
        if not credentials_path.exists():
            return {
                "success": False,
                "message": (
                    "OAuth credentials file not found.\n\n"
                    "To set up Gmail OAuth:\n"
                    "1. Go to https://console.cloud.google.com\n"
                    "2. Create a project and enable the Gmail API\n"
                    "3. Create OAuth credentials (Desktop app)\n"
                    f"4. Save the JSON file to: {credentials_path}"
                )
            }
        
        try:
            from google_auth_oauthlib.flow import InstalledAppFlow
            
            flow = InstalledAppFlow.from_client_secrets_file(
                str(credentials_path), SCOPES
            )
            
            # This opens the browser for consent
            creds = flow.run_local_server(port=0)
            
            # Save the token
            token_path = config.GMAIL_TOKEN_FILE
            token_path.parent.mkdir(parents=True, exist_ok=True)
            with open(token_path, 'w') as f:
                f.write(creds.to_json())
            
            self._credentials = creds
            self._service = None  # Force rebuild
            
            # Get user email
            email = self._get_user_email()
            
            return {
                "success": True,
                "message": "Gmail connected successfully!",
                "email": email
            }
            
        except Exception as e:
            return {"success": False, "message": f"OAuth flow failed: {str(e)}"}
    
    def _get_user_email(self) -> Optional[str]:
        """Get the authenticated user's email address."""
        if self._oauth_user_email:
            return self._oauth_user_email
            
        service = self._get_gmail_service()
        if service:
            try:
                profile = service.users().getProfile(userId='me').execute()
                self._oauth_user_email = profile.get('emailAddress')
                return self._oauth_user_email
            except Exception:
                pass
        return None
    
    def get_oauth_status(self) -> dict:
        """
        Get current OAuth connection status.
        
        Returns:
            dict with 'status' ('connected', 'disconnected', 'needs_setup')
            and optionally 'email'
        """
        creds = self._load_oauth_credentials()
        
        if creds and creds.valid:
            email = self._get_user_email()
            return {"status": "connected", "email": email}
        
        if config.GMAIL_CREDENTIALS_FILE.exists():
            return {"status": "disconnected"}
        
        return {"status": "needs_setup"}
    
    def disconnect(self):
        """Remove saved OAuth token."""
        token_path = config.GMAIL_TOKEN_FILE
        if token_path.exists():
            token_path.unlink()
        self._credentials = None
        self._service = None
        self._oauth_user_email = None
    
    @property
    def is_configured(self) -> bool:
        """Check if any email sending method is configured."""
        # Check OAuth first
        creds = self._load_oauth_credentials()
        if creds and creds.valid:
            return True
        # Fall back to SMTP
        return bool(self.user and self.password)
    
    @property
    def is_oauth_active(self) -> bool:
        """Check if OAuth is the active sending method."""
        creds = self._load_oauth_credentials()
        return bool(creds and creds.valid)
    
    def authenticate(self) -> bool:
        """
        Verify credentials are available.
        For OAuth, checks token. For SMTP, checks env vars.
        """
        if self.is_oauth_active:
            return True
        return bool(self.user and self.password)
    
    def _send_via_gmail_api(self, to: str, subject: str, body: str, is_html: bool = False) -> SendResult:
        """Send email using Gmail API (OAuth)."""
        service = self._get_gmail_service()
        if not service:
            return SendResult(success=False, error="Gmail API service not available. Please reconnect.")
        
        try:
            if is_html:
                msg = MIMEMultipart("alternative")
                msg.attach(MIMEText(body, "html"))
            else:
                msg = MIMEText(body, "plain")
            
            msg["Subject"] = subject
            msg["From"] = self._get_user_email() or "me"
            msg["To"] = to
            
            # Encode for Gmail API
            raw = base64.urlsafe_b64encode(msg.as_bytes()).decode('utf-8')
            
            result = service.users().messages().send(
                userId='me',
                body={'raw': raw}
            ).execute()
            
            return SendResult(success=True, message_id=result.get('id', 'gmail-api-sent'))
            
        except Exception as e:
            return SendResult(success=False, error=f"Gmail API error: {str(e)}")
    
    def _send_via_smtp(self, to: str, subject: str, body: str, is_html: bool = False) -> SendResult:
        """Send email using SMTP (App Password)."""
        if is_html:
            msg = MIMEMultipart("alternative")
            msg.attach(MIMEText(body, "html"))
        else:
            msg = MIMEText(body, "plain")
            
        msg["Subject"] = subject
        msg["From"] = self.user
        msg["To"] = to
        
        try:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
                server.login(self.user, self.password)
                server.sendmail(self.user, to, msg.as_string())
                
            return SendResult(success=True, message_id="smtp-sent")
            
        except Exception as e:
            return SendResult(success=False, error=str(e))
        
    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        is_html: bool = False
    ) -> SendResult:
        """
        Send an email. Uses OAuth (Gmail API) if available, falls back to SMTP.
        """
        if not self.is_configured:
            return SendResult(success=False, error="Gmail not configured. Connect via OAuth or set GMAIL_USER and GMAIL_APP_PASSWORD in .env")
        
        # Prefer OAuth
        if self.is_oauth_active:
            return self._send_via_gmail_api(to, subject, body, is_html)
        
        # Fall back to SMTP
        return self._send_via_smtp(to, subject, body, is_html)

    def create_draft_for_lead(self, lead: Lead) -> SendResult:
        """
        Create a draft in Gmail for a lead.
        Uses Gmail API if OAuth is active, otherwise marks as local draft.
        """
        if self.is_oauth_active and lead.has_email_content() and lead.email:
            service = self._get_gmail_service()
            if service:
                try:
                    is_html = "<html>" in lead.email_body.lower() or "<div>" in lead.email_body.lower()
                    if is_html:
                        msg = MIMEMultipart("alternative")
                        msg.attach(MIMEText(lead.email_body, "html"))
                    else:
                        msg = MIMEText(lead.email_body, "plain")
                    
                    msg["Subject"] = lead.email_subject
                    msg["To"] = lead.email
                    
                    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode('utf-8')
                    
                    result = service.users().drafts().create(
                        userId='me',
                        body={'message': {'raw': raw}}
                    ).execute()
                    
                    return SendResult(success=True, message_id=result.get('id', 'gmail-draft'))
                except Exception as e:
                    return SendResult(success=False, error=f"Draft creation failed: {str(e)}")
        
        return SendResult(success=False, error="OAuth not active — cannot create Gmail draft. Connect Gmail first.")

    def send_email_to_lead(self, lead: Lead) -> SendResult:
        """Send email directly to a lead."""
        if not lead.email:
            return SendResult(success=False, error="Lead has no email address")
        
        if not lead.has_email_content():
            return SendResult(success=False, error="Lead has no email content generated")
        
        # Determine if body looks like HTML
        is_html = "<html>" in lead.email_body.lower() or "<div>" in lead.email_body.lower()
        
        result = self.send_email(
            to=lead.email,
            subject=lead.email_subject,
            body=lead.email_body,
            is_html=is_html
        )
        
        if result.success:
            lead.update_status(LeadStatus.SENT)
        else:
            lead.update_status(LeadStatus.FAILED)
        
        return result
    
    def send_batch(
        self,
        leads: List[Lead],
        create_drafts_only: bool = False,
        progress_callback=None
    ) -> List[Tuple[Lead, SendResult]]:
        """Process multiple leads with random delays between sends."""
        results = []
        total = len(leads)
        
        for i, lead in enumerate(leads):
            if progress_callback:
                progress_callback(i + 1, total)
            
            if create_drafts_only:
                result = self.create_draft_for_lead(lead)
            else:
                result = self.send_email_to_lead(lead)
            
            results.append((lead, result))
            
            # Random delay between sends to avoid spam detection
            if not create_drafts_only and i < total - 1:
                time.sleep(random.uniform(1, 7))
        
        return results
