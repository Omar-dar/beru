"""Extract text from PDFs and split into RAG-friendly chunks."""

import re
import uuid
from pathlib import Path

CHUNK_SIZE = 900
CHUNK_OVERLAP = 120
MIN_CHUNK_LEN = 40


def extract_pdf_text(pdf_path):
    """
    Extract text page-by-page from a PDF.
    Uses PyMuPDF first; pdfplumber as fallback for sparse pages.
    Returns list of {"page": int, "text": str}.
    """
    pages = _extract_with_pymupdf(pdf_path)

    if not any(p['text'].strip() for p in pages):
        pages = _extract_with_pdfplumber(pdf_path)

    cleaned = []
    for page in pages:
        text = _normalize_whitespace(page['text'])
        if text:
            cleaned.append({'page': page['page'], 'text': text})

    return cleaned


def _extract_with_pymupdf(pdf_path):
    fitz = _import_fitz()
    pages = []
    with fitz.open(pdf_path) as doc:
        for i, page in enumerate(doc, start=1):
            text = page.get_text('text') or ''
            pages.append({'page': i, 'text': text})
    return pages


def _import_fitz():
    try:
        import fitz
        return fitz
    except ImportError:
        try:
            import pymupdf as fitz
            return fitz
        except ImportError as exc:
            raise ImportError(
                'PyMuPDF is not installed in this Python. '
                'From the beru folder run: .venv/bin/python3 -m pip install pymupdf pdfplumber '
                'then start the API with: .venv/bin/python3 beru.py api'
            ) from exc


def _extract_with_pdfplumber(pdf_path):
    try:
        import pdfplumber
    except ImportError as exc:
        raise ImportError(
            'pdfplumber is not installed. Run: pip install pymupdf pdfplumber'
        ) from exc

    pages = []
    with pdfplumber.open(pdf_path) as doc:
        for i, page in enumerate(doc.pages, start=1):
            text = page.extract_text() or ''
            pages.append({'page': i, 'text': text})
    return pages


def _normalize_whitespace(text):
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r'[ \t]+\n', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def chunk_pages(pages, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """
    Split page text into overlapping chunks for embedding search.
    Each chunk: {chunk_index, page, text, char_count}.
    """
    chunks = []
    chunk_index = 0

    for page_info in pages:
        page_num = page_info['page']
        text = page_info['text']
        if len(text) <= chunk_size:
            if len(text) >= MIN_CHUNK_LEN:
                chunks.append({
                    'chunk_index': chunk_index,
                    'page': page_num,
                    'text': text,
                    'char_count': len(text),
                })
                chunk_index += 1
            continue

        start = 0
        while start < len(text):
            end = start + chunk_size
            piece = text[start:end].strip()
            if len(piece) >= MIN_CHUNK_LEN:
                chunks.append({
                    'chunk_index': chunk_index,
                    'page': page_num,
                    'text': piece,
                    'char_count': len(piece),
                })
                chunk_index += 1
            if end >= len(text):
                break
            start = max(end - overlap, start + 1)

    return chunks


def make_document_id():
    return f'doc_{uuid.uuid4().hex[:12]}'
