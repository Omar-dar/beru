from ddgs import DDGS
import requests
import random
import os
from dotenv import load_dotenv

load_dotenv()

OPENWEATHER_KEY = os.getenv('OPENWEATHER_KEY')

class TildSearch:
    def __init__(self):
        pass

    def get_weather(self, query):
        try:
            words = query.lower().replace('?', '').split()
            skip = ['what', 'is', 'the', 'weather', 'in', 'today',
                   'temperature', 'forecast', 'like', 'how', 'whats',
                   'current', 'now', 'degrees']
            city_words = [w for w in words if w not in skip]
            city = ' '.join(city_words).strip()

            if not city:
                city = "Gothenburg"

            url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_KEY}&units=metric"
            response = requests.get(url, timeout=5)
            data = response.json()

            if data.get('cod') == 200:
                temp = round(data['main']['temp'])
                feels = round(data['main']['feels_like'])
                desc = data['weather'][0]['description']
                humidity = data['main']['humidity']
                city_name = data['name']
                country = data['sys']['country']
                return f"It is currently {temp}°C in {city_name}, {country}. Feels like {feels}°C with {desc}. Humidity is {humidity}%."
            else:
                return None
        except Exception as e:
            print(f"Weather error: {e}")
            return None

    def search_web(self, query, max_results=5):
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(
                    query,
                    max_results=max_results,
                ))
            if not results:
                return None
            for result in results:
                body = result.get('body', '')
                if len(body) > 50:
                    if len(body) > 200:
                        body = body[:200] + "..."
                    return body
            return None
        except Exception as e:
            print(f"Search error: {e}")
            return None

    def search(self, query, max_results=5):
        query_lower = query.lower()

        if 'weather' in query_lower or 'temperature' in query_lower or 'forecast' in query_lower:
            result = self.get_weather(query)
            if result:
                return result

        return self.search_web(query, max_results)

    def format_response(self, result, query):
        if not result:
            return None

        query_lower = query.lower()

        if 'weather' in query_lower or 'temperature' in query_lower:
            intros = [
                "I checked for you!",
                "Here is the weather.",
                "I looked it up!",
            ]
        elif 'who is' in query_lower:
            intros = [
                "I looked that up!",
                "Here is what I know.",
                "Interesting question!",
            ]
        elif 'what is' in query_lower:
            intros = [
                "Good question! Here is what I found.",
                "I looked that up for you.",
                "Here is what I know about that.",
            ]
        elif 'news' in query_lower or 'latest' in query_lower:
            intros = [
                "Here is what is happening.",
                "I checked the latest news.",
                "Here is what I found.",
            ]
        else:
            intros = [
                "I looked that up!",
                "Here is what I found.",
                "Let me share what I found.",
            ]

        intro = random.choice(intros)
        return f"{intro} {result}"

    def should_search(self, text):
        search_triggers = [
            'what is', 'who is', 'where is', 'when is',
            'how much', 'how many', 'what happened',
            'tell me about', 'what are', 'latest',
            'current', 'today', 'news', 'weather',
            'price of', 'how old', 'when was',
            'what does', 'who won', 'who is the',
            'temperature', 'forecast', 'score',
            'when did', 'what time', 'how far',
        ]
        text_lower = text.lower()
        return any(trigger in text_lower for trigger in search_triggers)