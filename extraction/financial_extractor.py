import json
from openai import OpenAI

client = OpenAI()

EXTRACTION_PROMPT = """Extract exact financial figures from this tax document text.
Return ONLY JSON, no markdown, no preamble:
{{
  "entity_name": "string or null",
  "tax_year": "string or null",
  "form_type": "string or null (e.g. 1120-S, 1065, 1040)",
  "ordinary_business_income": number or null,
  "officer_compensation": number or null,
  "distributions": number or null,
  "total_assets": number or null,
  "retained_earnings": number or null,
  "gross_receipts": number or null,
  "shareholder_basis_notes": "string or null",
  "other_notable_figures": {{"description": number}}
}}
Use null for anything not explicitly present. Do not guess or estimate.

Document text:
{text}
"""


def extract_financial_figures(document_text: str) -> dict:
    resp = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=800,
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": EXTRACTION_PROMPT.format(text=document_text[:12000])}],
    )
    try:
        return json.loads(resp.choices[0].message.content)
    except json.JSONDecodeError:
        return {}