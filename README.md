# TaxTruth

AI-powered tax strategy analysis platform. Clients submit financial questionnaires + upload tax documents (PDF), the system extracts data, matches eligible tax strategies via a rule engine, and generates a professional AI-written consultancy report (PDF/Word export).

## Architecture

```
PDF Upload → Extraction (text/OCR/tables) → Structured Figures (GPT) → Postgres + Neo4j (Graph RAG)
Questionnaire → Postgres
                                    ↓
Rule Engine (matches ~150 strategies against client data)
                                    ↓
Tax Calculator (real 2024 IRS brackets, payroll/SE tax, reasonable-comp savings)
                                    ↓
LLM Report Generator (GPT-4o, structured JSON, grounded in calculated + extracted figures)
                                    ↓
Frontend Dashboard (charts, risk badges) + PDF/Word Export
```

## Stack

- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL (structured client/questionnaire data)
- **Graph DB**: Neo4j (document knowledge graph for Graph RAG)
- **LLM**: OpenAI GPT-4o
- **Frontend**: Single-file HTML/CSS/JS (no build step), Chart.js
- **PDF export**: ReportLab (professional landscape report)
- **Word export**: python-docx
- **PDF parsing**: PyMuPDF, pdfplumber, pytesseract (OCR fallback)

## Setup from scratch

1. Clone repo, open in PyCharm.
2. Create venv:
   ```
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Install Postgres locally. Create database:
   ```
   psql -U postgres -c "CREATE DATABASE taxtruth;"
   ```
4. Install Neo4j Desktop. Create a local DBMS, set password, start it.
5. Install Tesseract OCR (system-level, for scanned PDF fallback).
6. Copy `.env.example` → `.env`, fill in:
   ```
   DATABASE_URL=postgresql://postgres:postgres@localhost:5432/taxtruth
   NEO4J_URI=bolt://localhost:7687
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=password
   OPENAI_API_KEY=your_key
   APP_API_KEY=dev-key-change-me
   ```
7. Run: `uvicorn api.main:app --reload`
8. Open `frontend/index.html` directly in a browser.

## File-by-file guide

### `api/main.py`
FastAPI app. All HTTP endpoints live here. Protected by `x-api-key` header (or `api_key` query param for browser-opened export links). Key endpoints:
- `POST /clients` — create a client
- `POST /clients/{id}/questionnaire/personal` — save personal questionnaire (business structure, income, etc.)
- `POST /clients/{id}/questionnaire/financial` — save financial questionnaire (investments, net worth)
- `POST /clients/{id}/documents` — upload PDF, triggers extraction pipeline
- `POST /clients/{id}/generate-report` — runs rule engine + tax calculator + LLM, returns structured report
- `GET /clients/{id}/reports/{report_id}/export?format=pdf|docx` — download report

### `db/models.py`
SQLAlchemy models: `Client`, `PersonalQuestionnaire`, `FinancialQuestionnaire`, `Document` (stores extracted markdown + structured figures), `Strategy`, `StrategyReport`.

### `db/session.py`
DB engine/session setup, reads `DATABASE_URL` from env.

### `extraction/pdf_extractor.py`
Core PDF pipeline: tries native text layer first (PyMuPDF), falls back to OCR (pytesseract) per-page if no text found. Also extracts tables via pdfplumber.

### `extraction/markdown_serializer.py`
Converts extraction output into clean Markdown (stored on `Document.extracted_markdown`).

### `extraction/financial_extractor.py`
Sends extracted PDF text to GPT-4o to pull exact structured figures (officer compensation, distributions, retained earnings, total assets, etc.) into a fixed JSON schema. Stored on `Document.extracted_figures`. This is what makes the report reference *real* numbers from the tax return instead of hallucinating them.

### `rules/rule_engine.py`
Deterministic condition matcher. Each strategy has a `rule_definition` (JSON logic tree of `all`/`any` conditions on client fields). Returns the list of strategies the client is eligible for. No AI involved — pure logic, auditable.

### `rules/strategy_rules.json`
~150 tax strategies with their eligibility rules (e.g. "S-Corp Reasonable Compensation Planning" requires `has_1120s == true` and `s_corp_officer_comp > 0`).

### `rules/tax_calculator.py`
Real tax math — NOT LLM-generated. 2024 federal brackets, standard deduction, SE tax, payroll FICA, and a reasonable-compensation savings estimator (models shifting officer comp to distributions to save payroll tax). The LLM is instructed to use these calculated numbers as ground truth rather than inventing its own liability figures.

### `graph_rag/graph_store.py`
Neo4j-backed Graph RAG. Chunks document text, extracts entities/relations via GPT, stores as graph nodes, and retrieves relevant chunks by keyword traversal when generating a report. Currently a fallback path — `financial_extractor.py`'s structured figures are the primary grounding source since they're more reliable than graph keyword retrieval.

### `llm/report_generator.py`
Builds the final report. Prompt includes: questionnaire data, document-extracted structured figures, calculated tax liability, matched strategies, and RAG context. System prompt enforces: use calculated liability exactly (don't recompute), never contradict document figures (e.g. don't say "no distributions" if distributions > 0), correct SEP IRA rules for S-Corp shareholder-employees, deadlines must be future-dated. Returns structured JSON matching a fixed schema (executive summary, strategies, risk assessment, action plan, scenario planning, etc.).

### `exports/report_export.py`
Word (.docx) export via python-docx. Simple structured document.

### `exports/report_export_pro.py`
PDF export via ReportLab. Landscape, multi-section, table-based professional report (executive summary table, optimization opportunities table, risk assessment table, scenario planning, action plan).

### `frontend/index.html`
Single-file dashboard. No build tooling — open directly in browser. Contains:
- Step-by-step forms (create client → questionnaires → upload → generate)
- API key sent via `x-api-key` header (hardcoded `API_KEY` constant — change for production)
- Report rendering: hero summary card, stat cards (savings/risk), Chart.js bar chart, strategy cards, risk table, action plan, export buttons

## Known limitations / not production-ready

- **Rule engine conditions are illustrative, not CPA-verified.** Every rule in `strategy_rules.json` needs review against actual current tax code before real client use.
- **No authentication beyond a single shared API key.** No per-user accounts, no RBAC.
- **No input validation** on questionnaire fields.
- **PII stored unencrypted** in Postgres (SSNs, financial data from uploaded returns).
- **No automated tests.**
- **Tax calculator is simplified** — real returns involve far more variables (itemized deductions, AMT, state tax, multiple income types) than the current bracket-only model.
- **Graph RAG retrieval is keyword-based**, not true vector similarity search.

## Recommended next steps for a new developer

1. Add pytest coverage for `rules/rule_engine.py` and `rules/tax_calculator.py` — these are the most safety-critical, most testable pieces.
2. Add real auth (per-user accounts, not a shared static key).
3. Get a licensed CPA/tax attorney to review and correct `strategy_rules.json`.
4. Add field-level input validation (Pydantic models instead of raw `dict` bodies in `api/main.py`).
5. Encrypt sensitive columns at rest or move to a compliant data store.