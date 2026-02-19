"""
Email Composer Module
Uses Gemini 1.5 Flash to generate personalized cold emails.
"""

import re
from typing import Optional, Tuple, List
from dataclasses import dataclass

import google.generativeai as genai

import config
from models import Lead, LeadStatus
from .templates import format_template, DEFAULT_SERVICE


@dataclass
class EmailResult:
    """Result of email generation."""
    subject: str
    body: str
    framework: str
    success: bool
    error: Optional[str] = None


class EmailComposer:
    """
    Generates personalized cold emails using Gemini 1.5 Flash.
    """
    
    # Spam trigger words to check for
    SPAM_TRIGGERS = [
        'act now', 'limited time', 'guaranteed', 'no obligation',
        'winner', 'congratulations', 'urgent', 'free money',
        'click here', 'buy now', 'order now'
    ]
    
    def __init__(
        self,
        api_key: str = None,
        model: str = None,
        temperature: float = None,
        max_words: int = None,
        sender_name: str = "Your Name",
        service_description: str = ""
    ):
        """
        Initialize the email composer.
        
        Args:
            api_key: Gemini API key (uses config if not provided)
            model: Model name (uses config if not provided)
            temperature: Generation temperature (uses config if not provided)
            max_words: Maximum words per email (uses config if not provided)
            sender_name: Name to use in email signature
            service_description: Description of your service/offer
        """
        self.api_key = api_key or config.GEMINI_API_KEY
        self.model_name = model or config.GEMINI_MODEL
        self.temperature = temperature if temperature is not None else config.GEMINI_TEMPERATURE
        self.max_words = max_words if max_words is not None else config.MAX_EMAIL_WORDS
        self.sender_name = sender_name
        self.service_description = service_description or DEFAULT_SERVICE
        
        # Initialize Gemini
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.model_name)
        else:
            self.model = None
    
    def _parse_email_response(self, response: str) -> Tuple[str, str]:
        """
        Parse the LLM response to extract subject and body.
        
        Args:
            response: Raw LLM response
            
        Returns:
            Tuple of (subject, body)
        """
        # Try to find SUBJECT: line
        subject_match = re.search(r'SUBJECT:\s*(.+?)(?:\n|---)', response, re.IGNORECASE)
        subject = subject_match.group(1).strip() if subject_match else "Quick Question"
        
        # Everything after --- is the body
        if '---' in response:
            body = response.split('---', 1)[1].strip()
        else:
            # Fallback: remove subject line and use rest
            body = re.sub(r'^SUBJECT:.*\n?', '', response, flags=re.IGNORECASE).strip()
        
        return subject, body
    
    def _validate_email(self, subject: str, body: str) -> List[str]:
        """
        Validate generated email for quality issues.
        
        Args:
            subject: Email subject
            body: Email body
            
        Returns:
            List of warning messages (empty if all good)
        """
        warnings = []
        
        # Check word count
        word_count = len(body.split())
        if word_count > self.max_words * 1.2:  # 20% tolerance
            warnings.append(f"Email is {word_count} words (target: {self.max_words})")
        
        # Check for spam triggers
        full_text = (subject + ' ' + body).lower()
        for trigger in self.SPAM_TRIGGERS:
            if trigger in full_text:
                warnings.append(f"Contains spam trigger: '{trigger}'")
        
        # Check for unfilled placeholders
        if '{' in body and '}' in body:
            warnings.append("Contains unfilled placeholder")
        
        # Check for generic openings
        generic_openings = ['i hope this finds you well', 'i hope this email finds you']
        for opening in generic_openings:
            if opening in body.lower():
                warnings.append("Contains generic opening phrase")
        
        return warnings
    
    def compose(
        self,
        lead: Lead,
        framework: str = None,
        custom_context: str = "",
        tone: str = ""
    ) -> EmailResult:
        """
        Generate a personalized email for a lead.
        
        Args:
            lead: Lead to generate email for
            framework: "AIDA" or "PAS" (uses config default if not provided)
            custom_context: Additional context to include
            tone: Desired email tone (e.g. "casual and witty", "formal")
            
        Returns:
            EmailResult with subject and body
        """
        framework = framework or config.DEFAULT_EMAIL_FRAMEWORK
        
        # REQUIRE Gemini API key — no silent template fallback
        if not self.model:
            return EmailResult(
                subject="",
                body="",
                framework=framework,
                success=False,
                error="Gemini API key is not set. Please add your Gemini API key in Settings to generate AI-powered emails."
            )
            
        # Build the prompt
        intent_signal = lead.intent_signal or "Local business"
        
        prompt = format_template(
            framework=framework,
            business_name=lead.business_name,
            owner_name=lead.owner_name,
            website=lead.website,
            intent_signal=intent_signal,
            service_description=self.service_description,
            sender_name=self.sender_name,
            max_words=self.max_words,
            tone=tone,
            custom_instructions=custom_context  # Pass explicit instructions
        )
        
        try:
            # Generate email
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=self.temperature,
                    max_output_tokens=500
                )
            )
            
            # Parse response
            subject, body = self._parse_email_response(response.text)
            
            # Validate
            warnings = self._validate_email(subject, body)
            
            return EmailResult(
                subject=subject,
                body=body,
                framework=framework,
                success=True,
                error="; ".join(warnings) if warnings else None
            )
            
        except Exception as e:
            # Return error instead of silent template fallback
            return EmailResult(
                subject="",
                body="",
                framework=framework,
                success=False,
                error=f"Gemini AI generation failed: {str(e)}. Check your API key in Settings."
            )

    def _generate_with_template(self, lead: Lead, framework: str, context: str, error_msg: str = None) -> EmailResult:
        """Generate email using static templates (fallback)."""
        subject = ""
        body = ""
        
        owner = lead.owner_name or "there"
        business = lead.business_name
        service = self.service_description or "[My Service]"
        sender = self.sender_name
        
        if framework == "AIDA":
            subject = f"Question about {business}"
            body = f"""Hi {owner},

I was looking at {business} online and noticed you're doing great work.

However, I saw an opportunity to improve your online presence that many businesses miss.

{service}

Are you open to a 10-minute chat this week?

Best,
{sender}"""
        else:  # PAS
            subject = f"Fixing {business}'s growth bottleneck"
            body = f"""Hi {owner},

Running a business like {business} is tough when you have to juggle everything yourself.

Most owners struggle to consistent lead flow without spending hours on outreach.

{service} helps you solve this permanently.

Can I send you a 1-minute video explaining how?

Best,
{sender}"""

        msg = f"Generated using basic template (API key missing)" if not error_msg else f"Fallback to template. {error_msg}"
        
        return EmailResult(
            subject=subject,
            body=body,
            framework=framework,
            success=True,
            error=msg
        )
    
    def compose_for_lead(self, lead: Lead, framework: str = None) -> Lead:
        """
        Generate email and update lead object.
        
        Args:
            lead: Lead to generate email for
            framework: Email framework to use
            
        Returns:
            Updated lead with email content
        """
        result = self.compose(lead, framework)
        
        if result.success:
            lead.set_email_content(
                subject=result.subject,
                body=result.body,
                framework=result.framework
            )
        
        return lead
    
    def compose_batch(
        self,
        leads: List[Lead],
        framework: str = None,
        progress_callback=None
    ) -> List[Lead]:
        """
        Generate emails for multiple leads.
        
        Args:
            leads: List of leads to process
            framework: Email framework to use
            progress_callback: Optional callback(current, total) for progress
            
        Returns:
            List of leads with email content
        """
        results = []
        total = len(leads)
        
        for i, lead in enumerate(leads):
            if progress_callback:
                progress_callback(i + 1, total)
            
            updated_lead = self.compose_for_lead(lead, framework)
            results.append(updated_lead)
        
        return results


# Convenience function
def generate_email(
    business_name: str,
    owner_name: str = "",
    website: str = "",
    framework: str = "AIDA",
    service_description: str = "",
    sender_name: str = "Your Name"
) -> EmailResult:
    """
    Simple function to generate a cold email.
    
    Args:
        business_name: Name of the business
        owner_name: Contact person's name
        website: Business website
        framework: "AIDA" or "PAS"
        service_description: What you're offering
        sender_name: Your name
        
    Returns:
        EmailResult with generated email
    """
    lead = Lead(
        business_name=business_name,
        owner_name=owner_name,
        website=website
    )
    
    composer = EmailComposer(
        sender_name=sender_name,
        service_description=service_description
    )
    
    return composer.compose(lead, framework)
