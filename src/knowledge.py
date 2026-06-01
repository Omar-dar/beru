import json
import os
import re

from src.omar_facts import fact_text, owner_fact_for_reply

OWNER_NAME = 'Omar'
OWNER_FULL_NAME = 'Omar Darwish'

TILD_IDENTITY_PATH = 'data/tild_identity.json'
OMAR_PROFILE_PATH = 'data/omar_profile.json'

OMAR_PERSONAL_TRIGGERS = [
    'about me', 'about myself', 'tell me about me', 'who am i really',
    'my university', 'my degree', 'my school', 'where do i study',
    'what do i study', 'my project', 'my projects', 'what did i build',
    'what have i built', 'my milestone', 'where do i live', 'where am i from',
    'omar darwish', 'about omar', 'tell me about omar', 'who is omar',
    'what do you know about omar', 'do you know omar', 'omar full name',
    'vad vet du om mig', 'berätta om mig', 'var studerar jag',
    'vilket universitet', 'mina projekt', 'berätta om omar', 'vem är omar',
]

OWNER_SELF_TRIGGERS = [
    'about me', 'about myself', 'tell me about me', 'who am i really',
    'what do you know about me', 'what do you remember about me',
    'what have you learned about me', 'what did you learn about me',
    'so what did you learn', 'what did you learn',
    'vad vet du om mig', 'berätta om mig', 'berätta kort', 'vad du vet om mig',
    'vad har du lärt dig om mig',
]

OMAR_ONLY_TRIGGERS = [
    'omar darwish', 'about omar', 'tell me about omar', 'who is omar',
    'what do you know about omar', 'do you know omar', 'omar full name',
    'berätta om omar', 'vem är omar', 'this omar', 'that omar',
]

TILD_SELF_TRIGGERS = [
    'who are you', 'what are you', 'about you', 'your name', 'your purpose',
    'built you', 'made you', 'created you', 'your creator', 'who made you',
    'who built you', 'who created you', 'what can you do', 'are you an ai',
    'vem är du', 'vad är du', 'vad heter du', 'vem skapade dig', 'vem byggde dig',
    'berätta om dig', 'hur fungerar du', 'what is tild',
]

TILD_EXPERIENCE_TRIGGERS = [
    'did you have fun', 'had fun', 'have fun today', 'have fun', 'enjoy today',
    'did you enjoy', 'do you feel', 'how do you feel', 'are you happy',
    'did you like talking', 'was it fun', 'did you have a good day',
    'do you have feelings', 'do you have emotions', 'did you feel',
    'personal experience', 'did you enjoy talking', 'enjoyed talking',
    'good conversation', 'how was your day', 'how has your day',
    'har du haft kul', 'hade du roligt', 'känner du', 'har du känslor',
    'hur mår du', 'roligt idag',
]

TILD_ACTIVITY_TRIGGERS = [
    'what are you doing', 'whatcha doing', 'what you doing', 'what u doing',
    'what are you up to', 'what you up to', 'what are u doing', 'what r u doing',
    'vad gör du', 'vad håller du på med',
]

SEARCH_BLOCK_TRIGGERS = OMAR_PERSONAL_TRIGGERS + TILD_SELF_TRIGGERS + [
    'do you know me', 'do you know who i am', 'what is my name', 'who am i',
]

DEEPER_DETAIL_TRIGGERS = [
    'go deeper', 'more detail', 'more details', 'tell me more', 'more about',
    'expand on', 'want more', 'give me more', 'elaborate',
    'gå djupare', 'mer om', 'berätta mer',
]

OWNER_CATEGORY_QUERIES = {
    'instructions': [
        'my instructions', 'what i asked you to remember', 'what i told you to remember',
        'my preferences', 'how i asked you to behave', 'what you remember i told',
    ],
    'education': [
        'my education', 'my university', 'my degree', 'my studies',
        'where do i study', 'what do i study', 'my school',
    ],
    'skills': ['my skills', 'my skill', 'programming languages', 'tech stack', 'technologies i'],
    'projects': ['my projects', 'my project', 'what did i build', 'what have i built'],
    'work': ['my work', 'my job', 'work experience', 'my work experience'],
    'languages': ['my languages', 'what languages do i', 'languages i speak'],
}

