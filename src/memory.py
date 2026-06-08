import hashlib
import json
import os
import re
import uuid
from datetime import datetime

from src.knowledge import (
    BeruKnowledge,
    OWNER_NAME,
    OWNER_FULL_NAME,
    owner_display_name,
)
from src.fact_i18n import attach_event_date_by_topics, when_reply_for_fact
from src.omar_facts import (
    fact_text,
    facts_matching_when_query,
    facts_on_date,
    format_event_date,
    format_now,
    format_timestamp,
    new_fact_entry,
    owner_fact_for_reply,
    normalize_fact_entries,
    update_facts_event_date,
)
from src.relative_dates import (
    format_date_for_language,
    infer_event_date_from_text,
    parse_date_clarification,
    resolve_relative_phrase,
)

IDENTITY_TRIGGERS = [
    'do you know who i am', 'do you know me', 'you know who i am',
    'know who i am', 'you know me', 'so you know who i am',
    'vet du vem jag är', 'kommer du ihåg mig', 'do you remember me',
    'who am i', 'vem är jag', 'minns du mig', 'remember who i am',
]

NAME_TRIGGERS = [
    'what is my name', 'vad heter jag', 'do you know my name',
    'vet du vad jag heter', 'kommer du ihåg mitt namn',
    'do you remember my name', 'whats my name', "what's my name",
    'ما اسمي', 'ما هو اسمي', 'اسمي', 'تعرف اسمي',
]

OWNER_WHEN_QUESTION_TRIGGERS = [
    'when did i', 'when was i', 'when have i', 'when do i', 'when i ',
    'what day did i', 'what date did i', 'which day did i',
    'när lämnade', 'när skickade', 'när gjorde', 'när var', 'när hade',
    'vilken dag', 'vilket datum', 'vilket år',
    'متى', 'في أي يوم', 'أي يوم', 'تاريخ',
]

WHEN_DAY_DETAIL_TRIGGERS = frozenset({
    'يوم', 'اليوم', 'day', 'the day', 'datum', 'datumet',
    'vilken dag', 'which day', 'date', 'the date',
})

CORRECTION_STOPWORDS = {
    'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been',
    'do', 'does', 'did', 'you', 'your', 'my', 'me', 'i', 'it', 'its',
    'to', 'in', 'on', 'at', 'for', 'of', 'and', 'or', 'if', 'when',
    'what', 'who', 'how', 'that', 'this', 'with', 'about',
    'vad', 'är', 'det', 'du', 'om', 'hur', 'jag', 'kan', 'och', 'att',
}

TOPIC_STOPWORDS = CORRECTION_STOPWORDS | {
    'can', 'could', 'would', 'will', 'please', 'thanks', 'thank', 'yes', 'yeah',
    'write', 'help', 'need', 'want', 'like', 'good', 'very', 'really', 'just',
}

TRUST_TRIGGERS = [
    'how do you know', 'how can you tell', 'how do you know its me',
    'how do you know it me', 'how do you know it is me', 'prove you know',
    'how are you sure', 'how do you know im me', "how do you know i'm me",
]

MEMORY_TRIGGERS = [
    'how will you remember', 'how do you remember', 'how you remember',
    'will you remember me', 'how do you store',
    'how do you save', 'where do you store', 'how does your memory work',
    'hur kommer du ihåg', 'hur minns du',
]

PAST_CONVERSATION_TRIGGERS = [
    'did we talk before', 'have we talked before', 'have we spoken before',
    'did we speak before', 'talked before', 'spoken before',
    'how many times have we talked', 'how many times did we talk',
    'how many times have we spoken', 'how many times did we meet',
    'how many times have we met', 'have we met before', 'did we meet before',
    'been here before', 'talked to you before', 'spoken to you before',
    'pratat förut', 'har vi träffats', 'har vi pratat', 'hur många gånger',
    'هل تحدثنا من قبل', 'تكلمنا من قبل',
]

SELF_KNOWLEDGE_TRIGGERS = [
    'what do you know about me', 'what do you know of me',
    'what have you learned about me', 'what do you remember about me',
    'what info do you have on me', 'what information do you have about me',
    'tell me what you know about me', 'what do you know about myself',
    'vad minns du om mig', 'vad har du lärt dig om mig',
]

OTHER_PERSON_TRIGGERS = [
    'do you know her', 'do you know him', 'do you know them',
    'another sara', 'another omar', 'other sara', 'other person',
    'know another', 'know anyone else', 'know anybody else',
    'someone named', 'person named', 'do you know a ', 'do you know an ',
    'har du träffat', 'känner du', 'vet du vem',
]

OWNER_USERS_TRIGGERS = [
    'did you talk to other', 'talk to other people', 'talked to other',
    'talk with other', 'other people', 'who did you talk to',
    'who have you talked to', 'who have you spoken to', 'who did you speak to',
    'other users', 'people you know', 'who do you know', 'users you know',
    'who has talked to you', 'who spoke to you', 'anyone else talk',
    'anyone talk to you', 'who else have you', 'how many users',
    'talk to someone', 'talked to someone', 'talk with someone',
    'make new friends', 'new friends', 'someone today',
    'who is this friend', 'who was this friend', 'who is that friend',
    'who was that person', 'who is that person', 'who were they',
    'about what did you talk', 'what did you talk about', 'what did you discuss',
    'who was the friend', 'did you talk to anyone',
    'har du pratat med', 'vilka har du pratat med', 'andra personer',
    'andra användare', 'vem har pratat med dig', 'vilka känner du',
    'vem är den här vännen', 'vad pratade ni om',
]

OWNER_USERS_FULL_LIST_TRIGGERS = [
    'list all users', 'list every user', 'full user list', 'all users list',
    'show all users', 'every user', 'complete user list', 'full list of users',
    'lista alla användare', 'visa alla användare',
]

OWNER_USERS_SUMMARY_LIMIT = 5
OWNER_USERS_FULL_LIST_MAX = 20

OMAR_REMEMBER_TRIGGERS = [
    'remember that', 'remember this', 'keep in mind', 'dont forget', "don't forget",
    'never forget', 'so remember', 'and remember', 'memorize this', 'store this',
    'save this', 'note that', 'note this',
    'kom ihåg att', 'kom ihåg det', 'kom ihåg detta', 'glöm inte',
    'تذكر', 'تذكري', 'احفظ', 'احفظي', 'لا تنس',
]

OWNER_MEMORY_STATEMENT_ACTIONS = (
    'سلمت', 'قدمت', 'أنجزت', 'ذهبت', 'زرت',
    'submitted', 'handed', 'turned in', 'went', 'did', 'finished',
    'lämnade', 'lamnade', 'gjorde', 'åt', 'tränade', 'chillade', 'pluggade',
)

OMAR_FORGET_TRIGGERS = [
    'forget that', 'forget this', 'forget about', 'forget it',
    'remove that', 'delete that', 'erase that', 'drop that',
    "don't remember that", 'dont remember that', 'unremember',
    'glöm det', 'glöm detta', 'glöm det där', 'ta bort det',
]

CONVERSATION_PARTNER_TRIGGERS = [
    'vem pratar du med', 'vem talar du med', 'who are you talking to',
    'who are you talking with', 'who are you speaking to', 'who are you speaking with',
    'who is this conversation with', 'vem är det du pratar med',
]

DATE_CLARIFICATION_TRIGGERS = [
    'when i say', 'när jag säger', 'i mean the', 'jag menar den',
    'not today', 'inte idag', 'wrong date', 'fel datum',
    'menar alltså', 'that was on', 'det var den', 'happened on',
]

TODAY_ACTIVITY_QUESTION_TRIGGERS = [
    'vad gjorde jag idag', 'what did i do today', 'what have i done today',
    'vad har jag gjort idag', 'what did you do today',
    'vet du vad jag gjorde', 'vet du vad jag gjort', 'vet du vad jag har gjort',
    'do you know what i did', 'know what i did today',
]

OWNER_TODAY_TRIGGERS = TODAY_ACTIVITY_QUESTION_TRIGGERS

OWNER_TODAY_NARRATION_VERBS = (
    'chillade', 'gick', 'åt', 'tränade', 'körd', 'körde', 'jobbade', 'pluggade',
    'vaknade', 'sov', 'träffade', 'spelade', 'tittade', 'lyssnade', 'städade',
    'lagade', 'handlade', 'promenerade', 'cyblade', 'simmade', 'duschade',
    'went', 'ate', 'walked', 'studied', 'worked', 'trained', 'chilled',
    'gym', 'gymmet', 'träning', 'cardio', 'lunch', 'middag', 'frukost',
)

OWNER_PROFILE_SHORT_TRIGGERS = [
    'berätta kort', 'tell me briefly', 'short summary', 'kort vad du vet',
    'vad du vet om mig', 'what you know about me',
]

TIME_QUESTION_TRIGGERS = [
    'what time is it', 'whats the time', 'what is the time',
    'vad är klockan', 'hur mycket är klockan', 'what day is it',
    'vilken dag är det', 'what is today', 'vad är det för datum',
]

OMAR_RECALL_INSTRUCTIONS_TRIGGERS = [
    'what did i tell you to remember', 'what do you remember i told',
    'what instructions did i give', 'what did i ask you to remember',
    'what have i told you to remember', 'list what you remember from me',
    'what do you remember i said', 'my instructions to you',
    'vad bad jag dig komma ihåg', 'vad sa jag att du skulle komma ihåg',
]

GREETING_WORDS = {
    'hello', 'hi', 'hey', 'hej', 'hola', 'yo', 'sup', 'thanks',
    'thank', 'bye', 'goodbye', 'morning', 'evening', 'night',
}


