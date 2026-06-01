"""Persistent vector index for uploaded PDF documents."""

import json
import os
import shutil
from datetime import datetime

import numpy as np

from src.document_loader import chunk_pages, extract_pdf_text, make_document_id
from src.document_analysis import analyze_document_text, format_analysis_notes

DOCUMENTS_DIR = 'data/documents'
MANIFEST_PATH = os.path.join(DOCUMENTS_DIR, 'manifest.json')

DOCUMENT_QUESTION_TRIGGERS = [
    'summarize', 'summary', 'summarise', 'document', 'pdf', 'uploaded',
    'this file', 'the file', 'the document', 'in the document', 'from the document',
    'according to', 'what does it say', 'what does the', 'page ', 'pages ',
    'main points', 'key points', 'tell me about this', 'explain this document',
    'what is this about', 'what is it about', 'what is this document about',
    'read this', 'in this pdf', 'my cv', 'the cv', 'this cv', 'my resume',
    'the resume', 'curriculum vitae', 'what did it say', 'what does it say about',
    'sammanfatta', 'dokumentet', 'pdfen', 'filen', 'mitt cv', 'cv:t',
]

RE_READ_DOCUMENT_PATTERNS = (
    r'\bread(?:ing)?\s+(?:it\s+)?again\b',
    r'\blook(?:ing)?\s+(?:at\s+)?(?:it\s+)?again\b',
    r'\btry(?:ing)?\s+(?:to\s+)?read(?:ing)?(?:\s+it)?\s+again\b',
    r'\bcheck(?:ing)?\s+(?:it\s+)?again\b',
    r'\btake another look\b',
    r'\bläs(?:a)?\s+(?:det\s+)?igen\b',
)

REMEMBER_DOCUMENT_PATTERNS = (
    r'\bremember\b.*\b(doc\w*|pdf|cv|resume|file|document|information|info|those)\b',
    r'\b(doc\w*|pdf|cv|resume|file|document)\b.*\bremember\b',
    r'\bstore\b.*\b(doc\w*|pdf|cv|information|info)\b',
    r'\bsave\b.*\b(doc\w*|pdf|cv|information|info)\b',
    r'\bkom\s+ih[åa]g\b.*\b(dok\w*|pdf|cv|filen|information)\b',
    r'\bwill you remember\b.*\b(doc\w*|information|info|about me)\b',
)

PRE_UPLOAD_DOCUMENT_TRIGGERS = (
    r'\bwill send\b', r'\bgoing to send\b', r"\bi'll send\b", r'\bill send\b',
    r'\babout to send\b', r'\bwant to send\b', r'\bcan i send\b',
    r'\bsending you a\b', r'\bsend you a doc', r'\bkommer skicka\b',
    r'\bska skicka\b',
)


