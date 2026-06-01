"""Shared Tild response pipeline for API, CLI, voice, and robot."""

from chat.chat import get_response, load_tild
from src.deep_brain import DeepBrain
from src.entities import TildEntityRecognizer
from src.language import detect_language
from src.learning import learn_from_exchange
from src.markdown_format import format_for_ui as apply_ui_format
from src.text_style import strip_long_dashes
from src.memory import TildMemory
from src.rag import TildRAG
from src.search import TildSearch


class TildPipeline:
    """Load once, use everywhere — same routing, formatting, and learning."""

    def __init__(self, *, load_model=False):
        print("Loading Tild pipeline...")
        self.rag = TildRAG()
        self.memory = TildMemory()
        self.search = TildSearch()
        self.ner = TildEntityRecognizer()
        self.brain = DeepBrain()
        if load_model:
            self.model, self.tokenizer = load_tild()
        else:
            self.model, self.tokenizer = None, None
        print("Tild pipeline ready!")

    def start_session(self, clear_history=True):
        self.memory.start_session(clear_history=clear_history)
        return strip_long_dashes(self.memory.greeting_for_session())

    def chat_turn(
        self,
        message,
        *,
        new_chat=False,
        format_for_ui=False,
        learn=True,
        language_hint=None,
    ):
        """
        One full chat turn: store message, route, format, learn, store reply.

        Returns dict with response, language, tone, source, and session flags.
        """
        message = (message or '').strip()
        if not message:
            raise ValueError('Empty message')

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
        if format_for_ui:
            response = apply_ui_format(response)

        if learn:
            if learn_from_exchange(message, response, source, rag=self.rag):
                print(f"[Tild learned from {source}]")

        self.memory.add_to_conversation('tild', response)

        return {
            'response': response,
            'language': language,
            'tone': tone,
            'source': source,
            'user': self.memory.get_user_name(),
            'is_owner': self.memory.is_owner(),
            'session_identified': self.memory.is_session_identified(),
            'active_document': self.memory.get_active_document_info(),
        }

    def ingest_pdf(self, file_path, original_filename):
        """Upload + index a PDF; set as active document for this session."""
        meta = self.rag.document_index.add_pdf(file_path, original_filename)
        self.memory.set_active_document(meta['id'], meta['filename'])
        return meta
