import os
import sys

from src.venv_bootstrap import ensure_project_venv

ensure_project_venv()

from src.project_env import load_project_dotenv

load_project_dotenv()

import base64
import tempfile
from contextlib import contextmanager

from flask import Flask, request, jsonify, Response
from werkzeug.utils import secure_filename

from src.api_contract import ui_chat_payload
from src.api_cors import init_cors
from src.client_sessions import bind_client_session, reset_client_session
from src.pipeline import BeruPipeline
from src.text_style import strip_long_dashes
from src.voice import (
    capabilities as voice_capabilities,
    is_tts_available,
    preload_stt_model,
    synthesize_speech,
    transcribe_file,
    SUPPORTED_AUDIO_EXTENSIONS,
)
from src import voice_auth

app = Flask(__name__)
init_cors(app)

pipeline = BeruPipeline()

MAX_UPLOAD_MB = 20
MAX_AUDIO_MB = 25
ALLOWED_EXTENSIONS = {'.pdf'}

print("Beru API ready!")

import threading

if os.getenv('BERU_PRELOAD_VOICE', '1').strip().lower() in ('1', 'true', 'yes'):
    threading.Thread(target=preload_stt_model, daemon=True).start()

if os.getenv('BERU_OLLAMA_PRELOAD', '1').strip().lower() in ('1', 'true', 'yes'):
    threading.Thread(target=pipeline.brain.preload_model, daemon=True).start()


def _allowed_file(filename):
    _, ext = os.path.splitext(filename.lower())
    return ext in ALLOWED_EXTENSIONS


def _collector_session_id():
    """Per-browser id from Netlify UI (localStorage) or fallback to IP."""
    header = (request.headers.get('X-Beru-Session-Id') or '').strip()
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
        return jsonify(ui_chat_payload(
            response=greeting,
            language=lang,
            active_document=memory.get_active_document_info(),
            source='gate',
            tone=memory.get_tone(),
            user=memory.get_user_name(),
            is_owner=memory.is_owner(),
            session_identified=memory.is_session_identified(),
            awaiting_owner_confirm=memory.is_awaiting_owner_confirm(),
            awaiting_voice_wake=memory.is_awaiting_voice_wake(),
            voice_verified=memory.is_voice_verified(),
            voice_enrolled=voice_auth.is_enrolled(),
            extra={'known_user': memory.is_session_identified()},
        ))


@app.route('/clear', methods=['POST'])
def clear_chat():
    data = request.get_json(silent=True) or {}
    lang_hint = (data.get('language') or '').strip() or None
    with _client_session_scope():
        lang = lang_hint or pipeline.memory.session.get('language') or 'en'
        greeting = pipeline.start_session(
            clear_history=True, language=lang, client_session_id=_collector_session_id()
        )
        memory = pipeline.memory
        payload = ui_chat_payload(
            response=greeting,
            language=lang,
            active_document=None,
            source='gate',
            tone=memory.get_tone(),
            is_owner=memory.is_owner(),
            session_identified=memory.is_session_identified(),
            awaiting_owner_confirm=memory.is_awaiting_owner_confirm(),
            awaiting_voice_wake=memory.is_awaiting_voice_wake(),
            voice_verified=memory.is_voice_verified(),
            voice_enrolled=voice_auth.is_enrolled(),
        )
        payload['status'] = 'ok'
        return jsonify(payload)


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
        return jsonify(ui_chat_payload(**result))


@app.route('/health', methods=['GET'])
def health():
    from src.conversation_collector import collect_dir, collection_enabled
    from src.computer_control import capabilities as computer_capabilities

    doc_count = len(pipeline.rag.document_index.documents)
    return jsonify({
        'status': 'ok',
        'message': 'Beru API is running',
        'documents_indexed': doc_count,
        'conversation_collection': collection_enabled(),
        'conversation_collect_dir': str(collect_dir()),
        'computer_control': computer_capabilities(),
    })


@app.route('/computer/capabilities', methods=['GET'])
def computer_caps():
    from src.computer_control import capabilities as computer_capabilities

    return jsonify(computer_capabilities())


@app.route('/voice/capabilities', methods=['GET'])
def voice_caps():
    caps = voice_capabilities()
    caps.update(voice_auth.auth_status())
    return jsonify(caps)


@app.route('/voice/auth/status', methods=['GET'])
def voice_auth_status():
    with _client_session_scope():
        return jsonify(voice_auth.auth_status(pipeline.memory))