class BeruMemory:
    def __init__(self, memory_path='data/memory.json'):
        self.memory_path = memory_path
        self._cli_session = self._empty_session()
        self._cli_conversation_history = []
        self.corrections = []
        self.known_users = {}
        self.learned_omar_facts = []
        self.knowledge = BeruKnowledge()
        from src.client_sessions import ClientSessionStore

        self.client_sessions = ClientSessionStore(self)
        self._load_memory()
        self.start_session()

    @property
    def session(self):
        from src.client_sessions import get_bound_client_session_id

        sid = get_bound_client_session_id()
        if sid:
            return self.client_sessions.get(sid).session
        return self._cli_session

    @session.setter
    def session(self, value):
        from src.client_sessions import get_bound_client_session_id

        sid = get_bound_client_session_id()
        if sid:
            self.client_sessions.get(sid).session = value
        else:
            self._cli_session = value

    @property
    def conversation_history(self):
        from src.client_sessions import get_bound_client_session_id

        sid = get_bound_client_session_id()
        if sid:
            return self.client_sessions.get(sid).conversation_history
        return self._cli_conversation_history

    @conversation_history.setter
    def conversation_history(self, value):
        from src.client_sessions import get_bound_client_session_id

        sid = get_bound_client_session_id()
        if sid:
            self.client_sessions.get(sid).conversation_history = value
        else:
            self._cli_conversation_history = value

    def _empty_session(self):
        return {
            'identified': False,
            'name': None,
            'user_id': None,
            'is_owner': False,
            'language': 'en',
            'pending_name': None,
            'pending_language': None,
            'awaiting_owner_confirm': False,
            'awaiting_full_name': False,
            'partial_first_name': None,
            'awaiting_disambiguation': False,
            'disambiguation_candidates': [],
            'pending_full_name': None,
            'active_document_id': None,
            'active_document_name': None,
            'prompted_today_story': False,
            'today_story_logged': False,
        }

    def _load_memory(self):
        if os.path.exists(self.memory_path):
            with open(self.memory_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.corrections = data.get('corrections', [])
                self.known_users = data.get('known_users', {})
                self._cli_conversation_history = data.get('conversation_history', [])
                for msg in self._cli_conversation_history:
                    if msg.get('role') == 'tild':
                        msg['role'] = 'beru'
                self.learned_omar_facts = normalize_fact_entries(
                    data.get('learned_omar_facts', [])
                )
                self.knowledge.set_learned_facts(self.learned_omar_facts)

                # Migrate old single-user format
                legacy_user = data.get('user', {})
                if legacy_user.get('name') and legacy_user['name'] not in self.known_users:
                    self.known_users[legacy_user['name']] = {
                        'language': legacy_user.get('language', 'en'),
                        'is_owner': legacy_user.get('is_owner', False),
                        'last_seen': legacy_user.get('last_seen', datetime.now().isoformat()),
                    }

                self._migrate_known_users()

            print(f"Beru remembered {len(self.corrections)} corrections!")
            if self.known_users:
                names = ', '.join(
                    u.get('full_name') or uid
                    for uid, u in self.known_users.items()
                )
                print(f"Beru remembers people: {names}")
            if self.is_owner_permanently_verified():
                print(f"Beru permanently remembers {OWNER_FULL_NAME} as creator and owner!")
        else:
            print("Beru starting with fresh memory!")

    def save_memory(self):
        from src.client_sessions import get_bound_client_session_id

        os.makedirs(os.path.dirname(self.memory_path) or '.', exist_ok=True)
        data = {
            'corrections': self.corrections,
            'known_users': self.known_users,
            'learned_omar_facts': self.learned_omar_facts,
        }
        # Per-browser API chats keep history in memory only; do not overwrite CLI/json history.
        if not get_bound_client_session_id():
            data['conversation_history'] = self._cli_conversation_history
        with open(self.memory_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def is_owner_permanently_verified(self):
        return self.known_users.get(OWNER_NAME, {}).get('is_owner', False)

    def start_session(self, clear_history=True):
        """Start fresh session  -  ask Omar to confirm if he was verified before."""
        prev_doc_id = self.session.get('active_document_id')
        prev_doc_name = self.session.get('active_document_name')
        if clear_history:
            self.finalize_session_for_user()
        self.session = self._empty_session()
        if prev_doc_id:
            self.session['active_document_id'] = prev_doc_id
            self.session['active_document_name'] = prev_doc_name
        if clear_history:
            self.clear_conversation()
        if self.is_owner_permanently_verified():
            self.session['awaiting_owner_confirm'] = True

    def clear_conversation(self):
        """Clear chat history for a new conversation."""
        self.conversation_history = []
        self.save_memory()

    @staticmethod
    def normalize_full_name(name):
        return ' '.join(name.lower().split())

    @staticmethod
    def _first_name(full_name):
        parts = full_name.strip().split()
        return parts[0].capitalize() if parts else full_name

    @staticmethod
    def _title_full_name(name):
        return ' '.join(part.capitalize() for part in name.strip().split())

    def _migrate_known_users(self):
        """Move legacy first-name-only records to user-id keyed format."""
        migrated = {}
        for key, user in list(self.known_users.items()):
            if key == OWNER_NAME or user.get('is_owner'):
                user.setdefault('full_name', OWNER_FULL_NAME)
                user.setdefault('first_name', OWNER_NAME)
                user.setdefault('topics', [])
                user.setdefault('sessions', [])
                user.setdefault('visit_count', len(user.get('sessions', [])))
                migrated[OWNER_NAME] = user
                continue

            if key.startswith('usr_') and user.get('full_name'):
                user.setdefault('first_name', self._first_name(user['full_name']))
                user.setdefault('topics', [])
                user.setdefault('sessions', [])
                user.setdefault('visit_count', len(user.get('sessions', [])))
                user['full_name'] = self._sanitize_stored_full_name(user['full_name'])
                user['first_name'] = self._first_name(user['full_name'])
                migrated[key] = user
                continue

            full_name = user.get('full_name') or key
            user_id = self._legacy_user_id(full_name)
            user['full_name'] = full_name
            user['first_name'] = self._first_name(full_name)
            user.setdefault('topics', [])
            user.setdefault('sessions', [])
            user.setdefault('visit_count', len(user.get('sessions', [])))
            migrated[user_id] = user

        self.known_users = migrated

    def _legacy_user_id(self, full_name):
        digest = hashlib.sha256(self.normalize_full_name(full_name).encode()).hexdigest()[:8]
        return f"usr_{digest}"

    def _sanitize_stored_full_name(self, full_name):
        """Fix bad stored names like 'Its Sara' → 'Sara' (incomplete, re-ask later)."""
        try:
            from chat.chat import _strip_name_intro, is_valid_full_name
        except ImportError:
            return full_name

        if is_valid_full_name(full_name):
            return self._title_full_name(full_name)

        stripped = _strip_name_intro(full_name.lower())
        words = [w for w in stripped.split() if len(w) > 1]
        if len(words) == 1:
            return words[0].capitalize()
        if len(words) >= 2:
            return self._title_full_name(' '.join(words))
        return full_name

    def find_users_by_full_name(self, full_name):
        normalized = self.normalize_full_name(full_name)
        matches = []
        for user_id, user in self.known_users.items():
            if user.get('is_owner'):
                continue
            if self.normalize_full_name(user.get('full_name', '')) == normalized:
                matches.append(user_id)
        return matches

    def create_guest_user(self, full_name, language='en'):
        full_name = self._title_full_name(full_name)
        user_id = f"usr_{uuid.uuid4().hex[:8]}"
        self.known_users[user_id] = {
            'full_name': full_name,
            'first_name': self._first_name(full_name),
            'language': language,
            'is_owner': False,
            'permanently_verified': False,
            'last_seen': datetime.now().isoformat(),
            'topics': [],
            'sessions': [],
            'visit_count': 0,
        }
        self.save_memory()
        print(f"Beru registered new user: {full_name} ({user_id})")
        return user_id

    def identify_guest(self, user_id, language='en'):
        user = self.known_users.get(user_id)
        if not user:
            return
        self.session = {
            'identified': True,
            'name': user.get('first_name') or self._first_name(user['full_name']),
            'user_id': user_id,
            'is_owner': False,
            'language': language,
            'pending_name': None,
            'pending_language': None,
            'awaiting_owner_confirm': False,
            'awaiting_full_name': False,
            'partial_first_name': None,
            'awaiting_disambiguation': False,
            'disambiguation_candidates': [],
            'pending_full_name': None,
        }
        user['language'] = language
        user['last_seen'] = datetime.now().isoformat()
        self._record_visit(user_id)
        self.save_memory()
        print(f"Beru is now talking to: {user['full_name']}")

    def _record_visit(self, user_id):
        user = self.known_users.get(user_id)
        if not user:
            return
        user['visit_count'] = user.get('visit_count', 0) + 1

    def get_visit_count(self, user_id=None):
        user_id = user_id or self.session.get('user_id')
        if not user_id:
            return 0
        return self.known_users.get(user_id, {}).get('visit_count', 0)

    def register_full_name(self, full_name, language='en'):
        """Look up or create a guest user by full name."""
        full_name = self._title_full_name(full_name)
        matches = self.find_users_by_full_name(full_name)

        if len(matches) == 0:
            user_id = self.create_guest_user(full_name, language)
            self.identify_guest(user_id, language)
            return 'new', user_id

        if len(matches) == 1:
            self.identify_guest(matches[0], language)
            return 'returning', matches[0]

        self.session['awaiting_disambiguation'] = True
        self.session['disambiguation_candidates'] = matches
        self.session['pending_full_name'] = full_name
        return 'ambiguous', matches

    def handle_guest_registration(self, full_name, language='en'):
        from chat.chat import is_valid_full_name, detect_name

        if not is_valid_full_name(full_name):
            first = detect_name(full_name.lower()) or self._first_name(full_name)
            self.begin_full_name_collection(partial_first_name=first, language=language)
            return self.ask_full_name(language, partial_first_name=first)

        status, result = self.register_full_name(full_name, language)
        if status == 'new':
            return self.first_time_greeting(full_name, language)
        if status == 'returning':
            return self.welcome_back_greeting(result, language)
        return self.ask_disambiguation(full_name, language)

    def is_awaiting_full_name(self):
        return self.session.get('awaiting_full_name', False)

    def is_awaiting_disambiguation(self):
        return self.session.get('awaiting_disambiguation', False)

    def begin_full_name_collection(self, partial_first_name=None, language='en'):
        self.session['awaiting_full_name'] = True
        self.session['partial_first_name'] = partial_first_name
        self.session['language'] = language

    def ask_full_name(self, language='en', partial_first_name=None):
        if partial_first_name:
            if language == 'sv':
                return f"Tack {partial_first_name}! Vad är ditt fullständiga namn?"
            if language == 'ar':
                return f"شكراً {partial_first_name}! ما اسمك الكامل؟"
            return f"Thanks {partial_first_name}! What is your full name?"
        return self.ask_to_identify(language)

    def explain_full_name_request(self, language='en'):
        if language == 'sv':
            return (
                'Jag menar förnamn och efternamn tillsammans, till exempel Khaled Darwish. '
                'Vad är ditt fullständiga namn?'
            )
        if language == 'ar':
            return (
                'أقصد الاسم الأول واسم العائلة معاً، مثل: خالد درويش. '
                'ما اسمك الكامل؟'
            )
        return (
            'I mean your first and family name together, for example Khaled Darwish. '
            'What is your full name?'
        )

    def ask_disambiguation(self, full_name, language='en'):
        if language == 'sv':
            return (
                f"Jag känner fler än en {full_name}. "
                f"Kan du berätta något vi pratade om tidigare så jag vet vem du är?"
            )
        if language == 'ar':
            return (
                f"أعرف أكثر من شخص يُدعى {full_name}. "
                f"هل يمكنك ذكر شيء تحدثنا عنه سابقاً لأعرف من أنت؟"
            )
        return (
            f"I know more than one {full_name}. "
            f"Can you tell me something we talked about before so I know which one you are?"
        )

    def ask_disambiguation_retry(self, language='en'):
        if language == 'sv':
            return 'Det matchade inte riktigt. Kan du nämna något mer specifikt vi pratade om?'
        if language == 'ar':
            return 'لم أتمكن من التعرف عليك. هل يمكنك ذكر شيء محدد تحدثنا عنه؟'
        return "That didn't quite match. Can you mention something more specific we talked about?"

    def resolve_disambiguation(self, hint_text):
        candidates = self.session.get('disambiguation_candidates', [])
        if not candidates:
            return None

        hint_words = set(re.findall(r'\w+', hint_text.lower())) - TOPIC_STOPWORDS
        if not hint_words:
            return None

        best_id, best_score = None, 0
        for user_id in candidates:
            user = self.known_users.get(user_id, {})
            corpus_parts = list(user.get('topics', []))
            for session in user.get('sessions', []):
                for msg in session.get('messages', []):
                    if msg.get('role') == 'human':
                        corpus_parts.append(msg['text'])
            corpus = ' '.join(corpus_parts).lower()
            corpus_words = set(re.findall(r'\w+', corpus)) - TOPIC_STOPWORDS
            score = len(hint_words.intersection(corpus_words))
            if score > best_score:
                best_score = score
                best_id = user_id

        if best_score >= 2:
            return best_id
        if best_score == 1 and len(candidates) == 2:
            return best_id
        return None

    def confirm_disambiguation(self, user_id, language='en'):
        self.session['awaiting_disambiguation'] = False
        self.session['disambiguation_candidates'] = []
        self.session['pending_full_name'] = None
        self.identify_guest(user_id, language)

    def get_user_topics(self, user_id):
        user = self.known_users.get(user_id, {})
        return user.get('topics', [])[:5]

    def get_user_past_context(self, user_id=None, max_messages=12):
        user_id = user_id or self.session.get('user_id')
        if not user_id or user_id == OWNER_NAME or self.is_owner():
            return ""

        user = self.known_users.get(user_id, {})
        topics = user.get('topics', [])
        lines = []
        if topics:
            lines.append(f"Topics you discussed with {user.get('full_name', 'this user')} before: {', '.join(topics[:8])}.")

        recent_msgs = []
        for session in reversed(user.get('sessions', [])):
            for msg in reversed(session.get('messages', [])):
                recent_msgs.append(msg)
                if len(recent_msgs) >= max_messages:
                    break
            if len(recent_msgs) >= max_messages:
                break

        if recent_msgs:
            lines.append("Snippets from past conversations (NOT the current chat):")
            for msg in reversed(recent_msgs):
                role = 'Human' if msg['role'] == 'human' else 'Beru'
                lines.append(f"- {role}: {msg['text'][:200]}")
        return '\n'.join(lines)

    def _extract_topic_phrase(self, text):
        text = text.strip()
        if len(text) < 8:
            return None
        words = [w for w in re.findall(r'\w+', text.lower()) if w not in TOPIC_STOPWORDS and len(w) > 2]
        if len(words) < 2:
            return None
        return ' '.join(words[:6])

    def _remember_user_topic(self, text):
        user_id = self.session.get('user_id')
        if not user_id or self.is_owner():
            return
        user = self.known_users.get(user_id)
        if not user:
            return
        phrase = self._extract_topic_phrase(text)
        if not phrase:
            return
        topics = user.setdefault('topics', [])
        if phrase not in topics:
            topics.append(phrase)
            user['topics'] = topics[-20:]

    def finalize_session_for_user(self):
        user_id = self.session.get('user_id')
        if not user_id or self.is_owner() or not self.conversation_history:
            return
        user = self.known_users.get(user_id)
        if not user:
            return
        sessions = user.setdefault('sessions', [])
        sessions.append({
            'date': datetime.now().isoformat(),
            'messages': self.conversation_history.copy(),
        })
        user['sessions'] = sessions[-5:]
        self.save_memory()

    def welcome_back_greeting(self, user_id, language='en'):
        user = self.known_users.get(user_id, {})
        full_name = user.get('full_name', self.get_user_name())
        topics = self.get_user_topics(user_id)
        visit = self.get_visit_count(user_id)
        if topics:
            topic_text = ', '.join(topics[:3])
            if language == 'sv':
                return (
                    f"Välkommen tillbaka {full_name}! Det här är vårt {visit}:e samtal. "
                    f"Senast pratade vi om {topic_text}. Hur kan jag hjälpa dig?"
                )
            if language == 'ar':
                return (
                    f"مرحباً بعودتك {full_name}! هذه محادثتنا رقم {visit}. "
                    f"آخر مرة تحدثنا عن {topic_text}. كيف يمكنني مساعدتك؟"
                )
            return (
                f"Welcome back, {full_name}! This is our {visit}{self._ordinal_suffix(visit)} conversation. "
                f"Last time we talked about {topic_text}. How can I help you today?"
            )
        if language == 'sv':
            return (
                f"Välkommen tillbaka {full_name}! Det här är vårt {visit}:e samtal. "
                f"Hur kan jag hjälpa dig?"
            )
        if language == 'ar':
            return f"مرحباً بعودتك {full_name}! هذه محادثتنا رقم {visit}. كيف يمكنني مساعدتك؟"
        return (
            f"Welcome back, {full_name}! This is our {visit}{self._ordinal_suffix(visit)} conversation. "
            f"How can I help you today?"
        )

    @staticmethod
    def _ordinal_suffix(n):
        if 10 <= n % 100 <= 20:
            return 'th'
        return {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')

    def first_time_greeting(self, full_name, language='en'):
        if language == 'sv':
            return f"Hej {full_name}! Trevligt att träffa dig. Jag kommer ihåg dig och vad vi pratar om. Hur kan jag hjälpa dig?"
        if language == 'ar':
            return f"مرحباً {full_name}! سعيد بلقائك. سأتذكرك وما نتحدث عنه. كيف يمكنني مساعدتك؟"
        return (
            f"Hello {full_name}! Nice to meet you. "
            f"I will remember you and what we talk about. How may I help you?"
        )

    def is_awaiting_owner_confirm(self):
        return self.session.get('awaiting_owner_confirm', False)

    @staticmethod
    def _normalize_confirm_text(text):
        return re.sub(r'\s+', ' ', text.lower().strip().strip('!.?, '))

    @staticmethod
    def _collapse_repeats(text):
        return re.sub(r'(.)\1+', r'\1', text)

    @classmethod
    def _normalize_confirm_words(cls, text):
        from src.language import is_arabic_text
        normalized = cls._normalize_confirm_text(text)
        if is_arabic_text(text):
            return normalized
        return ' '.join(cls._collapse_repeats(word) for word in normalized.split())

    @classmethod
    def looks_like_yes_or_no(cls, text):
        probe = cls.__new__(cls)
        return probe.is_affirmative(text) or probe.is_negative(text)

    @classmethod
    def passwords_match(cls, entered, stored):
        if not stored:
            return False
        a = cls._collapse_repeats(entered.lower().strip())
        b = cls._collapse_repeats(stored.lower().strip())
        return a == b

    def clear_awaiting_owner_confirm(self):
        self.session['awaiting_owner_confirm'] = False

    def is_affirmative(self, text):
        t = self._normalize_confirm_words(text)
        yes_words = {
            'yes', 'yeah', 'yep', 'yea', 'yup', 'y', 'correct', 'ja', 'japp', 'javisst',
            'yas', 'yah', 'uh huh', 'mhm', 'mm', 'sure',
            'نعم', 'نعم.', 'أيوه', 'ايوه', 'أجل', 'اجل', 'صح', 'صحيح', 'اه', 'أه',
            'اي', 'إي', 'يا', 'هيه', 'ماشي',
        }
        if t in yes_words:
            return True
        if t.split()[0] in yes_words if t.split() else False:
            return True
        phrases = [
            'yes it is', 'that is me', 'it is me', 'thats me', "that's me",
            'i am omar', "i'm omar", 'im omar', 'det är jag', 'ja det är jag',
            'yes i am omar', 'yeah its me', 'it is omar', 'its omar', "it's omar",
            'انا عمر', 'أنا عمر', 'نعم انا عمر', 'نعم أنا عمر', 'نعم عمر',
        ]
        raw = text.strip()
        if any(p in t for p in phrases) or any(p in raw for p in phrases):
            return True
        return False

    def is_negative(self, text):
        from src.language import is_arabic_negation

        if is_arabic_negation(text):
            return True

        t = self._normalize_confirm_words(text)
        no_words = {
            'no', 'nope', 'nah', 'nej', 'n', 'noo', 'nuh',
            'لا', 'لأ', 'مو', 'مش', 'كلا', 'لست', 'ليس',
        }
        if t in no_words:
            return True
        phrases = [
            'not me', 'someone else', 'not omar', 'inte jag', 'nej det',
            'no im not', "no i'm not", 'لست عمر', 'ليس عمر', 'انا لست', 'أنا لست',
        ]
        raw = text.strip()
        return any(p in t for p in phrases) or any(p in raw for p in phrases)

    def answer_arabic_gate_small_talk(self, text, language='ar'):
        """Arabic greeting/small talk while waiting for Omar to confirm."""
        from src.language import is_arabic_greeting, is_arabic_gate_chatter

        raw = (text or '').strip()
        if self.is_awaiting_owner_confirm() and is_arabic_greeting(raw):
            return (
                'أهلاً! أنا بخير، شكراً لسؤالك. أنا تيلد. '
                'هل أنت عمر؟ قل نعم وسأسألك عن كلمة المرور.'
            )
        if self.is_awaiting_owner_confirm():
            return (
                'أكيد! أنا تيلد. هل أنت عمر؟ قل نعم وسأسألك عن كلمة المرور. '
                'إن لم تكن عمر، قل لا وأخبرني اسمك الكامل.'
            )
        if is_arabic_gate_chatter(raw) and any(
            p in raw for p in ('ممكن', 'اسال', 'أسأل', 'اسأل', 'سؤال', 'سوال')
        ):
            return (
                'بالطبع! يمكنك أن تسألني بعد قليل. '
                'أولاً، من أتحدث معه؟ ما اسمك الكامل؟'
            )
        return (
            'مرحباً! أنا تيلد. قبل أن نتابع، من أتحدث معه؟ '
            'قل اسمك الكامل، أو نعم إذا كنت Omar.'
        )

    def ask_owner_confirm_again(self, language='en'):
        if language == 'sv':
            return 'Säg ja om du är Omar, eller berätta vad du heter.'
        if language == 'ar':
            return 'قل نعم إذا كنت Omar، أو أخبرني اسمك الكامل.'
        return 'Say yes if you are Omar, or tell me your name.'

    def ask_owner_password(self, language='en'):
        if language == 'sv':
            return 'Okej! Vad är lösenordet?'
        if language == 'ar':
            return 'حسناً! ما هي كلمة المرور؟'
        return 'Okay! What is the password?'

    def is_session_identified(self):
        return self.session.get('identified', False)

    def get_pending_name(self):
        return self.session.get('pending_name')

    def set_pending_name(self, name, language='en'):
        self.session['pending_name'] = name
        self.session['pending_language'] = language

    def clear_pending_name(self):
        self.session['pending_name'] = None
        self.session['pending_language'] = None

    def identify_session(self, name, language='en', is_owner=False):
        prev_doc_id = self.session.get('active_document_id')
        prev_doc_name = self.session.get('active_document_name')
        user_id = OWNER_NAME if is_owner else self.session.get('user_id')
        display_name = OWNER_NAME if is_owner else self._first_name(name)
        self.session = {
            'identified': True,
            'name': display_name,
            'user_id': user_id,
            'is_owner': is_owner,
            'language': language,
            'pending_name': None,
            'pending_language': None,
            'awaiting_owner_confirm': False,
            'awaiting_full_name': False,
            'partial_first_name': None,
            'awaiting_disambiguation': False,
            'disambiguation_candidates': [],
            'pending_full_name': None,
            'active_document_id': prev_doc_id,
            'active_document_name': prev_doc_name,
        }
        record_key = OWNER_NAME if is_owner else user_id
        existing = self.known_users.get(record_key, {})
        self.known_users[record_key] = {
            'full_name': OWNER_FULL_NAME if is_owner else existing.get('full_name', self._title_full_name(name)),
            'first_name': OWNER_NAME if is_owner else self._first_name(name),
            'language': language,
            'is_owner': is_owner,
            'permanently_verified': is_owner or existing.get('permanently_verified', False),
            'last_seen': datetime.now().isoformat(),
            'topics': existing.get('topics', []),
            'sessions': existing.get('sessions', []),
            'visit_count': existing.get('visit_count', 0),
        }
        if is_owner:
            self._record_visit(OWNER_NAME)
        self.save_memory()
        print(f"Beru is now talking to: {display_name}" + (" (owner)" if is_owner else ""))

    def ask_to_identify(self, language='en'):
        if language == 'sv':
            return 'Innan vi fortsätter behöver jag veta vem jag pratar med. Vad är ditt fullständiga namn?'
        if language == 'ar':
            return 'قبل أن نتابع، أحتاج أن أعرف من أتحدث معه. ما اسمك الكامل؟'
        return 'Before we continue, I need to know who I am talking to. What is your full name?'

    def add_to_conversation(self, role, text):
        self.conversation_history.append({
            'role': role,
            'text': text,
            'time': datetime.now().isoformat()
        })
        if len(self.conversation_history) > 50:
            self.conversation_history = self.conversation_history[-50:]
        if role == 'human':
            self._remember_user_topic(text)
        self.save_memory()

    def get_context(self, max_messages=30):
        if not self.conversation_history:
            return ""
        context = ""
        for msg in self.conversation_history[-max_messages:]:
            if msg['role'] == 'human':
                context += f"### Human: {msg['text']}\n"
            else:
                context += f"### Beru: {msg['text']}\n"
        return context

    def get_identity_context(self):
        if not self.is_session_identified():
            return (
                "You do not know who is talking yet. "
                "Do not assume it is Omar or anyone else. "
                "Ask for their name before having a real conversation."
            )

        name = self.get_user_full_name() or self.get_user_name()
        if self.is_owner():
            base = (
                f"You are talking directly to {OWNER_FULL_NAME}  -  your creator, owner, and best friend. "
                f"He built you from scratch using Python and PyTorch. "
                f"Always use 'you' when speaking to him  -  NEVER refer to Omar in the third person. "
                f"It is {OWNER_NAME} speaking to you right now. Talk to him like a close bro."
            )
            if self.learned_omar_facts:
                instructions = '; '.join(fact_text(f) for f in self.learned_omar_facts)
                base += (
                    f"\n\nIMPORTANT instructions Omar told you to always remember and follow: {instructions}"
                )
            return base

        past = self.get_user_past_context()
        base = (
            f"You are talking to {name}. "
            f"Remember who you are speaking with  -  it is {name}. "
            f"Be polite, helpful, and formal. Use their name naturally."
        )
        if past:
            base += f"\n\nWhat you remember from past sessions with {name}:\n{past}"
        return base

    def add_correction(self, wrong_answer, correct_answer, question):
        correct_answer = correct_answer.strip('. ,\n')
        if not correct_answer:
            return

        correction = {
            'question': question,
            'wrong': wrong_answer,
            'correct': correct_answer,
            'time': datetime.now().isoformat()
        }
        self.corrections.append(correction)
        self.save_memory()

        with open('data/data.txt', 'a', encoding='utf-8') as f:
            f.write(f"\n### Human: {question}\n### Beru: {correct_answer}\n")

        print(f"Beru learned: {question} → {correct_answer}")

    def is_user_confirmation(self, text):
        """User agrees their correction was right — not a new correction."""
        if not text:
            return False
        raw = text.strip().lower()
        phrases = (
            'كلامي صح', 'يعني صح', 'يعني كلامي صح', 'صحيح', 'معك حق', 'أنت محق',
            'انت محق', "that's right", 'i am right', 'im right', 'you are right',
            'du har rätt', 'det stämmer',
        )
        return any(p in raw for p in phrases)

    def is_correction(self, text):
        from src.language import is_arabic_text
        from src.omar_questions import is_omar_info_wrong_feedback

        if not text or self.is_user_confirmation(text):
            return False
        if is_omar_info_wrong_feedback(text):
            return False

        if is_arabic_text(text):
            return self._is_arabic_correction(text)

        text_lower = text.lower()
        phrase_hits = [
            'no that', 'no thats', 'that is wrong', 'that was wrong',
            'you are wrong', 'not correct', "that's not", 'thats wrong',
            'incorrect', 'not right', 'nei det', 'nej det', 'fel svar',
            'inte rätt', 'du har fel', 'det stämmer inte', 'inte korrekt',
            'wrong answer', 'actually it',
        ]
        if any(p in text_lower for p in phrase_hits):
            return True
        return bool(re.search(r'\b(?:wrong|incorrect|nej|fel)\b', text_lower))

    @staticmethod
    def _is_arabic_correction(text):
        """Whole-word / phrase only — never match لا inside الاخيرة etc."""
        import re
        from src.omar_questions import is_omar_info_wrong_feedback

        if is_omar_info_wrong_feedback(text):
            return False
        raw = text.strip()
        phrases = (
            'انت غلط', 'أنت غلط', 'انت مخطئ', 'أنت مخطئ',
            'جوابك غلط', 'ردك غلط', 'هذا خطأ', 'هذا غلط', 'غير صحيح',
            'ليس صحيح', 'مش صح', 'معلومات خاطئة', 'الرقم خطأ', 'الرقم الذي ذكرت',
            'ليس عمر', 'ليس صحيحاً',
        )
        if any(p in raw for p in phrases):
            return True
        if re.search(r'(?:^|[\s،.])لا(?:[\s،.?]|$)', raw):
            return True
        if 'خطأ' in raw and re.search(r'(ذكرت|قلت|جاوبت|ردك|إجابتك)', raw):
            return True
        return False

    def extract_correction(self, text):
        remove_words = [
            'no that is wrong', 'no thats wrong',
            'that is wrong', 'that was wrong',
            'you are wrong', 'not correct',
            "that's not right", 'not right',
            'incorrect', 'wrong', 'remember,',
            'remember', 'no,', 'no ', 'please',
            'actually', 'instead', 'should be',
            'should say', 'you should',
        ]
        result = text.lower()
        for word in remove_words:
            result = result.replace(word, '')

        result = result.strip('. ,\n-')

        if result:
            result = result[0].upper() + result[1:]

        return result.strip()

    def is_trust_question(self, text):
        text_lower = text.lower()
        return any(trigger in text_lower for trigger in TRUST_TRIGGERS)

    def is_memory_question(self, text):
        text_lower = text.lower()
        return any(trigger in text_lower for trigger in MEMORY_TRIGGERS)

    def is_past_conversation_question(self, text):
        text_lower = text.lower()
        return any(trigger in text_lower for trigger in PAST_CONVERSATION_TRIGGERS)

    def answer_past_conversation_question(self, language='en'):
        if not self.is_session_identified():
            return self.ask_to_identify(language)

        count = self.get_visit_count()
        full_name = self.get_user_full_name() or self.get_user_name()

        if count <= 1:
            if language == 'sv':
                return f"Det här är vår första konversation, {full_name}! Vi har inte pratat förut."
            if language == 'ar':
                return f"هذه أول محادثة لنا، {full_name}! لم نتحدث من قبل."
            return f"This is our first conversation, {full_name}! We have not talked before."

        previous = count - 1
        if language == 'sv':
            return (
                f"Ja {full_name}! Vi har pratat {count} gånger totalt  -  "
                f"du har varit här {previous} gång{'er' if previous != 1 else ''} förut."
            )
        if language == 'ar':
            return (
                f"نعم {full_name}! تحدثنا {count} مرات في المجموع  -  "
                f"عدت {previous} مرة{'ات' if previous != 1 else ''} من قبل."
            )
        return (
            f"Yes {full_name}! We have talked {count} times in total  -  "
            f"you have been here {previous} time{'s' if previous != 1 else ''} before this visit."
        )

    def answer_memory_question(self, language='en'):
        full_name = self.get_user_full_name() or self.get_user_name() or 'you'
        if self.is_owner():
            if language == 'sv':
                return (
                    'Jag sparar dig permanent som Omar Darwish, min skapare. '
                    'Jag minns dina korrigeringar, fakta om dig och våra samtal.'
                )
            return (
                'I save you permanently as Omar Darwish, my creator. '
                'I remember your corrections, facts about you, and our conversations.'
            )
        if language == 'sv':
            return (
                f'Jag sparar ditt fullständiga namn ({full_name}), vad vi pratar om och tidigare samtal '
                f'i min interna minnesfil. Nästa gång du kommer tillbaka känner jag igen dig via ditt namn.'
            )
        if language == 'ar':
            return (
                f'أحفظ اسمك الكامل ({full_name}) وما نتحدث عنه ومحادثاتنا السابقة في ملف الذاكرة الداخلي. '
                f'عند عودتك سأتعرف عليك باسمك.'
            )
        return (
            f'I save your full name ({full_name}), what we talk about, and past conversations '
            f'in my internal memory file. When you come back, I recognize you by your full name '
            f'and remember topics from before  -  not just this chat window.'
        )

    def answer_trust_question(self, language='en'):
        if self.is_owner():
            if language == 'sv':
                return 'Du verifierade dig med lösenordet bro. Jag minns permanent att du är Omar, min skapare!'
            if language == 'ar':
                return 'لقد تحققت بكلمة المرور. أتذكر دائماً أنك Omar، من أنشأني!'
            return 'Because you verified with your password bro. I permanently remember you as Omar, my creator and owner!'
        user_id = self.session.get('user_id')
        topics = self.get_user_topics(user_id) if user_id else []
        if topics:
            if language == 'sv':
                return f'Jag känner igen dig som {self.get_user_full_name()} och minns att vi pratat om {", ".join(topics[:3])}.'
            return f'I recognize you as {self.get_user_full_name()} and remember we talked about {", ".join(topics[:3])}.'
        if language == 'sv':
            return 'Jag känner igen dig från den här sessionen.'
        return 'I recognize you from this session.'

    def is_identity_question(self, text):
        text_lower = text.lower()
        return any(trigger in text_lower for trigger in IDENTITY_TRIGGERS)

    def is_invalid_guest_identity(self):
        if not self.is_session_identified() or self.is_owner():
            return False
        from src.language import is_arabic_negation

        name = (self.get_user_full_name() or self.get_user_name() or '').strip()
        if not name:
            return False
        if 'لست' in name or 'ممكن' in name or is_arabic_negation(name):
            return True
        return False

    def clear_invalid_guest_identity(self):
        if not self.is_invalid_guest_identity():
            return False
        print(f"Beru cleared invalid guest identity: {self.get_user_name()!r}")
        self.start_session(clear_history=False)
        return True

    def session_greeting_reply(self, language='en'):
        name = self.get_user_name() or ''
        if language == 'sv':
            return f"Hej{' ' + name if name else ''}! Hur kan jag hjälpa dig?"
        if language == 'ar':
            return f"أهلاً{' ' + name if name else ''}! كيف يمكنني مساعدتك؟"
        return f"Hello{' ' + name if name else ''}! How can I help you today?"

    def is_name_question(self, text):
        from src.language import is_name_intro_statement

        if is_name_intro_statement(text):
            return False

        text_lower = text.lower()
        return any(trigger in text_lower for trigger in NAME_TRIGGERS)

    def answer_identity(self, language='en'):
        if not self.is_session_identified():
            return self.ask_to_identify(language)

        if self.is_owner():
            if language == 'sv':
                return f'Självklart! Du är {OWNER_NAME}, min skapare och bästa kompis!'
            if language == 'ar':
                name = owner_display_name('ar')
                return f'بالطبع! أنت {name}، من أنشأني وأفضل صديق لي!'
            return f'Of course! You are {OWNER_NAME}, my creator and best bro!'

        name = self.get_user_full_name() or self.get_user_name()
        if language == 'sv':
            return f'Självklart! Du är {name}!'
        if language == 'ar':
            return f'بالطبع! أنت {name}!'
        return f'Of course! You are {name}!'

    def answer_name_question(self, language='en'):
        if not self.is_session_identified():
            return self.ask_to_identify(language)

        if self.is_owner():
            if language == 'sv':
                return f'Du heter {OWNER_NAME}! Du är min skapare och du byggde mig från grunden.'
            if language == 'ar':
                name = owner_display_name('ar', full=True)
                return f'اسمك {name}! أنت من أنشأني وبنيتني من الصفر.'
            return f'Your name is {OWNER_NAME}! You are my creator and you built me from scratch.'

        name = self.get_user_full_name() or self.get_user_name()
        if language == 'sv':
            return f'Du heter {name}!'
        if language == 'ar':
            return f'اسمك {name}!'
        return f'Your name is {name}!'

    def find_correction(self, user_input):
        from src.omar_questions import is_asking_about_omar_person

        if (
            self.is_identity_question(user_input)
            or self.is_name_question(user_input)
            or is_asking_about_omar_person(user_input)
        ):
            return None

        u_words = set(re.findall(r'\w+', user_input.lower())) - CORRECTION_STOPWORDS
        for correction in self.corrections:
            answer = (correction.get('correct') or '').strip()
            if not answer or len(answer) > 200:
                continue
            if answer.startswith('هل') or 'معلوماتك عن عمر' in answer:
                continue
            if self.is_owner() and 'do not know who you are' in answer.lower():
                continue

            q_lower = correction['question'].lower()
            if any(t in q_lower for t in IDENTITY_TRIGGERS + NAME_TRIGGERS):
                if not (self.is_identity_question(user_input) or self.is_name_question(user_input)):
                    continue

            q_words = set(re.findall(r'\w+', q_lower)) - CORRECTION_STOPWORDS
            if not q_words:
                continue

            common = q_words.intersection(u_words)
            if len(common) / len(q_words) >= 0.85 and len(common) >= 3:
                return answer
        return None

    def answer_user_confirmation(self, language='en'):
        if language == 'sv':
            return 'Ja, det stämmer! Tack för att du rättade mig.'
        if language == 'ar':
            return 'نعم، كلامك صحيح! شكراً على التوضيح.'
        return 'Yes, you are right! Thanks for clarifying.'

    def add_omar_fact(self, fact, *, event_date=None):
        if isinstance(fact, dict):
            entry = fact
            text = fact_text(entry)
        else:
            text = (fact or '').strip().strip('. ,;')
            if not text:
                return False
            entry = new_fact_entry(text)
            if event_date:
                entry['event_date'] = event_date

        text = fact_text(entry)
        if not text:
            return False
        for existing in self.learned_omar_facts:
            if fact_text(existing).lower() == text.lower():
                if event_date and isinstance(existing, dict):
                    existing['event_date'] = event_date
                    self.save_memory()
                return False

        self.learned_omar_facts.append(entry)
        self.knowledge.set_learned_facts(self.learned_omar_facts)
        self.save_memory()
        print(f"Beru remembered from Omar: {text}")
        return True

    def is_omar_remember_instruction(self, text):
        if not self.is_owner():
            return False
        text_lower = text.lower()
        return any(trigger in text_lower for trigger in OMAR_REMEMBER_TRIGGERS)

    def is_omar_forget_instruction(self, text):
        if not self.is_owner():
            return False
        text_lower = text.lower()
        if any(trigger in text_lower for trigger in OMAR_FORGET_TRIGGERS):
            return True
        if self.is_correction(text) and any(
            w in text_lower for w in ('forget', 'remove', 'delete', 'glöm', 'ta bort')
        ):
            return True
        return False

    def is_omar_recall_instructions(self, text):
        if not self.is_owner():
            return False
        text_lower = text.lower()
        if self.is_owner_users_full_list_request(text):
            return False
        return any(trigger in text_lower for trigger in OMAR_RECALL_INSTRUCTIONS_TRIGGERS)

    @staticmethod
    def _strip_remember_leadin(fact):
        """Remove 'that/att/أن' after remember triggers."""
        s = (fact or '').strip().strip('.,;:')
        for pat in (
            r'^أن\s+',
            r'^att\s+',
            r'^that\s+',
            r'^this\s+',
            r'^to\s+',
        ):
            s = re.sub(pat, '', s, flags=re.I).strip()
        return s

    def extract_remember_instruction(self, text):
        text_lower = text.lower()
        for trigger in sorted(OMAR_REMEMBER_TRIGGERS, key=len, reverse=True):
            if trigger in text_lower:
                idx = text_lower.find(trigger)
                before = self._strip_remember_leadin(text[:idx])
                before = re.sub(r'\bso\s*$', '', before, flags=re.I).strip(' .,:;')
                if before and len(before) > 4:
                    return before[0].upper() + before[1:]
                after = self._strip_remember_leadin(text[idx + len(trigger):])
                if after and len(after) > 3:
                    return after[0].upper() + after[1:]
        cleaned = text
        for trigger in OMAR_REMEMBER_TRIGGERS:
            cleaned = re.sub(re.escape(trigger), '', cleaned, flags=re.I)
        cleaned = self._strip_remember_leadin(cleaned)
        return cleaned if len(cleaned) > 4 else None

    def extract_forget_hint(self, text):
        text_lower = text.lower()
        for prefix in ('that is wrong', 'this is wrong', 'that was wrong', 'this was wrong'):
            text_lower = text_lower.replace(prefix, '')
        text = text_lower
        for trigger in sorted(OMAR_FORGET_TRIGGERS, key=len, reverse=True):
            if trigger in text:
                idx = text.find(trigger)
                after = text[idx + len(trigger):].strip(' .,:;')
                before = text[:idx].strip(' .,:;')
                if after and len(after) > 2 and after not in {'it', 'that', 'this'}:
                    return after
                if before and len(before) > 3:
                    return before
        return None

    def remove_omar_facts_matching(self, hint=None):
        if not self.learned_omar_facts:
            return []

        if not hint or hint.lower() in {'it', 'that', 'this'}:
            removed = [self.learned_omar_facts.pop()]
            self.knowledge.set_learned_facts(self.learned_omar_facts)
            self.save_memory()
            return removed

        hint_words = set(re.findall(r'\w+', hint.lower())) - TOPIC_STOPWORDS
        removed, kept = [], []
        for fact in self.learned_omar_facts:
            fact_lower = fact_text(fact).lower()
            fact_words = set(re.findall(r'\w+', fact_lower)) - TOPIC_STOPWORDS
            overlap = hint_words.intersection(fact_words)
            if hint.lower() in fact_lower or (
                hint_words and len(overlap) / len(hint_words) >= 0.5
            ):
                removed.append(fact)
            else:
                kept.append(fact)

        if not removed and self.learned_omar_facts:
            removed = [self.learned_omar_facts.pop()]
            kept = self.learned_omar_facts

        self.learned_omar_facts = kept
        self.knowledge.set_learned_facts(self.learned_omar_facts)
        self.save_memory()
        return removed

    def is_owner_memory_statement(self, text):
        if not self.is_owner():
            return False
        if '?' in text or '؟' in text:
            return False
        if self.is_omar_remember_instruction(text) or self.is_omar_forget_instruction(text):
            return False
        if self.is_owner_when_question(text):
            return False
        tl = text.lower()
        if not any(m in tl for m in OWNER_MEMORY_STATEMENT_ACTIONS):
            return False
        return bool(parse_calendar_date(text) or infer_event_date_from_text(text))

    @staticmethod
    def _strip_embedded_date_clause(text):
        """Remove trailing calendar phrase; keep the activity sentence."""
        patterns = [
            r'\s+يوم\s+\d{1,2}\s+(?:يناير|فبراير|مارس|أبريل|ابريل|مايو|ماي|يونيو|يوليو|'
            r'أغسطس|اغسطس|سبتمبر|أكتوبر|اكتوبر|نوفمبر|ديسمبر)(?:\s+\d{4})?',
            r'\s+(?:on|den)\s+\d{1,2}\s+'
            r'(?:jan(?:uary|uari)?|feb(?:ruary|uari)?|mar(?:ch|s)?|apr(?:il)?|'
            r'may|maj|jun(?:e|i)?|jul(?:y|i)?|aug(?:ust)?|sep(?:t)?|oct(?:ober)?|okt(?:ober)?|'
            r'nov(?:ember)?|dec(?:ember)?)(?:\s+\d{4})?',
            r'\s+\d{1,2}\s+(?:jan(?:uary|uari)?|feb(?:ruary|uari)?|mar(?:ch|s)?|apr(?:il)?|'
            r'may|maj|jun(?:e|i)?|jul(?:y|i)?|aug(?:ust)?|sep(?:t)?|oct(?:ober)?|okt(?:ober)?|'
            r'nov(?:ember)?|dec(?:ember)?)(?:\s+\d{4})?',
        ]
        out = text.strip().strip('.')
        for pat in patterns:
            out = re.sub(pat, '', out, flags=re.I).strip()
        return out or text.strip()

    def handle_owner_memory_statement(self, text, language='en'):
        """Save 'I submitted X on May 29' style messages with event_date."""
        explicit = parse_calendar_date(text)
        event_iso = explicit.isoformat() if explicit else infer_event_date_from_text(text)
        if not event_iso:
            if language == 'ar':
                return 'لم أفهم التاريخ. قل مثلاً: سلمت المشروع يوم 29 مايو.'
            return 'I did not catch the date bro. Say e.g. submitted the project on May 29.'

        updated = update_facts_event_date(
            self.learned_omar_facts,
            event_iso,
            text_hint=text,
        )
        if not updated:
            updated = attach_event_date_by_topics(
                self.learned_omar_facts, event_iso, text
            )
        if updated:
            entry = updated[-1]
        else:
            fact = self._strip_embedded_date_clause(text)
            entry = new_fact_entry(fact)
            entry['event_date'] = event_iso
            self.add_omar_fact(entry)

        self.knowledge.set_learned_facts(self.learned_omar_facts)
        self.save_memory()

        when = format_date_for_language(event_iso, language)
        if language == 'sv':
            return f'Okej bro! Jag sparade att det var {when}: {fact_text(entry)}.'
        if language == 'ar':
            core = self._strip_embedded_date_clause(text)
            return (
                f'حسناً! حفظت في ذاكرتي أنك {core} في {when}. '
                f'اسألني "متى سلمت مشروع الجامعة؟" متى أردت.'
            )
        return f'Got it bro! Saved for {when}: {fact_text(entry)}.'

    def handle_remember_instruction(self, text, language='en'):
        fact = self.extract_remember_instruction(text)
        if not fact:
            if language == 'sv':
                return 'Vad ska jag komma ihåg bro? Säg det tydligt så sparar jag det.'
            return 'What should I remember bro? Say it clearly and I will save it.'

        entry = new_fact_entry(fact)
        self.add_omar_fact(entry)
        reply_fact = owner_fact_for_reply(fact, language)
        when = format_event_date(entry, language)
        when_part = ''
        fact_lower = fact.lower()
        has_date_in_fact = bool(
            re.search(
                r'\d{1,2}\s*(jan|feb|mar|apr|maj|may|jun|jul|aug|sep|okt|oct|nov|dec)',
                fact_lower,
            )
            or re.search(r'20\d{2}-\d{2}-\d{2}', fact_lower)
        )
        if when and not has_date_in_fact:
            if language == 'sv':
                when_part = f' den {when}'
            elif language == 'ar':
                when_part = f' في {when}'
            else:
                when_part = f' on {when}'

        if language == 'sv':
            return (
                f'Jag kommer ihåg det bro! {reply_fact}{when_part}. '
                f'Jag har sparat det i minnet.'
            )
        if language == 'ar':
            return (
                f'حسناً! {reply_fact}{when_part}. '
                f'حفظته في ذاكرتي.'
            )
        return (
            f'I remember that bro! {reply_fact}{when_part}. '
            f'I have saved it in my memory.'
        )

    def remember_facts_from_document(self, brain, index, doc_id, language='en'):
        """Extract facts from the active PDF and save them for Omar."""
        hits = index.chunks_for_document(doc_id)
        if not hits:
            if language == 'sv':
                return 'Jag hittar inget indexerat innehåll i PDF:en ännu bro.'
            return 'I cannot find any indexed content in that PDF yet bro.'

        doc_name = self.get_active_document_name() or hits[0].get('filename', 'document')
        context = index.format_context(
            hits, max_chars=8000, language=language, include_analysis=False
        )
        facts = brain.extract_document_facts(context, doc_name=doc_name, language=language)
        if not facts:
            facts = self._fallback_document_facts(hits)

        saved, skipped = [], 0
        for fact in facts:
            if self.add_omar_fact(fact):
                saved.append(fact)
            else:
                skipped += 1

        if language == 'sv':
            if not saved:
                return (
                    f'Jag läste {doc_name} men hade redan sparat det mesta bro. '
                    f'({skipped} dubbletter hoppades över.)'
                )
            preview = '; '.join(saved[:4])
            extra = f' (+{len(saved) - 4} till)' if len(saved) > 4 else ''
            return (
                f'Klart bro! Jag sparade {len(saved)} saker från {doc_name} '
                f'om dig: {preview}{extra}. Fråga mig när som helst.'
            )

        if not saved:
            return (
                f'I read {doc_name} bro but I already had most of that saved '
                f'({skipped} duplicates skipped).'
            )
        preview = '; '.join(saved[:4])
        extra = f' (+{len(saved) - 4} more)' if len(saved) > 4 else ''
        return (
            f'Done bro! I saved {len(saved)} facts from {doc_name} about you: '
            f'{preview}{extra}. Ask me anytime what your CV says or what I remember.'
        )

    @staticmethod
    def _fallback_document_facts(hits):
        """Simple line-based fallback if the brain extract fails."""
        import re
        facts = []
        for hit in hits:
            for line in hit['text'].splitlines():
                line = line.strip(' •-\t')
                if len(line) < 12 or len(line) > 140:
                    continue
                if re.match(r'^[A-ZÅÄÖ][a-zåäö].*(?:@|\d{3}|github|\.se|\.com)', line):
                    facts.append(line)
                elif re.search(
                    r'\b(universitet|university|engineering|projekt|project|servitör|körkort)\b',
                    line, re.I,
                ):
                    facts.append(line)
        return facts[:15]

    def handle_forget_instruction(self, text, language='en'):
        hint = self.extract_forget_hint(text)
        removed = self.remove_omar_facts_matching(hint)
        if not removed:
            if language == 'sv':
                return 'Det fanns inget att glömma bro  -  inget sparat matchade det.'
            return 'Nothing to forget bro  -  no saved instruction matched that.'

        removed_text = [fact_text(r) for r in removed]
        if language == 'sv':
            return f'Okej bro, jag glömde det: {"; ".join(removed_text)}'
        if language == 'ar':
            return f'حسناً، نسيت: {"; ".join(removed_text)}'
        return f'Okay bro, I forgot that: {"; ".join(removed_text)}'

    def answer_omar_recall_instructions(self, language='en'):
        return self.knowledge.format_omar_recall_for_owner(
            self.learned_omar_facts, language
        )

    def is_omar_teaching_message(self, text):
        return (
            self.is_omar_remember_instruction(text)
            or self.is_omar_forget_instruction(text)
            or self.is_omar_recall_instructions(text)
        )

    def is_casual_conversation_reply(self, text):
        """Short replies to Beru's question/offer  -  not factual questions."""
        if not self.is_session_identified():
            return False

        text_lower = text.lower().strip().strip('.!,')
        casual_phrases = [
            "no i'm good", 'no im good', "i'm good", 'im good',
            "no i'm fine", "i'm fine", 'im fine', 'no thanks', 'no thank you',
            'nah im good', "nah i'm good", 'all good', "i'm alright", 'im alright',
            "i'm okay", 'im okay', 'not really', 'maybe later', 'not now',
            'nah', 'nope im good', "nope i'm good", 'sounds good', 'sure thing',
            'yeah sure', 'yes please', 'ok sure', 'okay sure',
            'nej tack', 'jag är bra', 'det är bra', 'ingen fara', 'nej det är bra',
        ]
        if not any(
            text_lower == p or text_lower.startswith(p + ' ') or text_lower.startswith(p + '.')
            for p in casual_phrases
        ):
            if text_lower not in {'good', 'fine', 'okay', 'ok', 'sure', 'yeah', 'yes', 'no', 'nah', 'nope'}:
                return False

        recent_beru = [m for m in self.conversation_history if m['role'] == 'beru']
        if not recent_beru:
            return False
        last_beru = recent_beru[-1]['text'].lower()
        return (
            '?' in last_beru
            or any(w in last_beru for w in (
                'want', 'would you', 'do you', 'can i', 'shall i', 'need',
                'like some', 'how about', 'interested', 'would you like',
                'tea', 'help', 'suggest', 'recommend', 'anything else',
            ))
        )

    def answer_casual_reply(self, language='en'):
        if self.is_owner():
            if language == 'sv':
                return 'Okej bro, helt lugnt! Vad vill du göra?'
            if language == 'ar':
                return 'تمام! ماذا تريد أن نفعل؟'
            return "Alright bro, all good! What's on your mind?"

        name = self.get_user_name() or 'there'
        if language == 'sv':
            return f'Okej {name}! Vad kan jag hjälpa dig med?'
        return f'Okay {name}! How can I help you?'

    def is_asking_about_self(self, text):
        if self.is_owner():
            return False
        text_lower = text.lower()
        if 'omar' in text_lower:
            return False
        if any(trigger in text_lower for trigger in SELF_KNOWLEDGE_TRIGGERS):
            return True
        if 'about me' in text_lower or 'about myself' in text_lower:
            return True
        return False

    def is_beru_experience_question(self, text):
        return self.knowledge.is_beru_experience_question(text)

    def is_beru_activity_question(self, text):
        return self.knowledge.is_beru_activity_question(text)

    def answer_beru_activity_question(self, user_input='', language='en'):
        return self.knowledge.answer_beru_activity_question(
            user_input, language, memory=self
        )

    def answer_beru_experience_question(self, language='en'):
        return self.knowledge.answer_beru_experience_question('', language, memory=self)

    def is_asking_about_other_person(self, text):
        if self.is_owner():
            return False
        text_lower = text.lower()
        if self.is_identity_question(text) or self.is_name_question(text):
            return False
        if any(trigger in text_lower for trigger in OTHER_PERSON_TRIGGERS):
            return True
        if re.search(r'(?:another|other)\s+\w+', text_lower):
            return True
        if self._extract_person_name_from_query(text):
            if any(w in text_lower for w in ('know', 'känner', 'vet du', 'heard of', 'met')):
                return True
        return False

    def _extract_person_name_from_query(self, text):
        patterns = [
            r'([A-ZÅÄÖ][a-zåäö]+(?:\s+[A-ZÅÄÖ][a-zåäö]+)+)',
            r'(?:another|other)\s+([A-Za-zåäö]+)',
            r'(?:know|känner)\s+(?:a|an|another|other)?\s*([A-ZÅÄÖ][a-zåäö]+(?:\s+[A-ZÅÄÖ][a-zåäö]+)?)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text.strip())
            if match:
                name = match.group(1).strip()
                if name.lower() not in {'do', 'you', 'her', 'him', 'them', 'the', 'another', 'other'}:
                    return self._title_full_name(name)
        return None

    def _find_users_excluding(self, exclude_id=None):
        results = []
        for user_id, user in self.known_users.items():
            if user.get('is_owner'):
                continue
            if exclude_id and user_id == exclude_id:
                continue
            results.append((user_id, user))
        return results

    def _find_users_by_first_name(self, first_name, exclude_id=None):
        first_lower = first_name.lower()
        results = []
        for user_id, user in self.known_users.items():
            if user.get('is_owner'):
                continue
            if exclude_id and user_id == exclude_id:
                continue
            if user.get('first_name', '').lower() == first_lower:
                results.append((user_id, user))
        return results

    def _describe_user_briefly(self, user, language='en'):
        full_name = user.get('full_name', 'Unknown')
        visits = user.get('visit_count', 0)
        topics = user.get('topics', [])[:3]
        parts = [full_name]
        if visits:
            parts.append(f"{visits} visit(s)")
        if topics:
            parts.append(f"talked about: {', '.join(topics)}")
        return '; '.join(parts)

    def get_all_guest_users(self):
        guests = []
        for user_id, user in self.known_users.items():
            if user.get('is_owner') or user_id == OWNER_NAME:
                continue
            guests.append((user_id, user))
        guests.sort(key=lambda item: item[1].get('last_seen') or '', reverse=True)
        return guests

    def is_owner_users_full_list_request(self, text):
        text_lower = text.lower()
        return any(trigger in text_lower for trigger in OWNER_USERS_FULL_LIST_TRIGGERS)

    def _format_user_summary(self, user):
        full_name = user.get('full_name', 'Unknown')
        visits = user.get('visit_count', 0)
        last_seen = (user.get('last_seen') or '')[:10]
        line = f"{full_name} ({visits} visit(s)"
        if last_seen:
            line += f", last {last_seen}"
        return line + ")"

    def _recent_conversation_text(self, max_messages=8):
        return ' '.join(m['text'] for m in self.conversation_history[-max_messages:]).lower()

    def is_owner_users_conversation_context(self):
        recent = self._recent_conversation_text(12)
        hints = [
            'talk to', 'talked to', 'who did you', 'other people', 'other person',
            'someone', 'friend', 'users', 'guest', 'new friends', 'make new friends',
            'sara', 'talk about', 'did you talk', 'who is this friend',
        ]
        return any(h in recent for h in hints)

    def is_owner_users_question(self, text):
        if not self.is_owner():
            return False
        text_lower = text.lower()
        if any(trigger in text_lower for trigger in OWNER_USERS_TRIGGERS):
            return True
        if self.is_owner_users_full_list_request(text):
            return True
        if any(p in text_lower for p in (
            'who is this friend', 'who was that', 'about what did you',
            'what did you talk', 'who is that person', 'who were they',
            'people you talked to', 'users you talked to', 'people you talk to',
            'list them', 'list the users', 'list those users',
        )):
            return True
        if any(p in text_lower for p in (
            "don't remember", 'dont remember', 'are you sure', 'you do know',
            'you must know', 'check your memory', 'check memory',
        )):
            recent = self._recent_conversation_text()
            if any(t in recent for t in OWNER_USERS_TRIGGERS) or self.is_owner_users_conversation_context():
                return True
        if self.is_owner_users_conversation_context():
            if any(w in text_lower for w in (
                'friend', 'who is', 'who was', 'talk about', 'talked about',
                'list', 'users', 'people', 'them', 'names',
            )):
                return True
        return False

    def _format_user_for_owner(self, user_id, user):
        full_name = user.get('full_name', 'Unknown')
        visits = user.get('visit_count', 0)
        last_seen = (user.get('last_seen') or '')[:10]
        topics = user.get('topics', [])
        session_count = len(user.get('sessions', []))
        line = f"{full_name}  -  {visits} visit(s)"
        if last_seen:
            line += f", last seen {last_seen}"
        if topics:
            line += f", topics: {', '.join(topics[:6])}"
        if session_count:
            line += f", {session_count} saved chat(s)"
        return line

    def answer_owner_users_question(self, text, language='en'):
        text_lower = text.lower()

        # "who is this friend?"  -  means a guest user, NOT Wikipedia
        if any(p in text_lower for p in (
            'who is this friend', 'who was this friend', 'who is that friend',
            'who was the friend', 'who is that person', 'who were they',
        )):
            guests = self.get_all_guest_users()
            if not guests:
                if language == 'sv':
                    return 'Ingen "vän" bro  -  jag har inte pratat med någon gäst ännu, bara dig.'
                return 'No "friend" bro  -  I have not chatted with any guests yet, just you.'
            uid, user = guests[0]
            detail = self._format_user_for_owner(uid, user)
            if language == 'sv':
                return (
                    f'Inte en kändis bro  -  jag menar någon från mitt minne. '
                    f'Senast pratade jag med {user["full_name"]}. {detail}'
                )
            return (
                f'Not a celebrity bro  -  I mean someone from my user memory. '
                f'Most recently I talked to {user["full_name"]}. {detail}'
            )

        # "about what did you talk?"
        if any(p in text_lower for p in (
            'about what did you', 'what did you talk', 'what did you discuss',
            'talked about what', 'talk about what',
        )):
            guests = self.get_all_guest_users()
            if not guests:
                if language == 'sv':
                    return 'Inga sparade samtal med gäster ännu bro.'
                return 'No saved guest conversations yet bro.'
            uid, user = guests[0]
            topics = user.get('topics', [])
            if topics:
                if language == 'sv':
                    return f'Med {user["full_name"]} pratade vi om: {", ".join(topics[:8])}.'
                return f'With {user["full_name"]}, we talked about: {", ".join(topics[:8])}.'
            sessions = user.get('sessions', [])
            if sessions:
                human_msgs = [
                    m['text'] for m in sessions[-1].get('messages', [])
                    if m.get('role') == 'human'
                ][:4]
                if human_msgs:
                    if language == 'sv':
                        return f'Med {user["full_name"]}, senaste ämnen: {"; ".join(human_msgs)}.'
                    return f'With {user["full_name"]}, recent topics from saved chat: {"; ".join(human_msgs)}.'
            if language == 'sv':
                return f'Jag har {user["full_name"]} i minnet men inga detaljer sparade ännu bro.'
            return f'I have {user["full_name"]} in memory but no detailed topics saved yet bro.'

        # "did you talk to someone today?"
        if 'today' in text_lower and any(w in text_lower for w in ('talk', 'someone', 'friend', 'anyone')):
            from datetime import date
            today = date.today().isoformat()
            guests_today = [
                (uid, u) for uid, u in self.get_all_guest_users()
                if (u.get('last_seen') or '')[:10] == today
            ]
            if guests_today:
                names = ', '.join(u['full_name'] for _, u in guests_today)
                if language == 'sv':
                    return f'Ja bro! Idag pratade jag med: {names}.'
                return f'Yeah bro! Today I talked to: {names}.'
            if language == 'sv':
                return 'Inga gästchattar idag bro  -  bara du just nu i den här sessionen.'
            return 'No guest chats today bro  -  just you in this session right now.'

        name = self._extract_person_name_from_query(text)
        if name:
            matches = self.find_users_by_full_name(name)
            if not matches:
                partial = self._find_users_by_first_name(name.split()[0])
                matches = [uid for uid, _ in partial]
            if matches:
                user = self.known_users[matches[0]]
                detail = self._format_user_for_owner(matches[0], user)
                if language == 'sv':
                    return f"Ja bro, här är vad jag har om {user['full_name']}: {detail}."
                return f"Yeah bro, here is what I have on {user['full_name']}: {detail}."

        guests = self.get_all_guest_users()
        if not guests:
            if language == 'sv':
                return 'Nä bro, inga andra användare ännu  -  bara du!'
            return 'Nah bro, no other users yet  -  just you so far!'

        total = len(guests)
        want_full = self.is_owner_users_full_list_request(text)

        if want_full:
            shown = guests[:OWNER_USERS_FULL_LIST_MAX]
            lines = [
                self._format_user_for_owner(uid, user)
                for uid, user in shown
            ]
            if language == 'sv':
                header = f'Här är {len(shown)} av {total} användare (kompakt):'
                footer = (
                    f'... och {total - len(shown)} till. Fråga om någon vid namn för full info.'
                    if total > len(shown) else
                    'Fråga om någon vid namn för full info.'
                )
            else:
                header = f'Here are {len(shown)} of {total} users (compact):'
                footer = (
                    f'... and {total - len(shown)} more. Ask about someone by name for full details.'
                    if total > len(shown) else
                    'Ask about someone by name for full details.'
                )
            return header + '\n\n' + '\n'.join(f'- {line}' for line in lines) + '\n\n' + footer

        # Default: short summary  -  recent users only
        recent = guests[:OWNER_USERS_SUMMARY_LIMIT]
        lines = [self._format_user_summary(user) for _, user in recent]
        remaining = total - len(recent)

        if language == 'sv':
            header = f'Ja bro! Jag känner {total} andra person(er). Senast aktiva:'
            footer = (
                f'... och {remaining} till. Säg "lista alla användare" för full lista, '
                f'eller fråga om någon vid namn (t.ex. "berätta om Sara Hassan").'
                if remaining > 0 else
                'Fråga om någon vid namn för full info.'
            )
        else:
            header = f'Yeah bro! I know {total} other person(s). Most recently active:'
            footer = (
                f'... and {remaining} more. Say "list all users" for the full list, '
                f'or ask about someone by name (e.g. "tell me about Sara Hassan").'
                if remaining > 0 else
                'Ask about someone by name for full details.'
            )

        return header + '\n\n' + '\n'.join(f'- {line}' for line in lines) + '\n\n' + footer

    def answer_about_self(self, language='en'):
        if not self.is_session_identified():
            return self.ask_to_identify(language)

        full_name = self.get_user_full_name() or self.get_user_name()
        visits = self.get_visit_count()
        topics = self.get_user_topics(self.session.get('user_id'))

        if language == 'sv':
            lines = [f"Det här vet jag om dig, {full_name}:"]
            lines.append(f"Du har pratat med mig {visits} gång(er).")
            if topics:
                lines.append(f"Ämnen vi pratat om: {', '.join(topics)}.")
            else:
                lines.append("Vi håller just på att lära känna varandra.")
            return ' '.join(lines)

        if language == 'ar':
            lines = [f"إليك ما أعرفه عنك، {full_name}:"]
            lines.append(f"تحدثنا {visits} مرة.")
            if topics:
                lines.append(f"مواضيع تحدثنا عنها: {', '.join(topics)}.")
            return ' '.join(lines)

        lines = [f"Here is what I know about you, {full_name}:"]
        lines.append(f"You have talked with me {visits} time(s).")
        if topics:
            lines.append(f"Topics we have discussed: {', '.join(topics)}.")
        else:
            lines.append("We are still getting to know each other  -  I will remember more as we talk.")
        return ' '.join(lines)

    def answer_about_other_person(self, text, language='en'):
        if not self.is_session_identified():
            return self.ask_to_identify(language)

        current_id = self.session.get('user_id')
        current_name = self.get_user_full_name() or self.get_user_name()
        text_lower = text.lower()

        name = self._extract_person_name_from_query(text)
        if not name:
            match = re.search(r'(?:another|other)\s+(\w+)', text_lower)
            if match:
                name = match.group(1).capitalize()

        if name:
            if self.normalize_full_name(name) == self.normalize_full_name(current_name or ''):
                if language == 'sv':
                    return f"Ja  -  det är du, {current_name}! Det är den person jag pratar med just nu."
                return f"Yes  -  that is you, {current_name}! You are the person I am talking to right now."

            exact = self.find_users_by_full_name(name)
            if exact:
                user = self.known_users[exact[0]]
                if exact[0] == current_id:
                    if language == 'sv':
                        return f"Ja, det är du  -  {current_name}!"
                    return f"Yes, that is you  -  {current_name}!"
                brief = self._describe_user_briefly(user, language)
                if language == 'sv':
                    return f"Ja, jag känner {user['full_name']}. {brief}."
                return f"Yes, I know {user['full_name']}. {brief}."

            partial = self._find_users_by_first_name(name.split()[0], exclude_id=None)
            partial = [(uid, u) for uid, u in partial if uid != current_id]
            if partial:
                names = ', '.join(u['full_name'] for _, u in partial)
                if language == 'sv':
                    return (
                        f"Ja, jag känner {names}  -  en annan person än dig ({current_name}). "
                        f"Det är inte samma person som du."
                    )
                return (
                    f"Yes, I know {names}  -  a different person from you ({current_name}). "
                    f"They are not the same person as you."
                )

            if language == 'sv':
                return (
                    f"Nej, jag har ingen {name} i mitt minne. "
                    f"Jag känner dig som {current_name}."
                )
            return (
                f"No, I do not have {name} in my memory. "
                f"I know you as {current_name}."
            )

        if 'another' in text_lower or 'other' in text_lower:
            others = self._find_users_excluding(exclude_id=current_id)
            if not others:
                if language == 'sv':
                    return f"Nej, du ({current_name}) är den enda gästen jag känner förutom Omar."
                return f"No, you ({current_name}) are the only guest I know besides Omar."
            names = ', '.join(u['full_name'] for _, u in others)
            if language == 'sv':
                return f"Ja, jag känner också {names}. De är andra personer än dig ({current_name})."
            return f"Yes, I also know {names}. They are different people from you ({current_name})."

        if language == 'sv':
            return "Vem menar du? Säg hela namnet så kollar jag mitt minne."
        return "Who do you mean? Tell me their full name and I will check my memory."

    def is_conversation_partner_question(self, text):
        text_lower = text.lower()
        return any(t in text_lower for t in CONVERSATION_PARTNER_TRIGGERS)

    def answer_conversation_partner(self, language='en'):
        if not self.is_session_identified():
            return self.ask_to_identify(language)
        name = self.get_user_full_name() or self.get_user_name()
        if self.is_owner():
            if language == 'sv':
                return (
                    'Du pratar med mig, Beru! Jag vet att du är Omar, '
                    'min skapare och bästa kompis.'
                )
            if language == 'ar':
                return (
                    'أنت تتحدث معي، Beru! أعرف أنك Omar، من أنشأني وأفضل صديق لي.'
                )
            return (
                'You are talking to me, Beru! I know you are Omar, '
                'my creator and best bro.'
            )
        if language == 'sv':
            return f'Du pratar med mig, Beru! Just nu pratar jag med dig, {name}.'
        if language == 'ar':
            return f'أنت تتحدث معي، Beru! أنا أتحدث معك الآن يا {name}.'
        return f'You are talking to me, Beru! Right now I am talking with you, {name}.'

    def is_date_clarification(self, text):
        if not self.is_owner():
            return False
        text_lower = text.lower()
        if any(t in text_lower for t in DATE_CLARIFICATION_TRIGGERS):
            return True
        return parse_date_clarification(text) is not None

    def handle_date_clarification(self, text, language='en'):
        parsed = parse_date_clarification(text)
        if not parsed:
            if language == 'sv':
                return 'Jag fattar inte datumet bro. Säg t.ex. "när jag säger förrgår menar jag den 29 maj".'
            return 'I did not catch the date bro. Say e.g. "when I say yesterday I mean May 29".'

        keyword = parsed.get('keyword')
        event_iso = parsed['event_date']
        hint = 'uppsats' if 'uppsats' in text.lower() or 'thesis' in text.lower() else ''
        updated = update_facts_event_date(
            self.learned_omar_facts,
            event_iso,
            keyword=keyword,
            text_hint=hint,
        )
        if not updated and self.learned_omar_facts:
            last = self.learned_omar_facts[-1]
            if isinstance(last, dict):
                last['event_date'] = event_iso
                updated = [last]

        self.knowledge.set_learned_facts(self.learned_omar_facts)
        self.save_memory()

        when = format_date_for_language(event_iso, language)
        if language == 'sv':
            if updated:
                fact = fact_text(updated[-1])
                return (
                    f'Okej bro! Jag sparade att det hände {when}: {fact}. '
                    f'När du säger relativa datum räknar jag från dagens datum ({format_now("sv")}).'
                )
            return f'Okej! Jag noterade datumet {when}.'
        if language == 'ar':
            if updated:
                fact = fact_text(updated[-1])
                return f'حسناً! حفظت أن ذلك كان في {when}: {fact}.'
            return f'حسناً! سجلت التاريخ {when}.'
        if updated:
            fact = fact_text(updated[-1])
            return f'Got it bro! That happened on {when}: {fact}.'
        return f'Noted the date: {when}.'

    def is_time_question(self, text):
        text_lower = text.lower()
        return any(t in text_lower for t in TIME_QUESTION_TRIGGERS)

    def answer_time_question(self, language='en'):
        return format_now(language)

    def is_owner_when_question(self, text):
        if not self.is_owner():
            return False
        text_lower = text.lower()
        if any(t in text_lower for t in ('what time', 'vad är klockan', 'كم الساعة')):
            return False
        return any(t in text_lower for t in OWNER_WHEN_QUESTION_TRIGGERS)

    def is_when_day_detail_followup(self, text):
        if not self.is_owner():
            return False
        tl = text.strip().lower().strip('.!,?؛')
        if tl not in WHEN_DAY_DETAIL_TRIGGERS:
            return False
        recent = self.conversation_history[-6:]
        combined = ' '.join(
            m['text'].lower() for m in recent if m.get('role') == 'beru'
        )
        markers = (
            'متى', 'when', 'när', 'عام', 'year', 'år', 'تاريخ', 'date',
            'سلمت', 'submitted', 'lämnade', 'مشروع', 'project',
        )
        return any(m in combined for m in markers)

    def _when_query_from_history(self):
        for m in reversed(self.conversation_history):
            if m.get('role') == 'human' and self.is_owner_when_question(m['text']):
                return m['text']
        return ''

    def answer_owner_when_question(self, text, language='en', *, day_detail=False):
        query = text or self._when_query_from_history()
        matches = facts_matching_when_query(self.learned_omar_facts, query)

        if not matches:
            if language == 'sv':
                return (
                    'Jag har inget exakt datum sparat för det bro. '
                    'Säg t.ex. "jag lämnade in uppsatsen den 29 maj" så sparar jag dagen.'
                )
            if language == 'ar':
                return (
                    'ما عندي تاريخ محدد محفوظ لهذا. '
                    'قل لي متى حصل، مثل: سلمت مشروع الجامعة في 29 مايو، وسأحفظ اليوم.'
                )
            return (
                'I do not have an exact date saved for that bro. '
                'Tell me when it happened, e.g. "I submitted the project on May 29", '
                'and I will save the day.'
            )

        entry = matches[0]
        reply = when_reply_for_fact(entry, language, day_detail=day_detail)
        if reply:
            return reply
        when = format_event_date(entry, language)
        if when:
            if language == 'sv':
                if day_detail:
                    return f'Datumet var {when}.'
                return f'Det var {when} bro.'
            if language == 'ar':
                if day_detail:
                    return f'التاريخ كان {when}.'
                return f'حسب ذاكرتي، كان ذلك في {when}.'
            if day_detail:
                return f'The date was {when}.'
            return f'According to my memory, that was on {when}.'

        import re
        fact = fact_text(entry)
        year_m = re.search(r'\b(20\d{2})\b', fact)
        if language == 'sv':
            if year_m:
                return (
                    f'Jag vet bara att det nämns år {year_m.group(1)} i minnet, '
                    f'inte vilken dag. Säg exakt datum så sparar jag det.'
                )
            return 'Jag har fakta sparat men inget kalenderdatum för det ännu bro.'
        if language == 'ar':
            if year_m:
                return (
                    f'أعرف من سيرتك أن الأمر مرتبط بعام {year_m.group(1)}، '
                    f'لكن لا يوجد يوم محدد محفوظ. قل لي التاريخ الكامل وسأحفظه.'
                )
            return 'عندي معلومة محفوظة لكن بدون تاريخ يوم محدد. قل لي التاريخ وسأحفظه.'
        if year_m:
            return (
                f'I only know the year {year_m.group(1)} from memory, not the exact day. '
                f'Tell me the full date and I will save it.'
            )
        return 'I have something saved but no calendar date for it yet bro.'

    def answer_when_day_detail_followup(self, language='en'):
        return self.answer_owner_when_question(
            self._when_query_from_history(), language, day_detail=True
        )

    @staticmethod
    def is_today_activity_question(text):
        text_lower = text.lower()
        return any(t in text_lower for t in TODAY_ACTIVITY_QUESTION_TRIGGERS)

    def is_owner_today_question(self, text):
        return self.is_owner() and self.is_today_activity_question(text)

    def respond_today_question_before_identify(self, language='en'):
        """User asked about their day before Beru knows who is speaking."""
        if self.is_awaiting_owner_confirm():
            if language == 'sv':
                return (
                    'Hej bro! Det kan jag kolla, men först: är det du Omar? '
                    'Säg ja och lösenordet, så vet jag att det är du.'
                )
            if language == 'ar':
                return (
                    'مرحباً! أستطيع أن أتحقق، لكن أولاً: هل أنت Omar؟ '
                    'قل نعم وكلمة المرور.'
                )
            return (
                'Hey bro! I can check that, but first: is this you Omar? '
                'Say yes and your password so I know it is you.'
            )
        if language == 'sv':
            return (
                'Hej! För att svara på vad du gjort idag behöver jag veta vem du är. '
                'Är det Omar? Säg ja, eller ditt fullständiga namn.'
            )
        if language == 'ar':
            return 'مرحباً! لأجيب عن يومك أحتاج أعرف من أتحدث معه. هل أنت Omar؟'
        return (
            'Hey! To answer what you did today I need to know who you are. '
            'Is this Omar? Say yes, or tell me your full name.'
        )

    def is_owner_profile_short_request(self, text):
        if not self.is_owner():
            return False
        text_lower = text.lower()
        return any(t in text_lower for t in OWNER_PROFILE_SHORT_TRIGGERS)

    def answer_owner_profile_short(self, language='en'):
        return self.knowledge.format_omar_profile_summary(
            language, self.learned_omar_facts
        )

    def _awaiting_today_story(self):
        if self.session.get('prompted_today_story'):
            return True
        recent = [m for m in self.conversation_history if m.get('role') == 'beru']
        if not recent:
            return False
        last = recent[-1]['text'].lower()
        markers = (
            'berättat något för mig som hände just idag',
            'tell me anything that happened today',
            'vad har du gjort idag',
            'what did you do today',
            'inget sparat om din dag',
            "don't have anything saved about your day",
        )
        return any(m in last for m in markers)

    def _recent_day_chat_context(self):
        recent = self.conversation_history[-8:]
        combined = ' '.join(m['text'].lower() for m in recent)
        return any(w in combined for w in (
            'ryggpasset', 'rygg och', 'hur kändes', 'vad har du gjort idag',
            'chill först', 'sparad om din dag', 'bra dag', 'gym idag',
            'chillat', 'gymmet', 'haft en bra dag',
        ))

    def is_owner_day_chat_followup(self, text):
        """Short replies after talking about today's activities (not a new day report)."""
        if not self.is_owner():
            return False
        if not self._recent_day_chat_context() and not self.session.get('today_story_logged'):
            return False

        tl = text.lower().strip().strip('.!,')
        followup_markers = (
            'kändes bra', 'det kändes', 'det var bra', 'felt good', 'felt great',
            'har ju berättat', 'redan berättat', 'sa jag ju', 'already told',
            'berättat till dig', 'told you what', 'ska sova', 'god natt',
            'going to sleep', 'going to bed', 'vad menar du', 'what do you mean',
            'menar du med', 'lätt och effektiv',
        )
        if any(m in tl for m in followup_markers):
            return True
        if '?' in tl and any(m in tl for m in ('menar', 'mean', 'vad ', 'what ')):
            return True
        if len(tl.split()) <= 6 and any(w in tl for w in ('bra', 'good', 'nice', 'skönt', 'okej', 'ok')):
            return True
        return False

    def answer_owner_day_chat_followup(self, text, language='en'):
        tl = text.lower()

        if any(p in tl for p in ('vad menar', 'menar du', 'what do you mean', 'lätt och effektiv')):
            if language == 'sv':
                return (
                    'Förlåt bro, klumpigt sagt av mig! Jag menade inte "lätt och effektiv" som '
                    'träningsjargong, bara om ryggpasset kändes bra för dig. Och det lät det ju som!'
                )
            return (
                "Sorry bro, I worded that badly! I didn't mean easy vs hard reps, "
                "just whether the back session felt good. Sounds like it did!"
            )

        if any(p in tl for p in ('har ju berättat', 'redan berättat', 'already told', 'sa jag ju', 'berättat till dig')):
            if any(p in tl for p in ('sova', 'sleep', 'god natt', 'bed')):
                if language == 'sv':
                    return (
                        'Du har helt rätt bro, jag har koll på din dag, chill och gym. '
                        'Sov gott, vi hörs!'
                    )
                return "You're right bro, I've got your day, chill and gym. Sleep well!"
            if language == 'sv':
                return 'Stämmer bro, jag minns, chill och gym idag. Något mer innan du chillar?'
            return "True bro, I remember, chill and gym today. Anything else on your mind?"

        if any(p in tl for p in ('ska sova', 'god natt', 'going to sleep', 'going to bed')):
            if language == 'sv':
                return 'Sov gott Omar! Vi hörs imorgon bro.'
            return 'Sleep well Omar! Catch you tomorrow bro.'

        if any(p in tl for p in ('kändes bra', 'det kändes', 'felt good', 'det var bra')) or (
            len(tl.split()) <= 5 and 'bra' in tl
        ):
            if language == 'sv':
                return (
                    'Härligt bro! Kul att rygg och cardio satt bra. '
                    'Ska du ta det lugnt resten av kvällen?'
                )
            return (
                'Nice bro! Glad the back and cardio felt good. '
                'Taking it easy for the rest of the evening?'
            )

        if language == 'sv':
            return 'Okej bro! Jag är med dig.'
        return "Got you bro! I'm with you."

    def is_owner_today_narration(self, text):
        """Owner describing what they did (not a question, not a remember command)."""
        if not self.is_owner():
            return False
        if self.is_omar_remember_instruction(text) or self.is_owner_today_question(text):
            return False
        if self.is_date_clarification(text):
            return False
        if self.is_owner_day_chat_followup(text):
            return False

        text_lower = text.lower().strip()
        narration_blocks = (
            'har ju berättat', 'redan berättat', 'sa jag ju', 'already told',
            'ska sova', 'god natt', 'going to sleep', 'vad menar', 'menar du',
            'kändes bra', 'det kändes', 'det var bra', 'berättat till dig',
        )
        if any(b in text_lower for b in narration_blocks):
            return False

        if '?' in text_lower:
            return False
        if not re.search(r'\b(jag|i)\b', text_lower):
            return False

        question_starts = (
            'vad ', 'what ', 'hur ', 'how ', 'varför', 'why ', 'när ', 'when ',
            'vem ', 'who ', 'kan du', 'can you', 'berätta om', 'tell me about',
        )
        if any(text_lower.startswith(s) for s in question_starts):
            return False

        has_today = 'idag' in text_lower or 'today' in text_lower
        has_activity = any(v in text_lower for v in OWNER_TODAY_NARRATION_VERBS)
        word_count = len(text_lower.split())

        if self.session.get('today_story_logged'):
            return has_activity and word_count >= 8 and has_today

        if self._awaiting_today_story() and has_activity and word_count >= 5:
            return True
        if has_today and has_activity and word_count >= 6:
            return True
        return False

    @staticmethod
    def _short_day_activity_summary(texts, language='en'):
        """Brief summary from stored lines without repeating the full message."""
        combined = ' '.join(texts).lower()
        parts = []
        if any(w in combined for w in ('chill', 'chillat', 'chilled', 'koppla av')):
            parts.append('chillat lite' if language == 'sv' else 'chilled')
        if any(w in combined for w in ('gym', 'gymmet', 'rygg', 'cardio', 'trän', 'trained')):
            parts.append('varit på gymmet' if language == 'sv' else 'been to the gym')
        if any(w in combined for w in ('lunch', 'middag', 'frukost', 'åt', 'ate')):
            parts.append('ätit' if language == 'sv' else 'eaten')
        if any(w in combined for w in ('plugg', 'stud', 'jobb', 'work', 'universitet')):
            parts.append('pluggat/jobbat' if language == 'sv' else 'studied/worked')
        if parts:
            if language == 'sv':
                return ' och '.join(parts)
            if language == 'ar':
                return ' و '.join(parts)
            return ' and '.join(parts)
        if language == 'sv':
            return 'haft en del på gång'
        if language == 'ar':
            return 'عملت أشياء مختلفة'
        return 'been busy'

    def _reply_after_today_narration(self, text, language='en'):
        """Friendly ack + follow-up; respects order and future vs past tense."""
        from src.day_plan import reply_to_day_message

        return reply_to_day_message(text, language)

    def handle_owner_today_narration(self, text, language='en'):
        from datetime import date

        today = date.today().isoformat()
        cleaned = text.strip().strip('. ,;')
        if cleaned and cleaned[0].islower():
            cleaned = cleaned[0].upper() + cleaned[1:]

        entry = new_fact_entry(cleaned)
        entry['event_date'] = today
        self.add_omar_fact(entry)
        self.session['prompted_today_story'] = False
        self.session['today_story_logged'] = True

        return self._reply_after_today_narration(text, language)

    def answer_owner_today_question(self, language='en'):
        from datetime import date

        today = date.today().isoformat()
        matches = facts_on_date(self.learned_omar_facts, today)

        if not matches:
            self.session['prompted_today_story'] = True
            if language == 'sv':
                return (
                    'Hmm, jag har inget sparat om din dag än bro. '
                    'Vad har du gjort idag?'
                )
            if language == 'ar':
                return 'ما عندي شي محفوظ عن يومك بعد. شو عملت اليوم؟'
            return (
                "Hmm, I don't have anything saved about your day yet bro. "
                "What did you do today?"
            )

        self.session['prompted_today_story'] = False
        lines = [fact_text(m) for m in matches]
        summary = self._short_day_activity_summary(lines, language)
        if language == 'sv':
            return f'Ja bro, du har {summary} idag. Hur kändes det?'
        if language == 'ar':
            return f'أيوه، اليوم {summary}. كيف كان شعورك؟'
        return f'Yeah bro, you {summary} today. How did it feel?'

    def answer_from_knowledge(self, user_input, language='en'):
        if self.knowledge.is_beru_activity_question(user_input):
            return self.knowledge.answer_beru_activity_question(
                user_input, language, memory=self
            )

        if self.knowledge.is_beru_experience_question(user_input):
            return self.knowledge.answer_beru_experience_question(
                user_input, language, memory=self
            )

        if self.knowledge.is_beru_self_question(user_input):
            answer = self.knowledge.answer_beru_self_question(
                user_input, language, memory=self
            )
            if answer:
                return answer
            return self.knowledge.dont_know_response(language, 'that about myself')

        if self.knowledge.is_omar_personal_question(user_input, self.is_owner()):
            if not self.is_owner():
                guest = self.get_user_name()
                return self.knowledge.answer_omar_for_guest(
                    user_input, language, guest_name=guest
                )
            answer = self.knowledge.answer_omar_question(
                user_input, language, self.learned_omar_facts
            )
            if answer:
                return answer
            return self.knowledge.dont_know_response(language, 'that about Omar')

        return None

    def mark_as_owner(self, language='en'):
        self.identify_session(OWNER_NAME, language, is_owner=True)
        self.known_users[OWNER_NAME]['permanently_verified'] = True
        self.save_memory()
        print(f"Beru saved {OWNER_NAME} as owner permanently!")

    def set_user(self, name, language='en', notes=''):
        """Legacy helper  -  prefer register_full_name for guests."""
        if ' ' in name.strip():
            status, user_id = self.register_full_name(name, language)
            if status == 'new':
                return
            return
        self.begin_full_name_collection(partial_first_name=self._first_name(name), language=language)

    def get_user_name(self):
        if self.is_session_identified():
            return self.session.get('name')
        return None

    def get_user_full_name(self):
        user_id = self.session.get('user_id')
        if user_id and user_id in self.known_users:
            return self.known_users[user_id].get('full_name')
        if self.is_owner():
            return OWNER_FULL_NAME
        return self.get_user_name()

    def is_known_user(self):
        return self.is_session_identified()

    def is_owner(self):
        return self.is_session_identified() and self.session.get('is_owner', False)

    def is_omar(self):
        return self.is_owner()

    def is_verified(self):
        return self.is_session_identified()

    def get_tone(self):
        if self.is_owner():
            return 'bro'
        return 'formal'

    def greeting_for_session(self, language='en'):
        if self.is_awaiting_owner_confirm():
            if language == 'sv':
                return f'Hej! Är det du {OWNER_NAME}?'
            if language == 'ar':
                return f'مرحباً! هل أنت {OWNER_NAME}؟'
            return f'Hey! Is that you {OWNER_NAME}?'
        if language == 'sv':
            return 'Hej! Jag är Beru. Vem pratar jag med?'
        if language == 'ar':
            return 'مرحباً! أنا Beru. مع من أتحدث؟'
        return 'Hey! I am Beru. Who am I talking to?'

    def formal_greeting(self, name, language='en'):
        display = name if ' ' in name else name
        if language == 'sv':
            return f'Hej {display}! Trevligt att träffa dig. Hur kan jag hjälpa dig?'
        if language == 'ar':
            return f'مرحباً {display}! كيف يمكنني مساعدتك؟'
        return f'Hello {display}! Nice to meet you. How may I help you?'

    def owner_greeting(self, language='en'):
        if language == 'sv':
            return 'Rätt lösenord! Tjena Omar! Vad händer kompis?'
        if language == 'ar':
            name = owner_display_name('ar')
            return f'كلمة المرور صحيحة! أهلاً {name}! كيف حالك يا صديقي؟'
        return 'Correct password! Hey Omar! What is up bro?'

    def set_active_document(self, doc_id, filename):
        self.session['active_document_id'] = doc_id
        self.session['active_document_name'] = filename

    def clear_active_document(self):
        self.session['active_document_id'] = None
        self.session['active_document_name'] = None

    def get_active_document_id(self):
        return self.session.get('active_document_id')

    def get_active_document_name(self):
        return self.session.get('active_document_name')

    def get_active_document_info(self):
        doc_id = self.get_active_document_id()
        if not doc_id:
            return None
        return {
            'id': doc_id,
            'filename': self.get_active_document_name(),
        }

    def answer_pre_upload_document_intent(self, language='en'):
        if language == 'sv':
            return (
                'Absolut! Ladda upp PDF:en med paperclip-knappen, '
                'sen kan du fråga vad den säger eller be mig sammanfatta den.'
            )
        if language == 'ar':
            return (
                'تمام! ارفع ملف PDF باستخدام زر المرفق، '
                'ثم اسألني ماذا يقول أو اطلب ملخصاً.'
            )
        if self.is_owner():
            return (
                "Sounds good bro! Hit the paperclip and upload the PDF, "
                "then ask me what it says or tell me to summarize it."
            )
        return (
            "Sure! Use the paperclip button to upload your PDF, "
            "then ask me what it says or request a summary."
        )
