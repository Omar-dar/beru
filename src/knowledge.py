import json
import os
import re

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
    'vad vet du om mig', 'berätta om mig',
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

SEARCH_BLOCK_TRIGGERS = OMAR_PERSONAL_TRIGGERS + TILD_SELF_TRIGGERS + [
    'do you know me', 'do you know who i am', 'what is my name', 'who am i',
]


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
        return any(trigger in text_lower for trigger in TILD_SELF_TRIGGERS)

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
        for learned in (learned_facts or self.learned_omar_facts):
            lines.append(f"- Learned fact: {learned}")
        return '\n'.join(lines)

    def answer_omar_question(self, text, language='en', learned_facts=None):
        text_lower = text.lower()
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
                return topics[topic_key]

        if any(k in text_lower for k in ['milestone', 'achieve', 'accomplish']):
            milestones = self.omar_profile.get('milestones', [])
            if milestones:
                return 'Omar Darwish milestones: ' + '; '.join(milestones[:3])

        if any(k in text_lower for k in ['project', 'projekt']):
            projects = self.omar_profile.get('projects', [])
            if projects:
                return 'Omar Darwish projects include: ' + '; '.join(projects[:3])

        for fact in (learned_facts or self.learned_omar_facts):
            fact_words = set(re.findall(r'\w+', fact.lower()))
            query_words = set(re.findall(r'\w+', text_lower))
            if len(fact_words.intersection(query_words)) >= 2:
                return fact

        return None

    def answer_omar_for_guest(self, text, language='en', guest_name=None):
        """When someone other than Omar asks who Omar is."""
        guest = guest_name or 'there'
        profile = self.omar_profile
        creator_line = profile.get('topics', {}).get(
            'creator',
            'Omar Darwish built Tild completely from scratch. He is Tild\'s creator and owner.',
        )
        if language == 'sv':
            return (
                f"Omar Darwish är min skapare och ägare. Han byggde mig från grunden med Python och PyTorch. "
                f"Han studerar software engineering vid Göteborgs universitet. "
                f"Jag frågade om du var Omar eftersom han är den enda som kan verifiera sig som min ägare. "
                f"Du sa att du är {guest}, så jag pratar med dig nu."
            )
        if language == 'ar':
            return (
                f"Omar Darwish هو من أنشأني ومالكي. بنى Tild من الصفر باستخدام Python و PyTorch. "
                f"سألتُ إن كنت Omar لأنه الوحيد الذي يمكنه تأكيد أنه مالكي. أنت {guest}."
            )
        return (
            f"Omar Darwish is my creator and owner. {creator_line} "
            f"He is a software engineering student at the University of Gothenburg in Sweden. "
            f"I asked if you were Omar because he is the only person who can verify as my owner with a password. "
            f"You told me you are {guest}, so I am talking to you now — not Omar."
        )

    def answer_tild_self_question(self, text, language='en'):
        text_lower = text.lower()
        identity = self.tild_identity
        creator = identity.get('creator', OWNER_FULL_NAME)

        if any(k in text_lower for k in ['name', 'heter', 'called']):
            return f"My name is Tild. {creator} gave me this name when he created me."
        if any(k in text_lower for k in ['who built', 'who made', 'who created', 'creator', 'skapade', 'byggde']):
            return f"{creator} built me completely from scratch using Python and PyTorch. He is my creator and owner."
        if any(k in text_lower for k in ['what are you', 'who are you', 'vad är du', 'vem är du']):
            return (
                f"I am Tild, a personal AI assistant built from scratch by {creator}. "
                f"I speak English, Swedish, and Arabic."
            )
        if any(k in text_lower for k in ['what can you do', 'capabilities', 'vad kan du']):
            return (
                "I can chat in English, Swedish, and Arabic, remember people and conversations, "
                "learn from corrections, search Wikipedia and weather, analyze text, and help with "
                "writing — code, letters, and more."
            )

        facts = identity.get('facts', [])
        if facts:
            return facts[0]
        return None

    def answer_tild_experience_question(self, text, language='en', memory=None):
        """Honest answer — no claimed human feelings; optional memory facts."""
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
                'Jag upplever inte känslor, glädje eller "kul" som en människa — jag är en AI-assistent. '
                'Jag bearbetar samtal och sparar information i minnet för att hjälpa användare.'
                + activity
            )
        if language == 'ar':
            return (
                'لا أختبر المشاعر أو المتعة كالبشر — أنا مساعد ذكاء اصطناعي. '
                'أعالج المحادثات وأحفظ المعلومات في الذاكرة لمساعدة المستخدمين.'
                + activity
            )
        if memory and memory.is_owner():
            return (
                'I do not experience fun, emotions, or personal feelings the way you do bro — I am an AI. '
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