CATEGORY_TOPIC_WORDS = {
    'instructions': ['instruction', 'remember', 'preference', 'rule'],
    'education': [
        'education', 'university', 'universitet', 'degree', 'study', 'studies',
        'school', 'utbildning', 'kandidat', 'examen', 'student', 'course', 'betyg',
    ],
    'skills': ['skills', 'skill', 'programming', 'tech', 'framework', 'färdigheter'],
    'projects': ['projects', 'project', 'tild', 'treely', 'built', 'projekt'],
    'work': ['work', 'job', 'restaurant', 'karlstad', 'server', 'arbete'],
    'languages': ['languages', 'language', 'speak', 'svenska', 'arabic', 'fluent'],
}

DETAIL_OFFER_EN = (
    'Want more on education, projects, skills, work, languages, or your instructions?'
)
DETAIL_OFFER_SV = (
    'Vill du ha mer om utbildning, projekt, skills, jobb, språk eller dina instruktioner?'
)
GUEST_DETAIL_OFFER_EN = 'Want to know more about his projects, studies, or skills?'
GUEST_DETAIL_OFFER_SV = 'Vill du veta mer om hans projekt, studier eller skills?'


def _load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


class TildKnowledge:
    def __init__(self):
        self.tild_identity = _load_json(TILD_IDENTITY_PATH)
        self.omar_profile = _load_json(OMAR_PROFILE_PATH)
        self.learned_omar_facts = []

    def set_learned_facts(self, facts):
        self.learned_omar_facts = facts or []

    def is_asking_about_omar(self, text):
        text_lower = text.lower()
        if 'omar' not in text_lower:
            return False
        hints = [
            'who is', 'what is', 'tell me about', 'know about', 'this omar',
            'who was', 'about omar', 'you asked', 'asked if', 'is he',
            'vem är', 'vad är', 'berätta om', 'den här omar',
        ]
        return any(h in text_lower for h in hints)

    def is_omar_personal_question(self, text, is_owner=False):
        text_lower = text.lower()
        if is_owner:
            teaching_triggers = [
                'remember that', 'remember this', 'forget that', 'forget this',
                'forget it', 'keep in mind', "don't forget", 'dont forget',
            ]
            if any(t in text_lower for t in teaching_triggers):
                return False

        if self.is_asking_about_omar(text):
            return True

        if is_owner:
            if any(trigger in text_lower for trigger in OMAR_PERSONAL_TRIGGERS):
                return True
            if any(w in text_lower for w in [' my ', ' me ', ' i ', ' mine ', ' myself']):
                personal_hints = [
                    'university', 'degree', 'study', 'project', 'build', 'built',
                    'milestone', 'job', 'work', 'name', 'from', 'live',
                    'universitet', 'studera', 'projekt', 'heter', 'bor',
                ]
                if any(h in text_lower for h in personal_hints):
                    return True
            return False

        return any(trigger in text_lower for trigger in OMAR_ONLY_TRIGGERS)

    def is_tild_self_question(self, text):
        text_lower = text.lower()
        if self.is_tild_activity_question(text):
            return False
        if re.search(r'what are you (doing|up to)', text_lower):
            return False
        return any(trigger in text_lower for trigger in TILD_SELF_TRIGGERS)

    def is_tild_activity_question(self, text):
        text_lower = text.lower()
        return any(trigger in text_lower for trigger in TILD_ACTIVITY_TRIGGERS)

    def is_tild_experience_question(self, text):
        text_lower = text.lower()
        return any(trigger in text_lower for trigger in TILD_EXPERIENCE_TRIGGERS)

    def should_block_search(self, text, is_owner=False):
        text_lower = text.lower()
        if self.is_omar_personal_question(text, is_owner):
            return True
        if self.is_tild_self_question(text):
            return True
        return any(trigger in text_lower for trigger in SEARCH_BLOCK_TRIGGERS)

    def get_tild_identity_prompt(self):
        identity = self.tild_identity
        lines = [
            f"Your name is {identity.get('name', 'Tild')}.",
            f"You were built from scratch by {identity.get('creator', OWNER_FULL_NAME)} using Python and PyTorch.",
            identity.get('type', 'Personal AI assistant') + '.',
        ]
        for fact in identity.get('facts', []):
            lines.append(fact)
        for cap in identity.get('capabilities', []):
            lines.append(f"You can: {cap}.")
        return '\n'.join(lines)

    def get_omar_facts_prompt(self, learned_facts=None):
        profile = self.omar_profile
        lines = [
            f"Permanent facts about {OWNER_FULL_NAME} (your creator and owner):",
            f"- Full name: {profile.get('full_name', OWNER_FULL_NAME)}",
            f"- Role: {profile.get('role', 'Creator of Tild')}",
            f"- University: {profile.get('university', 'University of Gothenburg')}",
            f"- Degree: {profile.get('degree', 'Software Engineering')}",
            f"- Location: {profile.get('location', 'Gothenburg, Sweden')}",
        ]
        for project in profile.get('projects', []):
            lines.append(f"- Project: {project}")
        for milestone in profile.get('milestones', []):
            lines.append(f"- Milestone: {milestone}")
        lines.append(
            "OMAR'S SAVED MEMORIES (things Omar did or told you — NOT your own experiences; "
            "when speaking to Omar, use YOU for these events, never I):"
        )
        for learned in (learned_facts or self.learned_omar_facts):
            raw = fact_text(learned)
            lang = 'sv' if re.search(r'\b(jag|min|mig)\b', raw, re.I) else 'en'
            lines.append(f"- Omar memory: {owner_fact_for_reply(raw, lang)}")
        return '\n'.join(lines)

    @staticmethod
    def _to_second_person(text, name=OWNER_FULL_NAME, first_name=OWNER_NAME):
        """Rewrite stored facts so Tild speaks directly to Omar."""
        if not text:
            return text
        out = text
        out = re.sub(re.escape(name), 'you', out, flags=re.I)
        out = re.sub(rf'\b{re.escape(first_name)}\b(?!\s+Darwish)', 'you', out, flags=re.I)
        out = re.sub(r'\bHe\b', 'You', out)
        out = re.sub(r'\bhe\b', 'you', out)
        out = re.sub(r'\bHis\b', 'Your', out)
        out = re.sub(r'\bhis\b', 'your', out)
        out = re.sub(r'\bHim\b', 'you', out)
        out = re.sub(r'\bhim\b', 'you', out)
        out = re.sub(r'\bYou are you\b', 'You are', out, flags=re.I)
        out = re.sub(r'\byou you\b', 'you', out, flags=re.I)
        out = re.sub(r'\bYou is\b', 'You are', out)
        out = re.sub(r'\byou is\b', 'you are', out, flags=re.I)
        out = re.sub(r'\bYou has\b', 'You have', out)
        out = re.sub(r'\byou has\b', 'you have', out, flags=re.I)
        out = re.sub(r'\bYou was\b', 'You were', out)
        out = re.sub(r'\byou was\b', 'you were', out, flags=re.I)
        for wrong, right in (
            (r'\bYou knows\b', 'You know'),
            (r'\byou knows\b', 'you know'),
            (r'\bYou uses\b', 'You use'),
            (r'\byou uses\b', 'you use'),
            (r'\bYou works\b', 'You work'),
            (r'\byou works\b', 'you work'),
        ):
            out = re.sub(wrong, right, out, flags=re.I)
        out = owner_fact_for_reply(out, 'sv' if re.search(r'\b(jag|min|mig)\b', out, re.I) else 'en')
        if out and out[0].islower():
            out = out[0].upper() + out[1:]
        return out

    @staticmethod
    def _is_instruction_fact(fact):
        """Short owner instructions  -  not CV/document extracts."""
        fact = fact_text(fact)
        fl = fact.lower()
        if len(fact) > 110:
            return False
        cv_markers = (
            'universitet', 'university', 'typescript', 'javascript', 'kotlin',
            'projekt', 'project', 'github', 'servitör', 'restaurang', 'figma',
            'flutter', 'göteborg', 'gothenburg', 'engineering and management',
            'hackathon', 'programmering', 'framework',
        )
        if any(m in fl for m in cv_markers):
            return False
        instruction_markers = (
            "don't", 'dont', 'only give', 'when i ask', 'when you ask',
            'never give', 'no suggestions', 'remember that', 'keep in mind',
        )
        return any(m in fl for m in instruction_markers)

    @classmethod
    def _split_learned_facts(cls, facts):
        instructions, document_facts = [], []
        for fact in facts or []:
            text = fact_text(fact)
            if cls._is_instruction_fact(fact):
                instructions.append(text)
            else:
                document_facts.append(text)
        return instructions, document_facts

    @classmethod
    def _categorize_document_facts(cls, facts):
        buckets = {key: [] for key in CATEGORY_TOPIC_WORDS if key != 'instructions'}
        buckets['other'] = []
        for fact in facts or []:
            fl = fact_text(fact).lower()
            placed = False
            for category, keywords in CATEGORY_TOPIC_WORDS.items():
                if category == 'instructions':
                    continue
                if any(k in fl for k in keywords):
                    buckets[category].append(fact)
                    placed = True
                    break
            if not placed:
                buckets['other'].append(fact)
        return buckets

    def detect_owner_detail_category(self, text):
        text_lower = text.lower()
        for category, phrases in OWNER_CATEGORY_QUERIES.items():
            if any(p in text_lower for p in phrases):
                return category
        has_deeper = any(t in text_lower for t in DEEPER_DETAIL_TRIGGERS)
        if has_deeper:
            for category, keywords in CATEGORY_TOPIC_WORDS.items():
                if any(k in text_lower for k in keywords):
                    return category
        return None

    def detect_guest_omar_category(self, text):
        text_lower = text.lower()
        if 'omar' not in text_lower:
            return None
        has_deeper = any(t in text_lower for t in DEEPER_DETAIL_TRIGGERS)
        for category in ('projects', 'education', 'skills', 'work', 'languages'):
            if any(k in text_lower for k in CATEGORY_TOPIC_WORDS[category]):
                if has_deeper or category in text_lower:
                    return category
        return None

    @staticmethod
    def _category_labels(language='en'):
        if language == 'sv':
            return {
                'education': 'utbildning',
                'skills': 'skills',
                'projects': 'projekt',
                'work': 'jobb/arbetslivserfarenhet',
                'languages': 'språk',
                'other': 'övrigt',
            }
        return {
            'education': 'education',
            'skills': 'skills',
            'projects': 'projects',
            'work': 'work experience',
            'languages': 'languages',
            'other': 'other details',
        }

    def _format_category_overview(self, document_facts, language='en'):
        if not document_facts:
            return ''
        buckets = self._categorize_document_facts(document_facts)
        labels = self._category_labels(language)
        parts = []
        for key in ('education', 'skills', 'projects', 'work', 'languages', 'other'):
            if buckets.get(key):
                parts.append(f"{labels[key]} ({len(buckets[key])})")
        if not parts:
            return ''
        joined = ', '.join(parts)
        if language == 'sv':
            return (
                f"Från ditt CV har jag sparat {len(document_facts)} saker om dig  -  "
                f"främst {joined}."
            )
        return (
            f"From your CV I've saved {len(document_facts)} things about you  -  "
            f"mainly {joined}."
        )

    def _format_owner_category_detail(self, category, learned_facts, language='en', limit=4):
        instructions, document_facts = self._split_learned_facts(learned_facts)
        labels = self._category_labels(language)

        if category == 'instructions':
            if not instructions:
                if language == 'sv':
                    return 'Du har inte gett mig några särskilda instruktioner ännu bro.'
                return "You haven't given me any special instructions yet bro."
            lines = [self._to_second_person(f) for f in instructions[:limit]]
            body = ' '.join(lines)
            extra = len(instructions) - limit
            if language == 'sv':
                tail = f' Jag har {len(instructions)} instruktioner totalt.' if extra > 0 else ''
                return f"Dina instruktioner till mig: {body}.{tail} Vill du ändra något?"
            tail = f' I have {len(instructions)} instructions total.' if extra > 0 else ''
            return f"Your instructions to me: {body}.{tail} Want to change any of them?"

        buckets = self._categorize_document_facts(document_facts)
        facts = buckets.get(category) or buckets.get('other', [])
        if not facts:
            if language == 'sv':
                return f"Jag har inget sparat om {labels.get(category, category)} ännu bro."
            return f"I don't have anything saved about your {labels.get(category, category)} yet bro."

        lines = [self._to_second_person(f.rstrip('.')) for f in facts[:limit]]
        body = '. '.join(lines) + '.'
        remaining = len(facts) - limit
        if language == 'sv':
            extra = f' Jag har {remaining} till om {labels.get(category, category)}.' if remaining > 0 else ''
            return f"Okej bro  -  om din {labels.get(category, category)}: {body}{extra} Vill du ha ännu mer?"
        extra = f' I have {remaining} more on your {labels.get(category, category)}.' if remaining > 0 else ''
        return f"Sure bro  -  about your {labels.get(category, category)}: {body}{extra} Want even more?"

    def _format_guest_category_detail(self, category, learned_facts, guest_name, language='en', limit=3):
        _, document_facts = self._split_learned_facts(learned_facts)
        buckets = self._categorize_document_facts(document_facts)
        facts = buckets.get(category) or []
        guest = guest_name or 'there'
        labels = self._category_labels(language)

        if not facts:
            if language == 'sv':
                return f"Jag har inte mycket sparat om Omars {labels.get(category, category)} ännu, {guest}."
            return f"I don't have much saved about Omar's {labels.get(category, category)} yet, {guest}."

        lines = [f.rstrip('.') for f in facts[:limit]]
        body = '. '.join(lines) + '.'
        remaining = len(facts) - limit
        if language == 'sv':
            extra = f' Det finns {remaining} till.' if remaining > 0 else ''
            return (
                f"Om Omars {labels.get(category, category)}, {guest}: {body}{extra} "
                f"Vill du veta mer om något annat?"
            )
        extra = f' There are {remaining} more details.' if remaining > 0 else ''
        return (
            f"About Omar's {labels.get(category, category)}, {guest}: {body}{extra} "
            f"Want to know about something else?"
        )

    def format_omar_profile_summary(self, language='en', learned_facts=None):
        """Short overview  -  facts about Omar vs instructions he gave Tild."""
        profile = self.omar_profile
        facts = learned_facts or self.learned_omar_facts
        instructions, document_facts = self._split_learned_facts(facts)

        if language == 'sv':
            intro = (
                f"Du är {profile.get('full_name', OWNER_FULL_NAME)}, min skapare och ägare  -  "
                f"du byggde mig från grunden. Du studerar "
                f"{profile.get('degree', 'Software Engineering')} vid "
                f"{profile.get('university', 'University of Gothenburg')} och bor i "
                f"{profile.get('location', 'Gothenburg, Sweden')}."
            )
            offer = DETAIL_OFFER_SV
        else:
            intro = (
                f"You're {profile.get('full_name', OWNER_FULL_NAME)}, my creator and owner  -  "
                f"you built me from scratch. You study "
                f"{profile.get('degree', 'Software Engineering')} at "
                f"{profile.get('university', 'University of Gothenburg')} and you're based in "
                f"{profile.get('location', 'Gothenburg, Sweden')}."
            )
            offer = DETAIL_OFFER_EN

        parts = [intro]
        cv_overview = self._format_category_overview(document_facts, language)
        if cv_overview:
            parts.append(cv_overview)

        if instructions:
            count = len(instructions)
            preview = self._to_second_person(instructions[0])
            if len(preview) > 90:
                preview = preview[:87] + '...'
            if language == 'sv':
                label = 'Dina instruktioner till mig' if count == 1 else f'Dina {count} instruktioner till mig'
                parts.append(f"{label} (separat från fakta om dig): {preview}.")
            else:
                label = 'Your instruction to me' if count == 1 else f'Your {count} instructions to me'
                parts.append(f"{label} (separate from facts about you): {preview}.")

        parts.append(offer)
        return ' '.join(parts)

    def format_omar_recall_for_owner(self, learned_facts=None, language='en'):
        """Only what Omar explicitly asked Tild to remember  -  not CV bio facts."""
        facts = learned_facts or self.learned_omar_facts
        instructions, _ = self._split_learned_facts(facts)

        if not instructions:
            if language == 'sv':
                return 'Du har inte bett mig komma ihåg några instruktioner ännu bro.'
            return "You haven't asked me to remember any instructions yet bro."

        if len(instructions) == 1:
            item = self._to_second_person(instructions[0])
            if language == 'sv':
                return f'Du bad mig komma ihåg detta bro: {item}. Vill du ändra det?'
            return f'You asked me to remember this bro: {item}. Want to change it?'

        preview = '; '.join(self._to_second_person(f) for f in instructions[:2])
        if language == 'sv':
            return (
                f'Du har gett mig {len(instructions)} instruktioner bro  -  t.ex. {preview}. '
                f'Säg "mer om mina instruktioner" om du vill se allt.'
            )
        return (
            f"You've given me {len(instructions)} instructions bro  -  e.g. {preview}. "
            f'Say "more about my instructions" if you want the full list.'
        )

    def answer_omar_question(self, text, language='en', learned_facts=None):
        text_lower = text.lower()
        facts = learned_facts or self.learned_omar_facts

        category = self.detect_owner_detail_category(text)
        if category:
            return self._format_owner_category_detail(category, facts, language)

        if any(trigger in text_lower for trigger in OWNER_SELF_TRIGGERS):
            return self.format_omar_profile_summary(language, facts)

        topics = self.omar_profile.get('topics', {})

        keyword_map = [
            (['university', 'universitet', 'school', 'college', 'study', 'studera'], 'university'),
            (['degree', 'program', 'software engineering', 'examen'], 'degree'),
            (['project', 'built', 'build', 'create', 'projekt', 'tild'], 'tild'),
            (['location', 'live', 'from', 'gothenburg', 'bor', 'stad'], 'location'),
            (['name', 'full name', 'heter', 'darwish'], 'name'),
            (['skill', 'passion', 'smart', 'talented', 'engineer'], 'skills'),
            (['github', 'repo', 'code'], 'github'),
            (['creator', 'owner', 'made you', 'built you'], 'creator'),
        ]

        for keywords, topic_key in keyword_map:
            if any(k in text_lower for k in keywords) and topic_key in topics:
                return self._to_second_person(topics[topic_key])

        if any(k in text_lower for k in ['milestone', 'achieve', 'accomplish']):
            milestones = self.omar_profile.get('milestones', [])
            if milestones:
                return 'Your milestones include: ' + '; '.join(milestones[:3])

        if any(k in text_lower for k in ['project', 'projekt']):
            projects = self.omar_profile.get('projects', [])
            if projects:
                return (
                    'Your projects include: ' + '; '.join(projects[:3])
                    + '. Want more on your projects?'
                )

        for fact in facts:
            ft = fact_text(fact)
            fact_words = set(re.findall(r'\w+', ft.lower()))
            query_words = set(re.findall(r'\w+', text_lower))
            if len(fact_words.intersection(query_words)) >= 2:
                return self._to_second_person(ft)

        return None

    def answer_omar_for_guest(self, text, language='en', guest_name=None):
        """When someone other than Omar asks who Omar is  -  brief, offer more."""
        guest = guest_name or 'there'
        profile = self.omar_profile
        category = self.detect_guest_omar_category(text)
        if category:
            return self._format_guest_category_detail(
                category, self.learned_omar_facts, guest, language
            )

        if language == 'sv':
            return (
                f"Omar Darwish är min skapare och ägare  -  han byggde mig från grunden. "
                f"Han studerar software engineering i Göteborg. "
                f"{GUEST_DETAIL_OFFER_SV} ({guest})"
            )
        if language == 'ar':
            return (
                f"Omar Darwish هو من أنشأني ومالكي. بنى Tild من الصفر. "
                f"سألتُ إن كنت Omar لأنه الوحيد الذي يمكنه تأكيد أنه مالكي. أنت {guest}."
            )
        return (
            f"Omar Darwish is my creator and owner  -  he built me from scratch. "
            f"He's a software engineering student in Gothenburg, Sweden. "
            f"{GUEST_DETAIL_OFFER_EN}"
        )

    def answer_tild_self_question(self, text, language='en', memory=None):
        text_lower = text.lower()
        identity = self.tild_identity
        creator = identity.get('creator', OWNER_FULL_NAME)
        is_owner = memory is not None and memory.is_owner()

        if any(k in text_lower for k in ['name', 'heter', 'called']):
            if is_owner:
                if language == 'sv':
                    return 'Jag heter Tild. Du gav mig namnet när du skapade mig.'
                if language == 'ar':
                    return 'اسمي Tild. أنت Omar أعطيتني الاسم عندما أنشأتني.'
                return 'My name is Tild. You gave me that name when you created me.'
            if language == 'sv':
                return f'Jag heter Tild. {creator} gav mig namnet när han skapade mig.'
            if language == 'ar':
                return f'اسمي Tild. {creator} أعطاني الاسم عندما أنشأني.'
            return f"My name is Tild. {creator} gave me this name when he created me."

        if any(k in text_lower for k in ['who built', 'who made', 'who created', 'creator', 'skapade', 'byggde']):
            if is_owner:
                if language == 'sv':
                    return (
                        'Du byggde mig från grunden med Python och PyTorch. '
                        'Du är min skapare och ägare.'
                    )
                if language == 'ar':
                    return (
                        'أنت بنيتني من الصفر باستخدام Python و PyTorch. '
                        'أنت من أنشأني ومالكي.'
                    )
                return (
                    'You built me completely from scratch using Python and PyTorch. '
                    'You are my creator and owner.'
                )
            if language == 'sv':
                return (
                    f'{creator} byggde mig från grunden med Python och PyTorch. '
                    f'Han är min skapare och ägare.'
                )
            if language == 'ar':
                return (
                    f'{creator} بناني من الصفر باستخدام Python و PyTorch. '
                    f'هو من أنشأني ومالكي.'
                )
            return (
                f'{creator} built me completely from scratch using Python and PyTorch. '
                f'He is my creator and owner.'
            )

        if any(k in text_lower for k in ['what are you', 'who are you', 'vad är du', 'vem är du']):
            if self.is_tild_activity_question(text):
                return None
            if is_owner:
                if language == 'sv':
                    return (
                        'Jag är Tild, din personliga AI. Du byggde mig från grunden. '
                        'Jag pratar svenska, engelska och arabiska.'
                    )
                if language == 'ar':
                    return (
                        'أنا Tild، مساعدك الشخصي. أنت بنيتني من الصفر. '
                        'أتحدث السويدية والإنجليزية والعربية.'
                    )
                return (
                    'I am Tild, your personal AI assistant. You built me from scratch. '
                    'I speak English, Swedish, and Arabic.'
                )
            if language == 'sv':
                return (
                    f'Jag är Tild, en personlig AI-assistent som {creator} byggde från grunden. '
                    f'Jag pratar svenska, engelska och arabiska.'
                )
            if language == 'ar':
                return (
                    f'أنا Tild، مساعد ذكاء اصطناعي شخصي. {creator} بناني من الصفر. '
                    f'أتحدث السويدية والإنجليزية والعربية.'
                )
            return (
                f'I am Tild, a personal AI assistant built from scratch by {creator}. '
                f'I speak English, Swedish, and Arabic.'
            )

        if any(k in text_lower for k in ['what can you do', 'capabilities', 'vad kan du']):
            if language == 'sv':
                return (
                    'Jag kan chatta på svenska, engelska och arabiska, minnas personer och samtal, '
                    'lära av rättelser, söka Wikipedia och väder, analysera text och hjälpa med '
                    'skrivande, kod, brev med mera.'
                )
            if language == 'ar':
                return (
                    'أستطيع الدردشة بالسويدية والإنجليزية والعربية، تذكر الأشخاص والمحادثات، '
                    'التعلم من التصحيحات، البحث في ويكيبيديا والطقس، وتحليل النصوص والمساعدة في الكتابة والبرمجة.'
                )
            return (
                'I can chat in English, Swedish, and Arabic, remember people and conversations, '
                'learn from corrections, search Wikipedia and weather, analyze text, and help with '
                'writing, code, letters, and more.'
            )

        facts = identity.get('facts', [])
        if facts:
            return facts[0]
        return None

    def answer_tild_activity_question(self, text, language='en', memory=None):
        """Casual 'what are you doing'  -  current session context, not identity."""
        if memory and memory.is_owner():
            if language == 'sv':
                return 'Pratar med dig just nu bro, redo att hjälpa till med vad som helst!'
            if language == 'ar':
                return 'أتحدث معك الآن، مستعد للمساعدة في أي شيء!'
            return 'Just talking with you right now bro, ready to help with whatever you need!'

        name = memory.get_user_name() if memory and memory.is_session_identified() else 'you'
        if language == 'sv':
            return f'Jag pratar med dig just nu, {name}, och är redo att hjälpa till.'
        if language == 'ar':
            return f'أتحدث معك الآن يا {name}، ومستعد للمساعدة.'
        return f'I am here chatting with you, {name}, ready to help with whatever you need.'

    def answer_tild_experience_question(self, text, language='en', memory=None):
        activity = ''
        if memory:
            from datetime import date
            today = date.today().isoformat()
            guests = memory.get_all_guest_users() if hasattr(memory, 'get_all_guest_users') else []
            today_names = [
                u['full_name'] for _, u in guests
                if (u.get('last_seen') or '')[:10] == today
            ]
            if today_names:
                if language == 'sv':
                    activity = f' I minnet interagerade jag idag med: {", ".join(today_names)}.'
                elif language == 'ar':
                    activity = f' في ذاكرتي، تفاعلت اليوم مع: {", ".join(today_names)}.'
                else:
                    activity = f' In my memory, I interacted today with: {", ".join(today_names)}.'

        if language == 'sv':
            return (
                'Jag upplever inte känslor, glädje eller "kul" som en människa  -  jag är en AI-assistent. '
                'Jag bearbetar samtal och sparar information i minnet för att hjälpa användare.'
                + activity
            )
        if language == 'ar':
            return (
                'لا أختبر المشاعر أو المتعة كالبشر  -  أنا مساعد ذكاء اصطناعي. '
                'أعالج المحادثات وأحفظ المعلومات في الذاكرة لمساعدة المستخدمين.'
                + activity
            )
        if memory and memory.is_owner():
            return (
                'I do not experience fun, emotions, or personal feelings the way you do bro  -  I am an AI. '
                'I process conversations and store what happens in memory to help people.'
                + activity
            )
        return (
            'I do not experience fun, emotions, or personal feelings the way humans do. '
            'I am an AI assistant. I process conversations and store information in memory to help users.'
            + activity
        )

    def dont_know_response(self, language='en', about='that'):
        if language == 'sv':
            return f"Det vet jag inte säkert ännu. Jag hittar inte {about} i minnet."
        if language == 'ar':
            return f"لا أعرف ذلك بشكل مؤكد بعد. لا أجد {about} في ذاكرتي."
        return f"I do not know that for certain yet. I do not have {about} stored in my memory."
