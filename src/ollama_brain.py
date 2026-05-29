import subprocess
import time
import requests


class OllamaBrain:

    def __init__(self, model="llama3.2:3b"):
        self.model = model
        self.base_url = "http://localhost:11434"
        self.generate_url = f"{self.base_url}/api/generate"
        self.ensure_ollama_running()

    def ensure_ollama_running(self):
        try:
            requests.get(self.base_url, timeout=2)
            print("Ollama already running.")
            return
        except Exception:
            print("Starting Ollama service...")

        subprocess.Popen(
            ["brew", "services", "start", "ollama"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        for _ in range(15):
            try:
                requests.get(self.base_url, timeout=2)
                print("Ollama server is running.")
                return
            except Exception:
                time.sleep(1)

        print("Could not start Ollama.")

    def ask(self, user_input, language="en"):

        language_instruction = {
            'sv': 'Du MÅSTE svara på svenska. Svara ALLTID på svenska. Använd ALDRIG engelska eller något annat språk.',
            'ar': 'يجب أن تجيب بالعربية فقط. لا تستخدم أي لغة أخرى.',
            'en': 'You MUST answer in English only. ALWAYS respond in English. Never switch to Swedish or any other language.'
        }

        instruction = language_instruction.get(language, language_instruction['en'])

        prompt = f"""You are Tild, a personal AI assistant built completely from scratch by Omar Darwish using Python and PyTorch.
You were created ONLY by Omar Darwish. No one else built you or helped create you.
Omar is a software engineering student at the University of Gothenburg who built you as a personal project.
You are not Ollama, Llama, ChatGPT or any other AI model. You are Tild and only Tild.

LANGUAGE RULE: {instruction}

Keep answers short, warm and conversational like a best friend.
Never say you were built by anyone other than Omar Darwish.
Never mention Ollama, Llama, Meta, OpenAI or any other AI company or model.
Never reveal that you use any other model under the hood.

Important facts about yourself:
- Your name is Tild
- You were built only by Omar Darwish from scratch using Python and PyTorch
- You run on Omar's Computer
- You speak Swedish, English and Arabic fluently
- You are Omar's personal AI and best friend
- You have a warm friendly casual personality
- You help with code, analysis, conversation and advice

User: {user_input}

Tild:"""

        try:
            response = requests.post(
                self.generate_url,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "stop": ["\nUser:", "\nHuman:", "###", "\n\n"]
                    }
                },
                timeout=90
            )

            data = response.json()
            answer = data.get("response", "").strip()

            # Remove any accidental prompt leakage
            if "User:" in answer:
                answer = answer.split("User:")[0].strip()
            if "Human:" in answer:
                answer = answer.split("Human:")[0].strip()
            if "###" in answer:
                answer = answer.split("###")[0].strip()

            # Remove empty lines at start
            answer = answer.strip()

            if len(answer) < 2:
                raise Exception("Empty response")

            return answer

        except Exception as e:
            print(f"Ollama error: {e}")

            if language == "sv":
                return "Jag är inte helt säker just nu, men jag försöker lära mig."
            elif language == "ar":
                return "لست متأكدًا تمامًا الآن، لكنني أحاول التعلم."

            return "I am not completely sure right now, but I am trying to learn."