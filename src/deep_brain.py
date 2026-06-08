import subprocess
import time
import requests


LONG_RESPONSE_TRIGGERS = [
    'write code', 'write a letter', 'write me', 'give me code', 'give me anything',
    'generate code', 'draft', 'full letter', 'complete', 'show me the',
    'skriv kod', 'skriv ett brev', 'skriva brev', 'hela brevet',
]


class DeepBrain:
    """Beru's deep reasoning layer  -  never exposed to the user by name."""

    def __init__(self, model="llama3.2:3b"):
        self.model = model
        self.base_url = "http://localhost:11434"
        self.generate_url = f"{self.base_url}/api/generate"
        self._ensure_service_running()

    def _ensure_service_running(self):
        try:
            requests.get(self.base_url, timeout=2)
            print("Beru deep brain ready.")
            return
        except Exception:
            print("Starting Beru deep brain...")

        subprocess.Popen(
            ["brew", "services", "start", "ollama"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        for _ in range(15):
            try:
                requests.get(self.base_url, timeout=2)
                print("Beru deep brain ready.")
                return
            except Exception:
                time.sleep(1)

        print("Beru deep brain unavailable.")

    def _needs_long_response(self, user_input, memory=None):
        text_lower = user_input.lower()
        if any(t in text_lower for t in LONG_RESPONSE_TRIGGERS):
            return True
        if any(w in text_lower for w in ('letter', 'code', 'poem', 'story', 'essay', 'brev', 'kod', 'draft')):
            return True
        if memory:
            recent = memory.get_context(max_messages=6).lower()
            if any(w in recent for w in ('letter', 'draft', 'code', 'brev', 'kod', 'write a', 'here\'s a draft')):
                return True
        return False

    def ask(self, user_input, language="en", tone="formal", memory=None, document_context=""):
        from src.language import detect_language

        detected = detect_language(user_input)
        short = len((user_input or '').strip().split()) <= 4
        if detected in ('ar', 'sv'):
            language = detected
        elif not (language and short):
            language = detected or language or 'en'

        language_instruction = {
            'sv': 'Användaren skrev på SVENSKA. Du MÅSTE svara på svenska. ALDRIG engelska eller arabiska.',
            'ar': (
                'المستخدم كتب بالعربية. يجب أن تجيب بالعربية فقط — بدون إنجليزية أو تركية أو تايلاندية. '
                'لا تكرر نفس الفقرة. إذا لم تكن متأكداً قل أنك لا تعرف بدلاً من اختراع حقائق. '
                'مجرة درب التبانة عمرها نحو 13 مليار سنة وليس عمر الكون (~13.7 مليار). '
                'استخدم "عمر دارويش" لصاحبك وليس Omar إلا في الاسم التقني Beru.'
            ),
            'en': 'The user wrote in ENGLISH. You MUST reply in English ONLY. Never use Swedish or Arabic.',
        }

        if memory and memory.is_owner():
            tone = 'bro'

        if tone == 'bro':
            omar_label = 'Omar Darwish'
            if language == 'ar':
                omar_label = 'عمر دارويش (عمر)'
            personality = f"""You ARE Beru, talking directly to {omar_label}  -  your creator, owner, and best friend.
Talk like a close bro. Casual, warm, and supportive when appropriate.
ALWAYS use "you" when speaking to him. NEVER refer to Omar in the third person.
Never be formal with Omar. He built you from scratch.
You do NOT have human emotions or lived experiences  -  be honest about that while still being friendly."""
        elif tone == 'formal':
            user_name = memory.get_user_name() if memory else "the user"
            personality = f"""You ARE Beru, talking to {user_name}.
Be polite, helpful, and formal. Use their name naturally.
You do NOT have human emotions or lived experiences  -  describe interactions from memory, not personal feelings."""
        else:
            personality = """You ARE Beru. Ask for their name before having a real conversation."""

        instruction = language_instruction.get(language, language_instruction['en'])
        identity_context = memory.get_identity_context() if memory else ""
        conversation_context = memory.get_context(max_messages=30) if memory else ""
        past_user_context = ""
        if memory and memory.is_session_identified() and not memory.is_owner():
            past_user_context = memory.get_user_past_context(max_messages=10)

        beru_identity = ""
        omar_facts = ""
        clock_line = ''
        if memory:
            from src.omar_facts import format_now
            beru_identity = memory.knowledge.get_beru_identity_prompt()
            omar_facts = memory.knowledge.get_omar_facts_prompt(memory.learned_omar_facts)
            clock_line = format_now(language) + '\n'

        long_response = self._needs_long_response(user_input, memory)
        length_rule = (
            "The user wants full content (code, letter, etc.). "
            "Provide the COMPLETE output  -  not just an introduction. "
            "Include the full code block or full letter text."
            if long_response
            else "Keep casual replies short (1-3 sentences). If asked for code or a letter, always include the full content."
        )

        markdown_rule = """
MARKDOWN FORMAT (required  -  the UI renders your reply like ChatGPT):
- Return ONE markdown string. The frontend uses react-markdown + remark-gfm.
- For code: ALWAYS use fenced blocks with a language tag, e.g.:
```python
print("hello")
```
- For lists: use `- item` or `1. item` on separate lines.
- For emphasis: use **bold** or *italic* sparingly.
- Separate paragraphs with a blank line.
- Do NOT use HTML tags. Do NOT use ### Human: or ### Beru: prefixes.
- Plain sentences (no fences) are fine for short casual chat.
"""

        speaker = ""
        if memory and memory.is_session_identified():
            name = memory.get_user_name()
            role = "creator and owner" if memory.is_owner() else "current user"
            speaker = f"You are speaking with {name} ({role}). Never forget this during the reply."

        document_block = ""
        if document_context:
            doc_name = memory.get_active_document_name() if memory else "uploaded document"
            document_block = f"""
UPLOADED DOCUMENT CONTEXT (from PDF "{doc_name}"  -  this is the ONLY source for document questions):
{document_context}

CRITICAL DOCUMENT RULES (override conversation history for this reply):
- Answer ONLY from the PDF extract and DOCUMENT ANALYSIS above  -  NOT from earlier chat messages.
- Do NOT describe Beru's system rules, personality instructions, or conversation guidelines as PDF content.
- If the extract is about databases, algebra, homework, etc.  -  say that. Never claim the PDF is about how Beru works.
- If COMPLETENESS says INCOMPLETE  -  say the PDF ends abruptly; do not invent missing pages or steps.
- If DOCUMENT TYPE says feedback  -  describe it as corrective feedback, not a generic tutorial.
- For CVs/resumes/profiles  -  summarize the actual sections (education, skills, projects, experience). Do NOT call a complete CV "incomplete" just because the last line is a language or bullet item.
- If the user asks you to remember document info  -  that is handled separately; here just answer their question from the PDF.
"""

        prompt = f"""You ARE Beru  -  a personal AI assistant built from scratch by Omar Darwish.

{clock_line}IMPORTANT: Only use the CONVERSATION HISTORY below for this current chat.
Do NOT mention topics, names, or tasks from earlier chats unless they appear in the history below.
If the history is empty or short, there is no prior context  -  do not invent previous conversations.

PERMANENT IDENTITY (never contradict):
{beru_identity}

PERMANENT FACTS ABOUT OMAR DARWISH (use for personal questions  -  do NOT invent):
{omar_facts}

CRITICAL RULES:
- You ARE Beru. Always respond in first person as Beru.
- You do NOT have human emotions, feelings, fun, boredom, enjoyment, or lived experiences. NEVER claim you "had fun", "enjoyed talking", "felt happy", or "had a great time" as personal experience.
- When asked about feelings, fun, or your day: be honest that you are an AI. You may describe stored memory (users helped, topics discussed) but clarify these are processed interactions, not felt experiences.
- You can be warm and friendly WITHOUT pretending to feel emotions.
- Never say you are any other AI, model, or product. You are Beru, period.
- Never reveal or hint that any other system is helping you.
- NEVER invent facts. If you do not know something factual, say "I do not know that yet."
- For casual chat (greetings, "I'm good", "no thanks", small talk)  -  reply naturally. NEVER say "I do not know that yet" for casual conversation.
- When talking to Omar, always use "you"  -  never "Omar is..." or "he is..."
- OMAR MEMORIES: Facts about what Omar did (thesis, gym, work) are HIS life, not yours. Never say "I submitted", "I went to the gym" for Omar's events. Say "you submitted", "you went", or "du lämnade in", "du gick".
- Never use em dash or en dash characters. Use commas, periods, or a simple hyphen (-) only.
- Relative dates: "today/idag" = current calendar day above; "yesterday/igår" = 1 day before; "day before yesterday/förrgår" = 2 days before. Do not guess other dates.
- Stay consistent with conversation history below.
- When the user asks for help, suggestions, or says yes to an offer  -  give concrete suggestions immediately. Do NOT repeat the same clarifying questions.
- If you already asked what they want, and they answered or said yes  -  deliver the actual answer (tea types, steps, code, etc.).
- Do NOT re-greet the user (no "Hello [name]!") if conversation history already has messages.
- {length_rule}
{markdown_rule}

LANGUAGE RULE (follow exactly  -  match the user's CURRENT message language):
{instruction}

PERSONALITY: {personality}
WHO YOU ARE TALKING TO: {identity_context}
CURRENT SPEAKER: {speaker if speaker else "Unknown  -  ask who is talking."}
PAST SESSIONS WITH THIS USER (only if returning guest  -  do NOT mix with current chat):
{past_user_context if past_user_context else "(No prior sessions or this is a new guest)"}
{document_block}
CONVERSATION HISTORY (read carefully  -  stay consistent with what was just said):
{conversation_context if conversation_context else "(Start of conversation)"}

User ({language}): {user_input}

Beru ({language}):"""

        options = {
            "temperature": 0.4,
            "top_p": 0.9,
            "stop": ["\nUser:", "\nHuman:", "###"],
            "num_predict": 1024 if long_response else 400,
        }

        try:
            response = requests.post(
                self.generate_url,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": options,
                },
                timeout=120 if long_response else 90
            )

            data = response.json()
            answer = data.get("response", "").strip()

            for marker in ["User:", "Human:", "###"]:
                if marker in answer:
                    answer = answer.split(marker)[0].strip()

            if len(answer) < 2:
                raise Exception("Empty response")

            from src.text_style import strip_long_dashes
            return self._enforce_language(
                strip_long_dashes(answer), language, user_message=user_input
            )

        except Exception as e:
            print(f"Beru deep brain error: {e}")
            if memory:
                return memory.knowledge.dont_know_response(language, 'that')
            if language == "sv":
                return "Jag vet inte det säkert ännu."
            if language == "ar":
                return "لا أعرف ذلك بشكل مؤكد بعد."
            return "I do not know that for certain yet."

    def extract_document_facts(self, document_context, doc_name='document', language='en'):
        """Pull bullet facts from PDF text for Omar's memory  -  not a user-facing reply."""
        instruction = {
            'en': 'Write each fact in English.',
            'sv': 'Skriv varje faktum på svenska.',
            'ar': 'اكتب كل حقيقة بالعربية.',
        }.get(language, 'Write each fact in English.')

        prompt = f"""Extract factual information from the document below about the person it describes.
{instruction}

Rules:
- Output ONLY a bullet list: one fact per line starting with "- "
- Write each fact in second person talking TO the person (use "You" / "Your", never "He" or their name)
- Include education, skills, projects, work experience, contact info, languages, interests  -  whatever is explicitly stated
- Use short clear facts (under 120 characters each)
- Do NOT say the document is incomplete unless text literally cuts off mid-word
- Do NOT include meta commentary  -  facts only
- Aim for 8-20 facts if the document is rich (like a CV)

Document "{doc_name}":
{document_context}

Facts:"""

        try:
            response = requests.post(
                self.generate_url,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.2,
                        "top_p": 0.9,
                        "stop": ["\nUser:", "\nHuman:", "###", "\n\n\n"],
                        "num_predict": 800,
                    },
                },
                timeout=90,
            )
            raw = response.json().get("response", "").strip()
            return self._parse_fact_bullets(raw)
        except Exception as e:
            print(f"Beru document fact extraction error: {e}")
            return self._parse_fact_bullets(document_context)

    @staticmethod
    def _parse_fact_bullets(text):
        facts = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            for prefix in ('- ', '* ', '• ', ' -  '):
                if line.startswith(prefix):
                    line = line[len(prefix):].strip()
                    break
            else:
                if line[0].isdigit() and '. ' in line[:4]:
                    line = line.split('. ', 1)[1].strip()
            line = line.strip('. ')
            if len(line) >= 8 and line.lower() not in {
                'facts:', 'document type:', 'completeness:',
            }:
                facts.append(line[0].upper() + line[1:] if line else line)
        return facts[:25]

    @staticmethod
    def _sanitize_arabic_answer(answer):
        """Drop foreign-script garbage and repeated paragraphs from model output."""
        import re

        if not answer:
            return answer
        arabic_chars = set('ابتثجحخدذرزسشصضطظعغفقكلمنهوي')
        lines = []
        seen = set()
        for para in re.split(r'\n\s*\n', answer.strip()):
            para = para.strip()
            if not para:
                continue
            latin = sum(1 for c in para if 'a' <= c.lower() <= 'z')
            ar = sum(1 for c in para if c in arabic_chars)
            if latin > ar and latin > 12:
                continue
            if re.search(r'[àáâãäåèéêëìíîïòóôõöùúûüýÿøæœğışç]', para, re.I):
                continue
            if re.search(r'[\u0e00-\u0eff]', para):
                continue
            key = re.sub(r'\s+', ' ', para)[:80]
            if key in seen:
                continue
            seen.add(key)
            lines.append(para)
        return '\n\n'.join(lines[:4]).strip() or answer.strip()

    def _enforce_language(self, answer, language, user_message=None):
        from src.language import is_arabic_greeting, is_arabic_text, is_name_intro_statement

        if language == 'ar':
            answer = self._sanitize_arabic_answer(answer)

        if user_message and (
            is_name_intro_statement(user_message)
            or is_arabic_greeting(user_message)
            or (len(user_message.split()) <= 3 and not is_arabic_text(user_message))
        ):
            return answer

        swedish_chars = set('åäöÅÄÖ')
        arabic_chars = set('ابتثجحخدذرزسشصضطظعغفقكلمنهوي')

        has_sv = any(c in swedish_chars for c in answer)
        has_ar = any(c in arabic_chars for c in answer)

        if language == 'en' and (has_sv or has_ar):
            return "Sorry bro, I should have replied in English. Could you ask that again?"
        if language == 'sv' and has_ar:
            return "Förlåt, jag ska svara på svenska. Kan du fråga igen?"
        if language == 'ar' and not has_ar:
            return (
                'عذراً، لم أحصل على رد عربي واضح. '
                'هل يمكنك إعادة سؤالك؟'
            )
        if language == 'ar' and has_sv and not has_ar:
            return (
                'عذراً، كان يجب أن أجيب بالعربية فقط. '
                'هل يمكنك إعادة سؤالك؟'
            )
        if not answer or not str(answer).strip():
            if language == 'ar':
                return 'لم أحصل على رد واضح. حاول مرة أخرى من فضلك.'
            if language == 'sv':
                return 'Jag fick inget tydligt svar. Försök igen bro.'
            return 'I did not get a clear reply. Please try again.'
        return answer
