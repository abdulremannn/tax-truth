FEDERAL_BRACKETS_2024_SINGLE = [
    (0, 11600, 0.10),
    (11600, 47150, 0.12),
    (47150, 100525, 0.22),
    (100525, 191950, 0.24),
    (191950, 243725, 0.32),
    (243725, 609350, 0.35),
    (609350, float("inf"), 0.37),
]

FEDERAL_BRACKETS_2024_MFJ = [
    (0, 23200, 0.10),
    (23200, 94300, 0.12),
    (94300, 201050, 0.22),
    (201050, 383900, 0.24),
    (383900, 487450, 0.32),
    (487450, 731200, 0.35),
    (731200, float("inf"), 0.37),
]

STANDARD_DEDUCTION_2024 = {"single": 14600, "mfj": 29200}

SE_TAX_RATE = 0.153  # Social Security + Medicare, self-employment
SE_TAX_WAGE_BASE_2024 = 168600
FICA_EMPLOYEE_RATE = 0.0765  # employee side (SS 6.2% + Medicare 1.45%)


def calc_federal_tax(taxable_income: float, filing_status: str = "mfj") -> float:
    brackets = FEDERAL_BRACKETS_2024_MFJ if filing_status == "mfj" else FEDERAL_BRACKETS_2024_SINGLE
    tax = 0.0
    for lower, upper, rate in brackets:
        if taxable_income > lower:
            tax += (min(taxable_income, upper) - lower) * rate
        else:
            break
    return round(tax, 2)


def calc_se_tax(net_se_income: float) -> float:
    if net_se_income <= 0:
        return 0.0
    taxable_se = net_se_income * 0.9235
    ss_portion = min(taxable_se, SE_TAX_WAGE_BASE_2024) * 0.124
    medicare_portion = taxable_se * 0.029
    return round(ss_portion + medicare_portion, 2)


def calc_payroll_fica(wages: float) -> float:
    """Employee-side FICA withheld on W-2 wages (employer matches separately)."""
    ss = min(wages, SE_TAX_WAGE_BASE_2024) * 0.062
    medicare = wages * 0.0145
    return round(ss + medicare, 2)

def estimate_reasonable_comp_savings(officer_comp: float, industry_reduction_pct: float = 0.15) -> dict:
    if not officer_comp or officer_comp <= 0:
        return {"shiftable_amount": 0, "estimated_payroll_tax_savings": 0}
    shiftable = round(officer_comp * industry_reduction_pct, 2)
    savings = round(calc_payroll_fica(shiftable) * 2, 2)
    return {"shiftable_amount": shiftable, "estimated_payroll_tax_savings": savings}

def estimate_current_liability(client_data: dict) -> dict:
    """
    Conservative estimate of current federal tax liability based on structured
    questionnaire data. This is NOT a substitute for actual return preparation —
    it gives a directionally correct baseline for report framing.
    """
    business_structure = (client_data.get("business_structure") or "").lower()
    household_income = client_data.get("household_income") or 0
    officer_comp = client_data.get("s_corp_officer_comp") or 0
    filing_status = "mfj" if client_data.get("spouse_name") else "single"

    std_ded = STANDARD_DEDUCTION_2024[filing_status]
    taxable_income = max(household_income - std_ded, 0)
    federal_tax = calc_federal_tax(taxable_income, filing_status)

    payroll_tax = 0.0
    if "s-corp" in business_structure or "s corp" in business_structure:
        payroll_tax = calc_payroll_fica(officer_comp) * 2  # employee + employer share, approx
    elif "sole" in business_structure:
        # rough SE income proxy: household income if no separate SE figure given
        payroll_tax = calc_se_tax(household_income)

    total_liability = round(federal_tax + payroll_tax, 2)

    return {
        "taxable_income": round(taxable_income, 2),
        "federal_income_tax": federal_tax,
        "payroll_or_se_tax": payroll_tax,
        "estimated_total_liability": total_liability,
        "filing_status": filing_status,
        "method": "2024 IRS brackets, standard deduction, approximate payroll/SE tax — not a full return calculation",
    }