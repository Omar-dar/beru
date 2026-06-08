"""Shared Beru response pipeline for API, CLI, voice, and robot."""

from chat.chat import get_response, load_beru
from src.deep_brain import DeepBrain
from src.entities import BeruEntityRecognizer
from src.language import detect_language
from src.learning import learn_from_exchange
from src.markdown_format import format_for_ui as apply_ui_format
from src.text_direction import strip_bidi_controls, text_direction_for_language
from src.text_style import strip_long_dashes
from src.client_sessions import bind_client_session, reset_client_session
from src.memory import BeruMemory
from src.rag import BeruRAG
from src.search import BeruSearch


class BeruPipeline:
    """Load once, use everywhere — same routing, formatting, and learning."""

    def __init__(self, *, load_model=False):
        print("Loading Beru pipeline...")
        self.rag = BeruRAG()
        self.memory = BeruMemory()
        self.search = BeruSearch()
        self.ner = BeruEntityRecognizer()
        self.brain = DeepBrain()
        if load_model:
            self.model, self.tokenizer = load_beru()
        else:
            self.model, self.tokenizer = None, None
        print("Beru pipeline ready!")

    def start_session(self, clear_history=True, language='en', client_session_id=None):
        bind_id = (client_session_id or '').strip() or None
        token = bind_client_session(bind_id)
        try:
            self.memory.start_session(clear_history=clear_history)
            greeting = strip_long_dashes(self.memory.greeting_for_session(language))
            return strip_bidi_controls(greeting)
        finally:
            reset_client_session(token)

    def chat_turn(
        self,
        message,
        *,
        new_chat=False,
        format_for_ui=False,
        learn=True,
        language_hint=None,
        collector_session_id=None,
        client_session_id=None,
    ):
        """
        One full chat turn: store message, route, format, learn, store reply.

        client_session_id: per-browser identity (X-Beru-Session-Id). Isolates Omar login
        from other devices; falls back to collector_session_id when omitted.
        """
        message = (message or '').strip()
        if not message:
            raise ValueError('Empty message')

        bind_id = (client_session_id or collector_session_id or '').strip() or None
        token = bind_client_session(bind_id)
        try:
            return self._chat_turn_impl(
                message,
                new_chat=new_chat,
                format_for_ui=format_for_ui,
                learn=learn,
                language_hint=language_hint,
                collector_session_id=collector_session_id,
            )
        finally:
            reset_client_session(token)

    def _chat_turn_impl(
        self,
        message,
        *,
        new_chat=False,
        format_for_ui=False,
        learn=True,
        language_hint=None,
        collector_session_id=None,
    ):
        if new_chat:
            self.memory.start_session(clear_history=True)

        tone = self.memory.get_tone()
        self.memory.add_to_conversation('human', message)

        response, source = get_response(
            self.model,
            self.tokenizer,
            self.rag,
            self.memory,
            self.search,
            self.ner,
            message,
            language_hint=language_hint,
            brain=self.brain,
        )
        language = self.memory.session.get('language') or detect_language(message)

        response = strip_long_dashes(response)
        if not (response or '').strip():
            lang = language or 'en'
            if lang == 'sv':
                response = 'Jag fick inget svar just nu. Försök igen bro.'
            elif lang == 'ar':
                response = 'لم أحصل على رد واضح. حاول مرة أخرى من فضلك.'
            else:
                response = 'I did not get a clear reply. Please try again.'
        if format_for_ui:
            response = apply_ui_format(response)
        response = strip_bidi_controls(response)

        if learn:
            if learn_from_exchange(message, response, source, rag=self.rag):
                print(f"[Beru learned from {source}]")

        self.memory.add_to_conversation('beru', response)

        if collector_session_id:
            from src.conversation_collector import collect_turn

            collect_turn(
                session_id=collector_session_id,
                user_message=message,
                beru_response=response,
                memory=self.memory,
                source=source,
                new_chat=new_chat,
            )

        return {
            'response': response,
            'language': language,
            'text_direction': text_direction_for_language(language),
            'tone': tone,
            'source': source,
            'user': self.memory.get_user_name(),
            'is_owner': self.memory.is_owner(),
            'session_identified': self.memory.is_session_identified(),
            'active_document': self.memory.get_active_document_info(),
        }

    def ingest_pdf(self, file_path, original_filename, client_session_id=None):
        """Upload + index a PDF; set as active document for this session."""
        bind_id = (client_session_id or '').strip() or None
        token = bind_client_session(bind_id)
        try:
            meta = self.rag.document_index.add_pdf(file_path, original_filename)
            self.memory.set_active_document(meta['id'], meta['filename'])
            return meta
        finally:
            reset_client_session(token)
