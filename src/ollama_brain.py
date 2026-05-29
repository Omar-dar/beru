import subprocess
import time
import requests


class OllamaBrain:

    def __init__(self, model="llama3.2:3b"):

        self.model = model

        self.base_url = "http://localhost:11434"

        self.generate_url = (
            f"{self.base_url}/api/generate"
        )

        self.ensure_ollama_running()


    def ensure_ollama_running(self):

        try:
            requests.get(
                self.base_url,
                timeout=2
            )

            print(
                "Ollama already running."
            )

            return

        except Exception:

            print(
                "Starting Ollama service..."
            )

        subprocess.Popen(

            [
                "brew",
                "services",
                "start",
                "ollama"
            ],

            stdout=subprocess.DEVNULL,

            stderr=subprocess.DEVNULL
        )

        for _ in range(15):

            try:
                requests.get(
                    self.base_url,
                    timeout=2
                )

                print(
                    "Ollama server is running."
                )

                return

            except Exception:

                time.sleep(1)

        print(
            "Could not start Ollama."
        )


    def ask(
        self,
        user_input,
        language="en"
    ):

        prompt = f"""
You are Tild, Omar's personal AI assistant.
Answer in the same language as the user.
If the user writes Swedish, answer in natural Swedish only.
Do not mix Swedish with German or English.
Keep answers short, warm and conversational.
Do not say you are Ollama, Llama or another AI model.

User: {user_input}

Tild:
"""

        try:

            response = requests.post(

                self.generate_url,

                json={

                    "model": self.model,

                    "prompt": prompt,

                    "stream": False,

                    "options": {

                        "temperature": 0.8,

                        "top_p": 0.9
                    }
                },

                timeout=90
            )

            data = response.json()

            answer = data.get(
                "response",
                ""
            ).strip()

            if len(answer) < 2:

                raise Exception(
                    "Empty response"
                )

            return answer

        except Exception as e:

            print(
                f"Ollama error: {e}"
            )

            if language == "sv":

                return (
                    "Jag är inte helt säker just nu, "
                    "men jag försöker lära mig."
                )

            elif language == "ar":

                return (
                    "لست متأكدًا تمامًا الآن، "
                    "لكنني أحاول التعلم."
                )

            return (
                "I am not completely sure right now, "
                "but I am trying to learn."
            )