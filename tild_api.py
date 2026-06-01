import os
import sys

from src.venv_bootstrap import ensure_project_venv

ensure_project_venv()

import base64
import tempfile
from contextlib import contextmanager

from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from werkzeug.utils import secure_filename

from src.client_sessions import bind_client_session, reset_client_session
from src.pipeline import TildPipeline
from src.text_direction import text_direction_for_language
from src.text_style import strip_long_dashes
from src.voice import (
    capabilities as voice_capabilities,
    is_tts_available,
    preload_stt_model,
    synthesize_speech,
    transcribe_file,
    SUPPORTED_AUDIO_EXTENSIONS,
)

app = Flask(__name__)
CORS(app)

pipeline = TildPipeline()

MAX_UPLOAD_MB = 20
MAX_AUDIO_MB = 25
ALLOWED_EXTENSIONS = {'.pdf'}

print("Tild API ready!")

if os.getenv('TILD_PRELOAD_VOICE', '1').strip().lower() in ('1', 'true', 'yes'):
    import threading
    threading.Thread(target=preload_stt_model, daemon=True).start()


def _allowed_file(filename):
    _, ext = os.path.splitext(filename.lower())
    return ext in ALLOWED_EXTENSIONS


def _collector_session_id():
    """Per-browser id from Netlify UI (localStorage) or fallback to IP."""
    header = (request.headers.get('X-Tild-Session-Id') or '').strip()
    if header:
        return header
    if request.is_json:
        body = request.get_json(silent=True) or {}
        sid = (body.get('session_id') or '').strip()
        if sid:
            return sid
    if request.form:
        sid = (request.form.get('session_id') or '').strip()
        if sid:
            return sid
    return request.remote_addr or 'anonymous'


@contextmanager
def _client_session_scope():
    """Bind this HTTP request to one browser session (Mac vs phone stay separate)."""
    token = bind_client_session(_collector_session_id())
    try:
        yield
    finally:
        reset_client_session(token)


def _parse_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ('1', 'true', 'yes', 'on')


def _audio_upload():
    if 'audio' not in request.files:
        return None, (jsonify({'error': 'No audio field. Use form key "audio".'}), 400)
    upload = request.files['audio']
    if not upload or not upload.filename:
        return None, (jsonify({'error': 'No audio file selected'}), 400)
    _, ext = os.path.splitext(upload.filename.lower())
    if ext not in SUPPORTED_AUDIO_EXTENSIONS:
        return None, (
            jsonify({'error': f'Unsupported audio type. Use one of: {sorted(SUPPORTED_AUDIO_EXTENSIONS)}'}),
            400,
        )
    upload.seek(0, os.SEEK_END)
    size = upload.tell()
    upload.seek(0)
    if size > MAX_AUDIO_MB * 1024 * 1024:
        return None, (jsonify({'error': f'Audio too large. Max {MAX_AUDIO_MB} MB.'}), 400)
    return upload, None


@app.route('/start', methods=['GET'])
def start():
    lang = (request.args.get('language') or 'en').strip() or 'en'
    sid = _collector_session_id()
    with _client_session_scope():
        greeting = pipeline.start_session(clear_history=True, language=lang, client_session_id=sid)
        memory = pipeline.memory
        return jsonify({
            'response': greeting,
            'language': lang,
            'text_direction': text_direction_for_language(lang),
            'known_user': memory.is_session_identified(),
            'awaiting_owner_confirm': memory.is_awaiting_owner_confirm(),
            'is_owner': memory.is_owner(),
            'tone': memory.get_tone(),
            'active_document': memory.get_active_document_info(),
        })


@app.route('/clear', methods=['POST'])
def clear_chat():
    with _client_session_scope():
        lang = pipeline.memory.session.get('language') or 'en'
        greeting = pipeline.start_session(
            clear_history=True, language=lang, client_session_id=_collector_session_id()
        )
        return jsonify({
            'status': 'ok',
            'response': greeting,
            'language': lang,
            'text_direction': text_direction_for_language(lang),
            'active_document': None,
        })


