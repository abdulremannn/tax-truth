import os
import json
import shutil
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from fastapi.responses import FileResponse
from db.session import get_db, engine
from db.models import Base, Client, PersonalQuestionnaire, FinancialQuestionnaire, Document, StrategyReport
from extraction.pdf_extractor import extract_document
from extraction.markdown_serializer import to_markdown
from extraction.financial_extractor import extract_financial_figures
from rules.rule_engine import match_strategies, load_strategies_from_file
from rules.tax_calculator import estimate_current_liability, estimate_reasonable_comp_savings
from graph_rag.graph_store import GraphRAGStore
from llm.report_generator import generate_report
from exports.report_export import export_docx
from exports.report_export_pro import export_pdf

Base.metadata.create_all(bind=engine)

API_KEY = os.getenv("APP_API_KEY", "dev-key-change-me")


def verify_api_key(x_api_key: str = Header(None), api_key: str = None):
    key = x_api_key or api_key
    if key != API_KEY:
        raise HTTPException(401, "Invalid API key")


app = FastAPI(title="TaxTruth API", dependencies=[Depends(verify_api_key)])

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "storage/uploads"
EXPORT_DIR = "storage/exports"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(EXPORT_DIR, exist_ok=True)

STRATEGY_RULES_PATH = "rules/strategy_rules.json"


@app.post("/clients")
def create_client(client_name: str, client_email: str, db: Session = Depends(get_db)):
    client = Client(client_name=client_name, client_email=client_email)
    db.add(client)
    db.commit()
    db.refresh(client)
    return {"id": client.id}


@app.post("/clients/{client_id}/questionnaire/personal")
def submit_personal_questionnaire(client_id: int, data: dict, db: Session = Depends(get_db)):
    client = db.query(Client).get(client_id)
    if not client:
        raise HTTPException(404, "Client not found")

    pq = PersonalQuestionnaire(client_id=client_id, **_filter_fields(data, PersonalQuestionnaire))
    db.add(pq)
    db.commit()
    return {"status": "saved"}


@app.post("/clients/{client_id}/questionnaire/financial")
def submit_financial_questionnaire(client_id: int, data: dict, db: Session = Depends(get_db)):
    client = db.query(Client).get(client_id)
    if not client:
        raise HTTPException(404, "Client not found")

    fq = FinancialQuestionnaire(client_id=client_id, **_filter_fields(data, FinancialQuestionnaire))
    db.add(fq)
    db.commit()
    return {"status": "saved"}


@app.post("/clients/{client_id}/documents")
async def upload_document(client_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    client = db.query(Client).get(client_id)
    if not client:
        raise HTTPException(404, "Client not found")

    path = os.path.join(UPLOAD_DIR, f"{client_id}_{file.filename}")
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    doc = Document(client_id=client_id, filename=file.filename, storage_path=path, extraction_status="processing")
    db.add(doc)
    db.commit()
    db.refresh(doc)

    try:
        extraction = extract_document(path)
        markdown = to_markdown(extraction, doc_title=file.filename)
        doc.extracted_markdown = markdown
        doc.extraction_status = "done"
        doc.extracted_figures = extract_financial_figures(extraction["full_text"])
        db.commit()

        store = GraphRAGStore()
        store.ingest_document(client_id, doc.id, extraction["full_text"])
        store.close()
    except Exception as e:
        doc.extraction_status = "failed"
        db.commit()
        raise HTTPException(500, f"Extraction failed: {e}")

    return {"document_id": doc.id, "status": doc.extraction_status}


@app.post("/clients/{client_id}/generate-report")
def generate_client_report(client_id: int, db: Session = Depends(get_db)):
    client = db.query(Client).get(client_id)
    if not client:
        raise HTTPException(404, "Client not found")

    pq = client.personal_questionnaire
    fq = client.financial_questionnaire
    if not pq:
        raise HTTPException(400, "Personal questionnaire not submitted")

    client_data = {c.name: getattr(pq, c.name) for c in pq.__table__.columns}
    if fq:
        client_data.update({c.name: getattr(fq, c.name) for c in fq.__table__.columns})

    strategies = load_strategies_from_file(STRATEGY_RULES_PATH)
    matched = match_strategies(client_data, strategies)
    tax_calc = estimate_current_liability(client_data)
    comp_savings = estimate_reasonable_comp_savings(client_data.get("s_corp_officer_comp") or 0)
    tax_calc["reasonable_comp_analysis"] = comp_savings

    # Prefer structured extracted figures over raw markdown dump
    docs = db.query(Document).filter(Document.client_id == client_id, Document.extraction_status == "done").all()
    document_figures = [d.extracted_figures for d in docs if d.extracted_figures]

    rag_context = [f"Structured document figures: {json.dumps(document_figures)}"] if document_figures else []

    store = GraphRAGStore()
    query_terms = [m["name"] for m in matched] or ["income", "deduction"]
    graph_context = store.retrieve_context(client_id, query_terms)
    store.close()
    rag_context += graph_context

    if not rag_context:
        for d in docs:
            if d.extracted_markdown:
                rag_context.append(d.extracted_markdown[:4000])

    summary = generate_report(client_data, matched, rag_context, tax_calc)

    report = StrategyReport(client_id=client_id, matched_strategies=matched, llm_summary=summary)
    db.add(report)
    db.commit()
    db.refresh(report)

    return {"report_id": report.id, "matched_strategies": matched, "report": summary}


def _filter_fields(data: dict, model) -> dict:
    valid_cols = {c.name for c in model.__table__.columns}
    return {k: v for k, v in data.items() if k in valid_cols}


@app.get("/clients/{client_id}/reports/latest")
def get_latest_report(client_id: int, db: Session = Depends(get_db)):
    report = (
        db.query(StrategyReport)
        .filter(StrategyReport.client_id == client_id)
        .order_by(StrategyReport.id.desc())
        .first()
    )
    if not report:
        raise HTTPException(404, "No report found")
    return {"report_id": report.id, "matched_strategies": report.matched_strategies, "report": report.llm_summary}


@app.get("/clients/{client_id}/reports/{report_id}/export")
def export_report(client_id: int, report_id: int, format: str = "pdf", db: Session = Depends(get_db)):
    report = db.query(StrategyReport).get(report_id)
    if not report or report.client_id != client_id:
        raise HTTPException(404, "Report not found")

    client = db.query(Client).get(client_id)
    out_path = os.path.join(EXPORT_DIR, f"report_{report_id}.{format}")

    summary = report.llm_summary
    if isinstance(summary, str):
        summary = json.loads(summary)

    if format == "docx":
        export_docx(summary, client.client_name, out_path)
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    elif format == "pdf":
        export_pdf(summary, client.client_name, out_path)
        media_type = "application/pdf"
    else:
        raise HTTPException(400, "format must be pdf or docx")

    return FileResponse(out_path, media_type=media_type, filename=os.path.basename(out_path))