class TildDocumentIndex:

    def __init__(self, embed_model, base_dir=DOCUMENTS_DIR):
        self.model = embed_model
        self.base_dir = base_dir
        self.manifest_path = os.path.join(base_dir, 'manifest.json')
        self.files_dir = os.path.join(base_dir, 'files')
        os.makedirs(self.files_dir, exist_ok=True)

        self.documents = {}
        self.chunks = []
        self.embeddings = np.zeros((0, 384), dtype=np.float32)
        self._load_manifest()

    def _load_manifest(self):
        if not os.path.exists(self.manifest_path):
            self._save_manifest()
            return

        with open(self.manifest_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.documents = {d['id']: d for d in data.get('documents', [])}
        self.chunks = data.get('chunks', [])

        emb_path = os.path.join(self.base_dir, 'embeddings.npy')
        if self.chunks and os.path.exists(emb_path):
            self.embeddings = np.load(emb_path)
        elif self.chunks:
            self._rebuild_embeddings()
        else:
            self.embeddings = np.zeros((0, 384), dtype=np.float32)

        print(f"Tild document index: {len(self.documents)} PDF(s), {len(self.chunks)} chunk(s)")

    def _save_manifest(self):
        os.makedirs(self.base_dir, exist_ok=True)
        payload = {
            'documents': list(self.documents.values()),
            'chunks': self.chunks,
        }
        with open(self.manifest_path, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

        if len(self.chunks) > 0:
            np.save(os.path.join(self.base_dir, 'embeddings.npy'), self.embeddings)

    def _rebuild_embeddings(self):
        texts = [c['text'] for c in self.chunks]
        if not texts:
            self.embeddings = np.zeros((0, 384), dtype=np.float32)
            return
        self.embeddings = self.model.encode(texts, normalize_embeddings=True)

    def list_documents(self):
        docs = sorted(
            self.documents.values(),
            key=lambda d: d.get('uploaded_at', ''),
            reverse=True,
        )
        return [
            {
                'id': d['id'],
                'filename': d['filename'],
                'page_count': d.get('page_count', 0),
                'chunk_count': d.get('chunk_count', 0),
                'uploaded_at': d.get('uploaded_at'),
                'preview': d.get('preview', ''),
            }
            for d in docs
        ]

    def get_document(self, doc_id):
        return self.documents.get(doc_id)

    def add_pdf(self, source_path, original_filename):
        """Ingest a PDF from disk; returns document metadata."""
        doc_id = make_document_id()
        dest_path = os.path.join(self.files_dir, f'{doc_id}.pdf')
        shutil.copy2(source_path, dest_path)

        pages = extract_pdf_text(dest_path)
        if not pages:
            os.remove(dest_path)
            raise ValueError('Could not extract text from this PDF. It may be scanned/image-only (OCR coming later).')

        doc_chunks = chunk_pages(pages)
        if not doc_chunks:
            os.remove(dest_path)
            raise ValueError('PDF had no usable text content.')

        preview = doc_chunks[0]['text'][:280].replace('\n', ' ')
        meta = {
            'id': doc_id,
            'filename': original_filename,
            'stored_path': dest_path,
            'page_count': len(pages),
            'chunk_count': len(doc_chunks),
            'uploaded_at': datetime.now().isoformat(),
            'preview': preview,
        }
        self.documents[doc_id] = meta

        start_idx = len(self.chunks)
        for chunk in doc_chunks:
            self.chunks.append({
                'doc_id': doc_id,
                'chunk_index': chunk['chunk_index'],
                'page': chunk['page'],
                'text': chunk['text'],
                'char_count': chunk['char_count'],
            })

        new_texts = [c['text'] for c in self.chunks[start_idx:]]
        new_emb = self.model.encode(new_texts, normalize_embeddings=True)
        if len(self.embeddings) == 0:
            self.embeddings = new_emb
        else:
            self.embeddings = np.vstack([self.embeddings, new_emb])

        self._save_manifest()
        return meta

    def chunks_for_document(self, doc_id, limit=20):
        """Return all indexed chunks for a document (for summarize / overview questions)."""
        doc = self.documents.get(doc_id, {})
        filename = doc.get('filename', 'document')
        results = []
        for chunk in self.chunks:
            if chunk['doc_id'] != doc_id:
                continue
            results.append({
                'doc_id': doc_id,
                'filename': filename,
                'page': chunk['page'],
                'text': chunk['text'],
                'score': 1.0,
            })
            if len(results) >= limit:
                break
        return results

    def search(self, query, doc_id=None, top_k=4, min_score=0.25):
        """Return top matching chunks, optionally scoped to one document."""
        if not self.chunks or len(self.embeddings) == 0:
            return []

        query_emb = self.model.encode([query], normalize_embeddings=True)
        scores = np.dot(self.embeddings, query_emb.T).flatten()

        indices = np.argsort(scores)[::-1]
        results = []
        for idx in indices:
            chunk = self.chunks[int(idx)]
            if doc_id and chunk['doc_id'] != doc_id:
                continue
            score = float(scores[int(idx)])
            if score < min_score:
                continue
            doc = self.documents.get(chunk['doc_id'], {})
            results.append({
                'doc_id': chunk['doc_id'],
                'filename': doc.get('filename', 'document'),
                'page': chunk['page'],
                'text': chunk['text'],
                'score': score,
            })
            if len(results) >= top_k:
                break
        return results

    @staticmethod
    def is_pre_upload_document_intent(text):
        """User will upload later  -  do not read an old indexed PDF."""
        import re
        text_lower = text.lower()
        return any(re.search(p, text_lower) for p in PRE_UPLOAD_DOCUMENT_TRIGGERS)

    @staticmethod
    def is_remember_from_document_intent(text):
        """User wants facts from the active PDF saved to memory."""
        import re
        text_lower = text.lower()
        return any(re.search(p, text_lower) for p in REMEMBER_DOCUMENT_PATTERNS)

    @staticmethod
    def is_document_question(text):
        import re
        text_lower = text.lower()
        if TildDocumentIndex.is_pre_upload_document_intent(text):
            return False
        if TildDocumentIndex.is_remember_from_document_intent(text):
            return True
        if any(re.search(p, text_lower) for p in RE_READ_DOCUMENT_PATTERNS):
            return True
        if re.search(r'\b(cv|resume|curriculum vitae)\b', text_lower):
            return True
        if any(trigger in text_lower for trigger in DOCUMENT_QUESTION_TRIGGERS):
            return True
        # typo-tolerant question about an already-present doc
        if re.search(r'doc\w*', text_lower) and re.search(r'ab(?:o|ou)t', text_lower):
            return True
        if re.search(r'doc\w*', text_lower) and re.search(
            r'\b(summarize|summarise|summary|main points|what does it say|what is it say|what does the)\b',
            text_lower,
        ):
            return True
        return False

    def resolve_document_id(self, memory):
        """Only the PDF attached in this session  -  never guess from old uploads."""
        if not memory:
            return None
        doc_id = memory.get_active_document_id()
        if doc_id and doc_id in self.documents:
            return doc_id
        return None

    def format_context(self, hits, max_chars=6500, language='en', include_analysis=True):
        if not hits:
            return ''

        combined_text = '\n\n'.join(hit['text'] for hit in hits)
        notes = ''
        if include_analysis:
            analysis = analyze_document_text(combined_text)
            notes = format_analysis_notes(analysis, language)

        parts = []
        if notes:
            parts.append(
                'DOCUMENT ANALYSIS (use this to shape your answer  -  do not paste as a rigid header):\n'
                + notes
            )

        total = sum(len(p) for p in parts)
        for hit in hits:
            header = f"[{hit['filename']}  -  page {hit['page']}]"
            block = f"{header}\n{hit['text']}"
            if total + len(block) > max_chars:
                remaining = max_chars - total
                if remaining > 200:
                    parts.append(block[:remaining] + '...')
                break
            parts.append(block)
            total += len(block)

        from src.text_style import strip_long_dashes
        return strip_long_dashes('\n\n---\n\n'.join(parts))
