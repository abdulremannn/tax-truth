# TaxTruth

## Setup (PyCharm)
1. Open this folder as project root.
2. Create venv, install: `pip install -r requirements.txt`
3. Install Tesseract OCR (system-level): https://github.com/tesseract-ocr/tesseract
4. Install Postgres + Neo4j locally (or via Docker).
5. Copy `.env.example` to `.env`, fill in DB creds + `ANTHROPIC_API_KEY`.
6. Run: `uvicorn api.main:app --reload`
7. Open http://127.0.0.1:8000/docs for Swagger UI to test endpoints.

## Flow
1. POST /clients -> create client
2. POST /clients/{id}/questionnaire/personal
3. POST /clients/{id}/questionnaire/financial
4. POST /clients/{id}/documents -> upload PDFs (tax returns, P&L)
5. POST /clients/{id}/generate-report -> rule engine match + Graph RAG context + LLM report

## Next steps
- Add auth
- Expand rules/strategy_rules.json to cover all ~150 strategies
- Add PDF/Word export of generated report
- Frontend (React) for questionnaire forms + report viewer
