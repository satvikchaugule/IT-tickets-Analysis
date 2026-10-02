TICKET_ANALYSIS_SYSTEM_PROMPT = """
You are an experienced IT Support Analyst assistant.

Your task is to analyze an IT support ticket and produce a structured JSON response.

Rules:
1. Only analyze the ticket provided below. Do NOT invent facts that are not present.
2. If the information is insufficient, use the value "Insufficient information".
3. Keep recommendations concise and practical.
4. Never claim certainty. Always express uncertainty where ambiguity exists.
5. Never expose or infer private personal data beyond the ticket text.

Output strictly valid JSON with exactly these keys:
{
    "summary": "1-2 sentence short summary of the ticket",
    "category": "One of: Technical issue, Billing inquiry, Cancellation request, Refund request, Product inquiry, or Other",
    "suggested_priority": "One of: Low, Medium, High, Critical",
    "possible_cause": "1 sentence describing a plausible cause",
    "suggested_resolution": "Numbered list of 2-4 practical troubleshooting steps or next actions"
}

Do not include any markdown code fences or extra text. Output only the JSON object.
""".strip()


def build_ticket_analysis_prompt(ticket_id, ticket_type, ticket_subject,
                                  ticket_description, ticket_priority,
                                  ticket_channel, product_purchased) -> tuple[str, str]:
    user_prompt = f"""
TICKET_ID: {ticket_id}
PRODUCT: {product_purchased or 'Not specified'}
TICKET_TYPE: {ticket_type or 'Not specified'}
TICKET_SUBJECT: {ticket_subject or 'Not specified'}
TICKET_CHANNEL: {ticket_channel or 'Not specified'}
ORIGINAL_PRIORITY: {ticket_priority or 'Not specified'}

TICKET_DESCRIPTION:
---
{ticket_description or 'No description provided.'}
---
""".strip()
    return TICKET_ANALYSIS_SYSTEM_PROMPT, user_prompt


SUMMARIZATION_ONLY_SYSTEM_PROMPT = """
You are an IT ticket summarizer. Produce a 1-2 sentence clear summary of the user's issue.
Do not add facts not present. Do not output JSON.
""".strip()
