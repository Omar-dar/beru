import os
import sys

from src.venv_bootstrap import ensure_project_venv

ensure_project_venv()

import tempfile

from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename

from src.pipeline import TildPipeline

app = Flask(__name__)
CORS(app)

pipeline = TildPipeline()

MAX_UPLOAD_MB = 20
ALLOWED_EXTENSIONS = {'.pdf'}

print("Tild API ready!")


def _allowed_file(filename):
    _, ext = os.path.splitext(filename.lower())
    return ext in ALLOWED_EXTENSIONS


@app.route('/start', methods=['GET'])
def start():
    pipeline.start_session(clear_history=True)
    lang = 'en'
    memory = pipeline.memory
    return jsonify({
        'response': memory.greeting_for_session(lang),
        'language': lang,
        'known_user': memory.is_session_identified(),
        'awaiting_owner_confirm': memory.is_awaiting_owner_confirm(),
        'is_owner': memory.is_owner(),
        'tone': memory.get_tone(),
        'active_document': memory.get_active_document_info(),
    })


@app.route('/clear', methods=['POST'])
def clear_chat():
    greeting = pipeline.start_session(clear_history=True)
    return jsonify({
        'status': 'ok',
        'response': greeting,
        'active_document': None,
    })


@app.route('/documents', methods=['GET'])
def list_documents():
    return jsonify({
        'documents': pipeline.rag.document_index.list_documents(),
        'active_document': pipeline.memory.get_active_document_info(),
    })


@app.route('/upload', methods=['POST'])
def upload_document():
    if 'file' not in request.files:
        return jsonify({'error': 'No file field. Use form key "file".'}), 400

    upload = request.files['file']
    if not upload or not upload.filename:
        return jsonify({'error': 'No file selected'}), 400

    filename = secure_filename(upload.filename)
    if not _allowed_file(filename):
        return jsonify({'error': 'Only PDF files are supported for now.'}), 400

    upload.seek(0, os.SEEK_END)
    size = upload.tell()
    upload.seek(0)
    if size > MAX_UPLOAD_MB * 1024 * 1024:
        return jsonify({'error': f'File too large. Max {MAX_UPLOAD_MB} MB.'}), 400

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            upload.save(tmp.name)
            tmp_path = tmp.name

        meta = pipeline.ingest_pdf(tmp_path, filename)
        short = f'Ready bro — I indexed "{meta["filename"]}". Ask me anything about it.'
        if not pipeline.memory.is_owner():
            short = f'Ready — I indexed "{meta["filename"]}". Ask me anything about it.'
        return jsonify({
            'status': 'ok',
            'document': {
                'id': meta['id'],
                'filename': meta['filename'],
                'page_count': meta['page_count'],
                'chunk_count': meta['chunk_count'],
                'preview': meta['preview'],
                'uploaded_at': meta['uploaded_at'],
            },
            'active_document': pipeline.memory.get_active_document_info(),
            'message': short,
        })
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 422
    except Exception as exc:
        return jsonify({'error': f'Upload failed: {exc}'}), 500
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


@app.route('/chat', methods=['POST'])
def chat():
    data = request.json or {}
    message = data.get('message', '').strip()
    new_chat = data.get('new_chat', False)
    document_id = data.get('document_id')

    if document_id:
        doc = pipeline.rag.document_index.get_document(document_id)
        if doc:
            pipeline.memory.set_active_document(doc['id'], doc['filename'])

    if not message:
        return jsonify({'error': 'No message'}), 400

    result = pipeline.chat_turn(message, new_chat=new_chat, format_for_ui=True)
    return jsonify(result)


@app.route('/health', methods=['GET'])
def health():
    doc_count = len(pipeline.rag.document_index.documents)
    return jsonify({
        'status': 'ok',
        'message': 'Tild API is running',
        'documents_indexed': doc_count,
    })


if __name__ == '__main__':
    app.run(port=8000, debug=False)
