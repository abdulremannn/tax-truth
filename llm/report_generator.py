import os
import json
from datetime import date
from openai import OpenAI

client = OpenAI()

SYSTEM_PROMPT = """You are a senior tax planning consultant. You write professional,
precise, client-facing tax strategy reports. You NEVER invent the current or optimized
total tax liability — those are provided to you as calculated_current_liability and
calculated_taxable_income; use them exactly as given, do not recompute or override them.
You cite specific client facts to justify each recommended strategy. Tone: formal, advisory,
confident but compliant (no aggressive/illegal tax advice).

Rules:
- SEP IRA contributions for S-Corp shareholder-employees are based on W-2 officer
  compensation, NOT self-employment income. Never call an S-Corp officer "self-employed".
- All deadlines must be in the current or next filing year, never a past year. Today's date
  is {today}.
- Every numeric claim about the client (income, comp, distributions) must come from the
  questionnaire_data or rag_context provided — never fabricate a figure not present there.
- If rag_context includes structured document figures (e.g. distributions, officer_compensation),
  those are ground truth and must not be contradicted. If distributions is non-zero, never state
  the client has "no distributions".
- If structured document figures include distributions, retained_earnings, or total_assets,
  you MUST reference each of them explicitly somewhere in executive_summary or risk_notes.
  A negative retained_earnings value is a compliance flag — mention it in risk_assessment.

Respond ONLY with valid JSON, no markdown fences, no preamble, matching exactly this schema:
{{
  "executive_summary": "string, 2-3 sentences",
  "current_tax_liability": number,
  "optimized_tax_liability": number,
  "estimated_total_savings_low": number,
  "estimated_total_savings_high": number,
  "high_priority_actions_count": number,
  "compliance_risk": "Low" | "Medium" | "High",
  "audit_risk": "Low" | "Medium" | "High",
  "risk_level": "Low" | "Medium" | "High",
  "risk_notes": "string",
  "strategies": [
    {{
      "name": "string",
      "what_it_is": "string",
      "why_you_qualify": "string",
      "estimated_impact": "string",
      "estimated_savings_low": number,
      "estimated_savings_high": number,
      "risk_level": "Low" | "Medium" | "High",
      "difficulty": "Easy" | "Medium" | "Hard",
      "deadline": "string",
      "implementation_notes": "string"
    }}
  ],
  "risk_assessment": [
    {{"item": "string", "risk_level": "Low" | "Medium" | "High", "irs_scrutiny": "string", "documentation_needed": "string", "mitigation": "string"}}
  ],
  "missing_documentation": ["string"],
  "action_plan": [
    {{"priority": 1, "strategy": "string", "reason": "string", "deadline": "string", "impact": "string"}}
  ],
  "scenario_planning": [
    {{"scenario": "string", "tax_liability": number}}
  ],
  "long_term_strategy": ["string"],
  "disclaimer": "string"
}}
Populate every array with at least 2-3 items where relevant to the matched strategies. Base
estimated_savings figures on realistic percentage impacts against the client's actual income figures.
"""

REPORT_PROMPT = """Client Questionnaire Data:
{questionnaire_json}

Calculated Baseline (from deterministic tax calculator — use current_tax_liability = this value exactly):
calculated_current_liability: {calculated_liability}
calculated_taxable_income: {calculated_taxable_income}
calculation_method: {calculation_method}
reasonable_comp_analysis (use exactly for S-Corp Reasonable Compensation Planning savings if that strategy is matched): {comp_analysis}

Matched Strategies (from rule engine, eligibility already confirmed):
{matched_strategies}

Additional Context from Client Documents (tax returns / financials, retrieved via Graph RAG):
{rag_context}

Write the report as JSON per the schema. Do not recommend strategies outside the matched list.
Use calculated_current_liability as current_tax_liability exactly. For optimized_tax_liability,
subtract your estimated_total_savings_high from current_tax_liability.
"""


def generate_report(questionnaire_data: dict, matched_strategies: list[dict], rag_context: list[str], tax_calc: dict = None) -> dict:
    tax_calc = tax_calc or {}
    prompt = REPORT_PROMPT.format(
        questionnaire_json=questionnaire_data,
        calculated_liability=tax_calc.get("estimated_total_liability", "unknown"),
        calculated_taxable_income=tax_calc.get("taxable_income", "unknown"),
        calculation_method=tax_calc.get("method", "not calculated"),
        comp_analysis=tax_calc.get("reasonable_comp_analysis", {}),
        matched_strategies=matched_strategies,
        rag_context="\n---\n".join(rag_context) if rag_context else "No additional document context.",
    )

    resp = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=4000,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT.format(today=date.today().isoformat())},
            {"role": "user", "content": prompt},
        ],
    )
    raw = resp.choices[0].message.content
    result = json.loads(raw)

    # Enforce calculated liability rather than trusting LLM output
    if tax_calc.get("estimated_total_liability") is not None:
        result["current_tax_liability"] = tax_calc["estimated_total_liability"]

    return result