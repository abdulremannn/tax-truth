import fitz  # PyMuPDF
import pdfplumber
import pytesseract
from PIL import Image
import io


def extract_text_layer(pdf_path: str) -> list[dict]:
    """Extract native text per page using PyMuPDF."""
    pages = []
    doc = fitz.open(pdf_path)
    for i, page in enumerate(doc):
        text = page.get_text("text")
        pages.append({"page": i + 1, "text": text, "has_text": bool(text.strip())})
    doc.close()
    return pages


def extract_tables(pdf_path: str) -> list[dict]:
    """Extract tables per page using pdfplumber."""
    tables_out = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            tables = page.extract_tables()
            if tables:
                tables_out.append({"page": i + 1, "tables": tables})
    return tables_out


def ocr_page(pdf_path: str, page_number: int, zoom: int = 3) -> str:
    """OCR fallback for scanned pages (no text layer)."""
    doc = fitz.open(pdf_path)
    page = doc[page_number - 1]
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    text = pytesseract.image_to_string(img)
    doc.close()
    return text


def extract_document(pdf_path: str) -> dict:
    """
    Full pipeline: text layer first, OCR fallback for pages without text,
    plus table extraction.
    """
    pages = extract_text_layer(pdf_path)

    for p in pages:
        if not p["has_text"]:
            p["text"] = ocr_page(pdf_path, p["page"])
            p["source"] = "ocr"
        else:
            p["source"] = "text_layer"

    tables = extract_tables(pdf_path)

    return {
        "pages": pages,
        "tables": tables,
        "full_text": "\n\n".join(p["text"] for p in pages),
    }
