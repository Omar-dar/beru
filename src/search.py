import requests
import random
import os
import ssl
import re
import wikipedia
from dotenv import load_dotenv

load_dotenv()

OPENWEATHER_KEY = os.getenv('OPENWEATHER_KEY')

# Fix SSL for Mac
ssl._create_default_https_context = ssl._create_unverified_context

class TildSearch:
    def __init__(self):
        wikipedia.set_lang('en')

    def get_weather(self, query):
        try:
            words = query.lower().replace('?', '').split()
            skip = ['what', 'is', 'the', 'weather', 'in', 'today',
                    'temperature', 'forecast', 'like', 'how', 'whats',
                    'current', 'now', 'degrees', 'vad', 'är', 'vädret',
                    'nu', 'idag', 'temperatur', 'grader']
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
                is_swedish = any(c in query for c in 'åäöÅÄÖ')
                if is_swedish:
                    return f"Det är just nu {temp}°C i {city_name}, {country}. Känns som {feels}°C med {desc}. Luftfuktighet {humidity}%."
                else:
                    return f"It is currently {temp}°C in {city_name}, {country}. Feels like {feels}°C with {desc}. Humidity is {humidity}%."
            else:
                return None
        except Exception as e:
            print(f"Weather error: {e}")
            return None

    def search_wikipedia(self, query):
        try:
            # Only use the last question if multiple sentences
            if '.' in query:
                query = query.split('.')[-1].strip()
            if '?' in query:
                parts = query.split('?')
                query = parts[-2].strip() + '?' if len(parts) > 1 else query

            clean_query = query.lower().strip('?').strip()

            remove_phrases = [
                'who is ', 'what is ', 'where is ', 'when is ',
                'tell me about ', 'who was ', 'what was ',
                'where was ', 'when was ',
                'vem är ', 'vad är ', 'var är ', 'när är ',
                'berätta om ', 'vem var ', 'vad var ',
            ]
            for phrase in remove_phrases:
                if clean_query.startswith(phrase):
                    clean_query = clean_query[len(phrase):]
                    break

            clean_query = clean_query.strip()
            print(f"[Wikipedia searching: {clean_query}]")

            result = wikipedia.summary(clean_query, sentences=2, auto_suggest=True)

            if len(result) > 200:
                result = result[:200] + "..."
            return result

        except wikipedia.exceptions.DisambiguationError as e:
            try:
                result = wikipedia.summary(e.options[0], sentences=2)
                if len(result) > 200:
                    result = result[:200] + "..."
                return result
            except:
                return None
        except Exception as e:
            print(f"Wikipedia error: {e}")
            return None

    def search(self, query, max_results=5):
        query_lower = query.lower()

        weather_words = ['weather', 'temperature', 'forecast',
                         'väder', 'vädret', 'temperatur', 'grader']
        if any(w in query_lower for w in weather_words):
            result = self.get_weather(query)
            if result:
                return result

        return self.search_wikipedia(query)

    def format_response(self, result, query):
        if not result:
            return None

        query_lower = query.lower()
        is_swedish = any(c in query for c in 'åäöÅÄÖ')

        if any(w in query_lower for w in ['weather', 'temperature', 'väder', 'vädret', 'temperatur']):
            intros = ['Jag kollade!', 'Här är vädret.', 'Jag sökte upp det!'] if is_swedish else ['I checked for you!', 'Here is the weather.', 'I looked it up!']
        elif any(w in query_lower for w in ['who is', 'vem är']):
            intros = ['Jag sökte upp det!', 'Här är vad jag vet.', 'Intressant fråga!'] if is_swedish else ['I looked that up!', 'Here is what I know.', 'Interesting question!']
        elif any(w in query_lower for w in ['what is', 'vad är']):
            intros = ['Bra fråga! Här är vad jag hittade.', 'Jag sökte upp det.', 'Här är vad jag vet.'] if is_swedish else ['Good question! Here is what I found.', 'I looked that up for you.', 'Here is what I know about that.']
        elif any(w in query_lower for w in ['where is', 'var är']):
            intros = ['Jag sökte upp det!', 'Här är vad jag hittade.', 'Låt mig berätta!'] if is_swedish else ['I looked that up!', 'Here is what I found.', 'Let me tell you!']
        else:
            intros = ['Jag sökte upp det!', 'Här är vad jag hittade.', 'Låt mig dela vad jag hittade.'] if is_swedish else ['I looked that up!', 'Here is what I found.', 'Let me share what I found.']

        intro = random.choice(intros)
        return f"{intro} {result}"

    def should_search(self, text):
        search_triggers = [
            # English
            'what is', 'who is', 'where is', 'when is',
            'how much', 'how many', 'what happened',
            'tell me about', 'what are', 'weather',
            'price of', 'how old', 'when was',
            'what does', 'who won', 'who is the',
            'temperature', 'forecast', 'when did',
            # Swedish
            'vad är', 'vem är', 'var är', 'när är',
            'hur mycket', 'hur många', 'vad hände',
            'berätta om', 'vädret', 'väder',
            'temperatur', 'hur gammal är', 'när var',
            'vem vann', 'vad kostar',
        ]
        text_lower = text.lower()
        return any(trigger in text_lower for trigger in search_triggers)