@app.route('/voice/enroll', methods=['POST'])
def voice_enroll():
    """Enroll Omar voice profile (2–5 short clips, form key audio or audio0..audio4)."""
    paths = []
    tmp_paths = []
    try:
        uploads = request.files.getlist('audio')
        if not uploads:
            uploads = [
                request.files[k]
                for k in sorted(request.files.keys())
                if k.startswith('audio')
            ]
        if not uploads:
            return jsonify({'error': 'Send one or more audio files under form key "audio".'}), 400

        for idx, upload in enumerate(uploads):
            if upload is None:
                continue
            raw_name = (upload.filename or '').strip()
            _, ext = os.path.splitext(secure_filename(raw_name))
            if not ext:
                ext = '.webm'
            upload.seek(0, os.SEEK_END)
            size = upload.tell()
            upload.seek(0)
            if size < 100:
                continue
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                upload.save(tmp.name)
                paths.append(tmp.name)
                tmp_paths.append(tmp.name)

        if not paths:
            return jsonify({
                'ok': False,
                'error': 'No audio files received. Send multipart form field "audio" with WebM/WAV clips (~2–4 s each).',
            }), 400

        result = voice_auth.enroll_audio_paths(paths)
        if not result.get('ok'):
            return jsonify(result), 422
        return jsonify(result)
    finally:
        for p in tmp_paths:
            if p and os.path.exists(p):
                os.unlink(p)


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
        import time as _time
        from src.performance import debug_timing

        t0 = _time.perf_counter()
        suffix = os.path.splitext(secure_filename(upload.filename))[1] or '.webm'
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            upload.save(tmp.name)
            tmp_path = tmp.name

        stt = transcribe_file(tmp_path, language_hint=language_hint)
        t_stt = _time.perf_counter()
        transcript = stt['text']
        if len(transcript.split()) < 1:
            return jsonify({'error': 'Could not understand audio. Please try again.'}), 422

        turn_language = language_hint if language_hint in ('en', 'sv', 'ar') else stt['language']
        sid = _collector_session_id()
        with _client_session_scope():
            memory = pipeline.memory
            voice_score = None

            if voice_auth.voice_auth_enabled() and not memory.is_session_identified():
                if not voice_auth.is_enrolled():
                    gate_msg = memory.prompt_voice_wake(turn_language)
                    ui_gate = ui_chat_payload(
                        response=gate_msg,
                        language=turn_language,
                        source='gate',
                        session_identified=False,
                        is_owner=False,
                        awaiting_voice_wake=True,
                        voice_verified=False,
                        voice_enrolled=False,
                    )
                    ui_gate['transcript'] = transcript
                    ui_gate['transcript_language'] = stt['language']
                    return jsonify(ui_gate)

                matched, voice_score = voice_auth.verify_audio_path(tmp_path)
                if not matched:
                    if turn_language == 'sv':
                        fail = 'Jag känner inte igen rösten, sir. Säg Beru igen eller registrera om din röst.'
                    elif turn_language == 'ar':
                        fail = 'لم أتعرف على الصوت يا سيدي. قل Beru مرة أخرى أو أعد تسجيل صوتك.'
                    else:
                        fail = "I don't recognize that voice, sir. Say Beru again or re-enroll your voice."
                    ui_gate = ui_chat_payload(
                        response=fail,
                        language=turn_language,
                        source='gate',
                        session_identified=False,
                        is_owner=False,
                        awaiting_voice_wake=True,
                        voice_verified=False,
                        voice_enrolled=True,
                    )
                    ui_gate['transcript'] = transcript
                    ui_gate['transcript_language'] = stt['language']
                    ui_gate['voice_score'] = round(voice_score, 3)
                    return jsonify(ui_gate)
                memory.confirm_owner_by_voice(turn_language)

            if document_id:
                doc = pipeline.rag.document_index.get_document(document_id)
                if doc:
                    memory.set_active_document(doc['id'], doc['filename'])

            result = pipeline.chat_turn(
                transcript,
                new_chat=new_chat,
                format_for_ui=True,
                language_hint=turn_language,
                collector_session_id=sid,
                client_session_id=sid,
            )
            if voice_score is not None:
                result['voice_score'] = round(voice_score, 3)
        t_chat = _time.perf_counter()
        ui_result = ui_chat_payload(**result)
        ui_result['transcript'] = transcript
        ui_result['transcript_language'] = stt['language']
        if result.get('voice_score') is not None:
            ui_result['voice_score'] = result['voice_score']

        if _parse_bool(request.form.get('include_audio'), False) and is_tts_available():
            try:
                lang = ui_result.get('language') or stt['language'] or 'en'
                audio_bytes, mime = synthesize_speech(ui_result['response'], lang)
                ui_result['audio_base64'] = base64.b64encode(audio_bytes).decode('ascii')
                ui_result['audio_mime'] = mime
            except Exception as exc:
                ui_result['audio_error'] = str(exc)

        if debug_timing():
            ui_result['timing_ms'] = {
                'stt': round((t_stt - t0) * 1000),
                'chat': round((t_chat - t_stt) * 1000),
                'total': round((_time.perf_counter() - t0) * 1000),
            }

        return jsonify(ui_result)
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
            'error': 'TTS not available. pip install edge-tts or set BERU_TTS_BACKEND=macos on macOS.',
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
