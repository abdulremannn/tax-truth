from sqlalchemy import Column, Integer, String, Boolean, Float, Date, JSON, ForeignKey, Text
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True)
    client_name = Column(String)
    client_email = Column(String)

    personal_questionnaire = relationship("PersonalQuestionnaire", back_populates="client", uselist=False)
    financial_questionnaire = relationship("FinancialQuestionnaire", back_populates="client", uselist=False)
    documents = relationship("Document", back_populates="client")
    strategy_reports = relationship("StrategyReport", back_populates="client")


class PersonalQuestionnaire(Base):
    __tablename__ = "personal_questionnaires"

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"))

    date_of_birth = Column(Date, nullable=True)
    cell_phone = Column(String)
    home_address = Column(String)
    spouse_name = Column(String)
    spouse_date_of_birth = Column(Date, nullable=True)
    spouse_annual_compensation = Column(Float, default=0)
    spouse_works_in_practice = Column(Boolean, default=False)
    no_of_children = Column(Integer, default=0)
    children = Column(JSON, default=list)

    primary_business_name = Column(String)
    business_address = Column(String)
    business_phone_number = Column(String)
    business_website = Column(String)
    business_structure = Column(String, default="Sole proprietorship")
    why_this_structure = Column(Text)
    employees_count = Column(Integer, default=0)
    business_ownership_percentage = Column(Float, default=0)
    secondary_business_ownership = Column(Float, default=0)
    third_business_ownership = Column(Float, default=0)

    has_1120s = Column(Boolean, default=False)
    has_1120 = Column(Boolean, default=False)
    has_1065 = Column(Boolean, default=False)
    s_corp_officer_comp = Column(Float, default=0)
    s_corp_distributions = Column(Float, default=0)
    c_corp_retained_earnings_actual = Column(Float, default=0)
    partnership_guaranteed_payments = Column(Float, default=0)
    management_company_revenue = Column(Float, default=0)

    owns_practice_building = Column(Boolean, default=False)
    building_purchase_price = Column(Float, default=0)
    building_placed_in_service_year = Column(Integer, default=0)
    planned_equipment_purchase = Column(Float, default=0)
    annual_equipment_lease_payments = Column(Float, default=0)

    monthly_lifestyle_expenses = Column(Float, default=0)
    monthly_medical_insurance = Column(Float, default=0)
    premium_payer = Column(String)

    owns_home = Column(Boolean, default=False)
    owns_primary_home = Column(Boolean, default=False)
    owns_secondary_home = Column(Boolean, default=False)
    secondary_home_count = Column(Integer, default=0)
    owns_boat_or_yacht = Column(Boolean, default=False)
    has_rental_properties = Column(Boolean, default=False)
    rental_property_count = Column(Integer, default=0)
    has_short_term_rental = Column(Boolean, default=False)
    real_estate_professional_hours = Column(Float, default=0)
    other_work_hours = Column(Float, default=0)

    planning_retirement = Column(Boolean, default=False)
    retirement_age = Column(Integer, default=0)
    long_term_financial_goals = Column(Text)
    practice_sale_planned = Column(Boolean, default=False)

    has_form_4797 = Column(Boolean, default=False)
    has_form_6252 = Column(Boolean, default=False)
    installment_sale_proceeds = Column(Float, default=0)
    section_1231_gain = Column(Float, default=0)
    nol_carryover_amount = Column(Float, default=0)
    iso_spread_amount = Column(Float, default=0)
    has_dso_equity = Column(Boolean, default=False)

    advisor1_description = Column(Text)
    relationship_length = Column(String)
    advisor_annual_cost = Column(String)
    advisor_rating = Column(Integer, default=1)
    advisor_rating_explanation = Column(Text)

    client_annual_compensation = Column(Float, default=0)
    household_income = Column(Float, default=0)
    future_income_year = Column(String)
    main_residence_details = Column(Text)
    secondary_home_details = Column(Text)
    pnl = Column(Text)
    tax_return_file_1 = Column(String)
    tax_return_file_2 = Column(String)

    client = relationship("Client", back_populates="personal_questionnaire")


class FinancialQuestionnaire(Base):
    __tablename__ = "financial_questionnaires"

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"))

    client_phone = Column(String)
    dob = Column(Date, nullable=True)
    federal_tax_returns = Column(Text)
    extraordinary_items = Column(Text)
    new_income_sources = Column(Text)
    retirement_age = Column(Integer, nullable=True)
    desired_retirement_income = Column(Float, default=0)
    retirement_plan = Column(Text)

    cash_on_hand = Column(Float, default=0)
    real_estate_values = Column(Float, default=0)
    automobile_values = Column(Float, default=0)
    mortgages = Column(Text)
    commercial_property = Column(Boolean, default=False)
    property_taxes = Column(Boolean, default=False)

    new_employees_per_year = Column(Integer, default=0)
    take_credit_cards = Column(Boolean, default=False)
    credit_card_type = Column(String)
    workers_comp_premium_over_40k = Column(Boolean, default=False)
    self_insured = Column(Boolean, default=False)
    any_savings = Column(String, default="0")

    has_life_insurance = Column(Boolean, default=False)
    insured_name = Column(String)
    death_benefit_amount = Column(Float, default=0)
    insurance_type = Column(String)
    insurance_policy_type = Column(String)
    annual_premium = Column(Float, default=0)
    annual_premium_1 = Column(String)
    total_cash_value = Column(Float, default=0)

    estimated_net_worth_range = Column(String)
    current_securities_investments = Column(Float, default=0)
    c_corp_retained_earnings = Column(Float, default=0)

    client = relationship("Client", back_populates="financial_questionnaire")


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"))
    filename = Column(String)
    doc_type = Column(String)  # tax_return, pnl, other
    storage_path = Column(String)
    extraction_status = Column(String, default="pending")  # pending, processing, done, failed
    extracted_markdown = Column(Text, nullable=True)
    extracted_figures = Column(JSON, nullable=True)

    client = relationship("Client", back_populates="documents")


class Strategy(Base):
    __tablename__ = "strategies"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    rule_definition = Column(JSON, nullable=True)  # eligibility conditions
    description = Column(Text, nullable=True)


class StrategyReport(Base):
    __tablename__ = "strategy_reports"

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"))
    matched_strategies = Column(JSON)  # list of strategy ids + rule scores
    llm_summary = Column(JSON)
    report_path = Column(String, nullable=True)

    client = relationship("Client", back_populates="strategy_reports")