@app.route('/documents', methods=['GET'])
def list_documents():
    with _client_session_scope():
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

        sid = _collector_session_id()
        with _client_session_scope():
            meta = pipeline.ingest_pdf(tmp_path, filename, client_session_id=sid)
            short = f'Ready bro - I indexed "{meta["filename"]}". Ask me anything about it.'
            if not pipeline.memory.is_owner():
                short = f'Ready - I indexed "{meta["filename"]}". Ask me anything about it.'
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
                'message': strip_long_dashes(short),
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
    language_hint = (data.get('language') or '').strip() or None

    if not message:
        return jsonify({'error': 'No message'}), 400

    sid = _collector_session_id()
    with _client_session_scope():
        if document_id:
            doc = pipeline.rag.document_index.get_document(document_id)
            if doc:
                pipeline.memory.set_active_document(doc['id'], doc['filename'])

        result = pipeline.chat_turn(
            message,
            new_chat=new_chat,
            format_for_ui=True,
            language_hint=language_hint,
            collector_session_id=sid,
            client_session_id=sid,
        )
        return jsonify(result)


@app.route('/health', methods=['GET'])
def health():
    from src.conversation_collector import collect_dir, collection_enabled

    doc_count = len(pipeline.rag.document_index.documents)
    return jsonify({
        'status': 'ok',
        'message': 'Tild API is running',
        'documents_indexed': doc_count,
        'conversation_collection': collection_enabled(),
        'conversation_collect_dir': str(collect_dir()),
    })


@app.route('/voice/capabilities', methods=['GET'])
def voice_caps():
    return jsonify(voice_capabilities())


@app.route('/voice/transcribe', methods=['POST'])
def voice_transcribe():
    upload, err = _audio_upload()
    if err:
        return err

    language_hint = (request.form.get('language') or '').strip() or None
    tmp_path = None
    try:
        suffix = os.path.splitext(secure_filename(upload.filename))[1] or '.webm'
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            upload.save(tmp.name)
            tmp_path = tmp.name
        return jsonify(transcribe_file(tmp_path, language_hint=language_hint))
    except Exception as exc:
        return jsonify({'error': f'Transcription failed: {exc}'}), 500
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


@app.route('/voice/chat', methods=['POST'])
def voice_chat():
    upload, err = _audio_upload()
    if err:
        return err

    new_chat = _parse_bool(request.form.get('new_chat'), False)
    document_id = (request.form.get('document_id') or '').strip() or None
    language_hint = (request.form.get('language') or '').strip() or None

    tmp_path = None
    try:
        suffix = os.path.splitext(secure_filename(upload.filename))[1] or '.webm'
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            upload.save(tmp.name)
            tmp_path = tmp.name

        stt = transcribe_file(tmp_path, language_hint=language_hint)
        transcript = stt['text']
        if len(transcript.split()) < 1:
            return jsonify({'error': 'Could not understand audio. Please try again.'}), 422

        turn_language = language_hint if language_hint in ('en', 'sv', 'ar') else stt['language']
        sid = _collector_session_id()
        with _client_session_scope():
            if document_id:
                doc = pipeline.rag.document_index.get_document(document_id)
                if doc:
                    pipeline.memory.set_active_document(doc['id'], doc['filename'])

            result = pipeline.chat_turn(
                transcript,
                new_chat=new_chat,
                format_for_ui=True,
                language_hint=turn_language,
                collector_session_id=sid,
                client_session_id=sid,
            )
        result['transcript'] = transcript
        result['transcript_language'] = stt['language']

        if _parse_bool(request.form.get('include_audio'), False) and is_tts_available():
            try:
                lang = result.get('language') or stt['language'] or 'en'
                audio_bytes, mime = synthesize_speech(result['response'], lang)
                result['audio_base64'] = base64.b64encode(audio_bytes).decode('ascii')
                result['audio_mime'] = mime
            except Exception as exc:
                result['audio_error'] = str(exc)

        return jsonify(result)
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    except Exception as exc:
        return jsonify({'error': f'Voice chat failed: {exc}'}), 500
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


@app.route('/voice/speak', methods=['POST'])
def voice_speak():
    if not is_tts_available():
        return jsonify({
            'error': 'TTS not available. pip install edge-tts or set TILD_TTS_BACKEND=macos on macOS.',
        }), 501

    data = request.json or {}
    text = strip_long_dashes((data.get('text') or '').strip())
    language = (data.get('language') or 'en').strip()

    if not text:
        return jsonify({'error': 'No text provided'}), 400

    try:
        audio_bytes, mime = synthesize_speech(text, language)
        return Response(audio_bytes, mimetype=mime)
    except Exception as exc:
        return jsonify({'error': f'Speech synthesis failed: {exc}'}), 500


if __name__ == '__main__':
    # 0.0.0.0 so phones / Netlify users can reach this Mac on the LAN (or via tunnel).
    app.run(host='0.0.0.0', port=8000, debug=False)
