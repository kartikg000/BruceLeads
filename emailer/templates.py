"""
Email Templates
Prompt templates for AIDA and PAS copywriting frameworks.
"""


AIDA_TEMPLATE = """You are an expert cold email copywriter specializing in B2B outreach. 
Write a brief, personalized cold email using the AIDA framework:

- **Attention**: Open with a hook that grabs attention (personalized observation, compliment, or intriguing question)
- **Interest**: Build interest by connecting to their specific situation
- **Desire**: Create desire by hinting at benefits without being salesy  
- **Action**: End with a soft, low-commitment call to action

## Lead Information:
- Business Name: {business_name}
- Owner/Contact Name: {owner_name}
- Website: {website}
- Industry Context: {intent_signal}

## Your Service/Offer:
{service_description}

## Tone & Style:
{tone_instructions}

## Requirements:
- Length: Under {max_words} words (this is critical - be concise!)
- Avoid: Generic phrases like "I hope this finds you well", spam triggers, being pushy
- CTA: Suggest a brief 15-minute call or simple reply
- Personalization: Reference their specific business by name

## Output Format:
Return ONLY the email in this exact format:
SUBJECT: [Your subject line here]
---
[Your email body here]

[Signature with your name: {sender_name}]"""


PAS_TEMPLATE = """You are an expert cold email copywriter specializing in B2B outreach.
Write a brief, personalized cold email using the PAS framework:

- **Problem**: Identify a specific pain point they likely face
- **Agitate**: Briefly emphasize the impact of this problem  
- **Solution**: Position your offer as the solution (without being salesy)

## Lead Information:
- Business Name: {business_name}
- Owner/Contact Name: {owner_name}
- Website: {website}
- Industry Context: {intent_signal}

## Your Service/Offer:
{service_description}

## Tone & Style:
{tone_instructions}

## Requirements:
- Length: Under {max_words} words (this is critical - be concise!)
- Avoid: Generic phrases, fear-mongering, spam triggers
- CTA: Suggest a brief 15-minute call or simple reply
- Personalization: Reference their specific business by name

## Output Format:
Return ONLY the email in this exact format:
SUBJECT: [Your subject line here]
---
[Your email body here]

[Signature with your name: {sender_name}]"""


FOLLOWUP_TEMPLATE = """You are an expert cold email copywriter.
Write a brief follow-up email to someone who hasn't responded to your initial outreach.

## Original Context:
- Business Name: {business_name}
- Owner/Contact Name: {owner_name}
- Days Since Last Email: {days_since}

## Your Service/Offer:
{service_description}

## Tone & Style:
{tone_instructions}

## Requirements:
- Length: Under 60 words
- Approach: Provide additional value or a fresh angle
- Avoid: "Just following up", "Checking in", guilt language

## Output Format:
Return ONLY the email in this exact format:
SUBJECT: Re: [Original subject theme]
---
[Your follow-up body here]

[Signature with your name: {sender_name}]"""


# Default service description if user doesn't provide one
DEFAULT_SERVICE = """We help small businesses build professional websites that attract more 
customers. Our approach focuses on clean design, fast loading, and high conversion rates."""


def get_template(framework: str) -> str:
    """
    Get the prompt template for a given framework.
    
    Args:
        framework: "AIDA", "PAS", or "FOLLOWUP"
        
    Returns:
        Template string
    """
    templates = {
        "AIDA": AIDA_TEMPLATE,
        "PAS": PAS_TEMPLATE,
        "FOLLOWUP": FOLLOWUP_TEMPLATE
    }
    return templates.get(framework.upper(), AIDA_TEMPLATE)


def format_template(
    framework: str,
    business_name: str,
    owner_name: str = "",
    website: str = "",
    intent_signal: str = "",
    service_description: str = "",
    sender_name: str = "Your Name",
    max_words: int = 120,
    tone: str = "",
    **kwargs
) -> str:
    """
    Format a template with lead data.
    
    Args:
        framework: Template framework to use
        business_name: Name of the business
        owner_name: Contact person's name
        website: Business website URL
        intent_signal: Context about why they're a good lead
        service_description: What you're offering
        sender_name: Your name for the signature
        max_words: Maximum word count
        tone: Desired email tone
        **kwargs: Additional template variables
        
    Returns:
        Formatted prompt ready for LLM
    """
    template = get_template(framework)
    
    # Sanitize user-supplied values to prevent prompt injection and limit length
    def _sanitize(val: str, max_len: int = 500) -> str:
        if not val:
            return val
        return val[:max_len]

    business_name = _sanitize(business_name, 200)
    owner_name = _sanitize(owner_name, 200) if owner_name else "there"
    website = _sanitize(website, 500)
    intent_signal = _sanitize(intent_signal, 500) if intent_signal else "Local business looking to grow their online presence"
    service_description = _sanitize(service_description, 1000) if service_description else DEFAULT_SERVICE
    sender_name = _sanitize(sender_name, 100)
    tone = _sanitize(tone, 200) if tone else ""
    
    # Build tone instructions
    if tone:
        tone_instructions = f"Write in a {tone} tone. Match this style throughout the entire email — subject line, opening, body, and sign-off."
    else:
        tone_instructions = "Write in a professional yet conversational tone, with a touch of wit."
    
    # Inject custom instructions if provided
    custom_instructions = kwargs.get('custom_instructions', '')
    custom_section = ""
    if custom_instructions:
        custom_instructions = _sanitize(custom_instructions, 1000)
        custom_section = f"\n## CUSTOM INSTRUCTIONS (IMPORTANT — follow these closely):\n{custom_instructions}\n"
    
    # Remove keys we already handle explicitly to avoid duplicate kwarg errors
    extra_kwargs = {k: v for k, v in kwargs.items() if k not in ('custom_instructions', 'tone')}
    
    formatted = template.format(
        business_name=business_name,
        owner_name=owner_name,
        website=website or "Not available",
        intent_signal=intent_signal,
        service_description=service_description,
        sender_name=sender_name,
        max_words=max_words,
        tone_instructions=tone_instructions,
        **extra_kwargs,
    )
    
    # Insert custom instructions before Requirements
    if custom_section:
        if "## Requirements:" in formatted:
            formatted = formatted.replace("## Requirements:", f"{custom_section}\n## Requirements:")
        else:
            formatted += f"\n{custom_section}"
            
    return formatted
