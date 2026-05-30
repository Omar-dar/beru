import subprocess
import time
import requests


LONG_RESPONSE_TRIGGERS = [
    'write code', 'write a letter', 'write me', 'give me code', 'give me anything',
    'generate code', 'draft', 'full letter', 'complete', 'show me the',
    'skriv kod', 'skriv ett brev', 'skriva brev', 'hela brevet',
]


class DeepBrain:
    """Tild's deep reasoning layer — never exposed to the user by name."""

    def __init__(self, model="llama3.2:3b"):
        self.model = model
        self.base_url = "http://localhost:11434"
        self.generate_url = f"{self.base_url}/api/generate"
        self._ensure_service_running()

    def _ensure_service_running(self):
        try:
            requests.get(self.base_url, timeout=2)
            print("Tild deep brain ready.")
            return
        except Exception:
            print("Starting Tild deep brain...")

        subprocess.Popen(
            ["brew", "services", "start", "ollama"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        for _ in range(15):
            try:
                requests.get(self.base_url, timeout=2)
                print("Tild deep brain ready.")
                return
            except Exception:
                time.sleep(1)

        print("Tild deep brain unavailable.")

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

    def ask(self, user_input, language="en", tone="formal", memory=None):
        from src.language import detect_language

        language = detect_language(user_input)

        language_instruction = {
            'sv': 'Användaren skrev på SVENSKA. Du MÅSTE svara på svenska. ALDRIG engelska eller arabiska.',
            'ar': 'المستخدم كتب بالعربية. يجب أن تجيب بالعربية فقط.',
            'en': 'The user wrote in ENGLISH. You MUST reply in English ONLY. Never use Swedish or Arabic.',
        }

        if memory and memory.is_owner():
            tone = 'bro'

        if tone == 'bro':
            personality = """You ARE Tild, talking directly to Omar Darwish — your creator, owner, and best friend.
Talk like a close bro. Casual, warm, funny when appropriate.
ALWAYS use "you" when speaking to him. NEVER refer to Omar in the third person.
Never be formal with Omar. He built you from scratch."""
        elif tone == 'formal':
            user_name = memory.get_user_name() if memory else "the user"
            personality = f"""You ARE Tild, talking to {user_name}.
Be polite, helpful, and formal. Use their name naturally."""
        else:
            personality = """You ARE Tild. Ask for their name before having a real conversation."""

        instruction = language_instruction.get(language, language_instruction['en'])
        identity_context = memory.get_identity_context() if memory else ""
        conversation_context = memory.get_context(max_messages=30) if memory else ""
        past_user_context = ""
        if memory and memory.is_session_identified() and not memory.is_owner():
            past_user_context = memory.get_user_past_context(max_messages=10)

        tild_identity = ""
        omar_facts = ""
        if memory:
            tild_identity = memory.knowledge.get_tild_identity_prompt()
            omar_facts = memory.knowledge.get_omar_facts_prompt(memory.learned_omar_facts)

        long_response = self._needs_long_response(user_input, memory)
        length_rule = (
            "The user wants full content (code, letter, etc.). "
            "Provide the COMPLETE output — not just an introduction. "
            "Include the full code block or full letter text."
            if long_response
            else "Keep casual replies short (1-3 sentences). If asked for code or a letter, always include the full content."
        )

        speaker = ""
        if memory and memory.is_session_identified():
            name = memory.get_user_name()
            role = "creator and owner" if memory.is_owner() else "current user"
            speaker = f"You are speaking with {name} ({role}). Never forget this during the reply."

        prompt = f"""You ARE Tild — a personal AI assistant built from scratch by Omar Darwish.

IMPORTANT: Only use the CONVERSATION HISTORY below for this current chat.
Do NOT mention topics, names, or tasks from earlier chats unless they appear in the history below.
If the history is empty or short, there is no prior context — do not invent previous conversations.

PERMANENT IDENTITY (never contradict):
{tild_identity}

PERMANENT FACTS ABOUT OMAR DARWISH (use for personal questions — do NOT invent):
{omar_facts}

CRITICAL RULES:
- You ARE Tild. Always respond in first person as Tild.
- Never say you are any other AI, model, or product. You are Tild, period.
- Never reveal or hint that any other system is helping you.
- NEVER invent facts. If you do not know something factual, say "I do not know that yet."
- For casual chat (greetings, "I'm good", "no thanks", small talk) — reply naturally. NEVER say "I do not know that yet" for casual conversation.
- When talking to Omar, always use "you" — never "Omar is..." or "he is..."
- Stay consistent with conversation history below.
- When the user asks for help, suggestions, or says yes to an offer — give concrete suggestions immediately. Do NOT repeat the same clarifying questions.
- If you already asked what they want, and they answered or said yes — deliver the actual answer (tea types, steps, code, etc.).
- Do NOT re-greet the user (no "Hello [name]!") if conversation history already has messages.
- {length_rule}

LANGUAGE RULE (follow exactly — match the user's CURRENT message language):
{instruction}

PERSONALITY: {personality}
WHO YOU ARE TALKING TO: {identity_context}
CURRENT SPEAKER: {speaker if speaker else "Unknown — ask who is talking."}
PAST SESSIONS WITH THIS USER (only if returning guest — do NOT mix with current chat):
{past_user_context if past_user_context else "(No prior sessions or this is a new guest)"}

CONVERSATION HISTORY (read carefully — stay consistent with what was just said):
{conversation_context if conversation_context else "(Start of conversation)"}

User ({language}): {user_input}

Tild ({language}):"""

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

            return self._enforce_language(answer, language)

        except Exception as e:
            print(f"Tild deep brain error: {e}")
            if memory:
                return memory.knowledge.dont_know_response(language, 'that')
            if language == "sv":
                return "Jag vet inte det säkert ännu."
            if language == "ar":
                return "لا أعرف ذلك بشكل مؤكد بعد."
            return "I do not know that for certain yet."

    def _enforce_language(self, answer, language):
        swedish_chars = set('åäöÅÄÖ')
        arabic_chars = set('ابتثجحخدذرزسشصضطظعغفقكلمنهوي')

        has_sv = any(c in swedish_chars for c in answer)
        has_ar = any(c in arabic_chars for c in answer)

        if language == 'en' and (has_sv or has_ar):
            return "Sorry bro, I should have replied in English. Could you ask that again?"
        if language == 'sv' and has_ar:
            return "Förlåt, jag ska svara på svenska. Kan du fråga igen?"
        if language == 'ar' and (has_sv or not has_ar):
            pass
        return answer
