import requests
import random
import os
import ssl
import re
import wikipedia
from src.project_env import load_project_dotenv

load_project_dotenv()

OPENWEATHER_KEY = os.getenv('OPENWEATHER_KEY')

# Fix SSL for Mac
ssl._create_default_https_context = ssl._create_unverified_context

class BeruSearch:
    def __init__(self):
        wikipedia.set_lang('en')

    @staticmethod
    def _wiki_lang(query):
        from src.language import is_arabic_text

        return 'ar' if is_arabic_text(query) else 'en'

    @staticmethod
    def _extract_city_from_weather_query(query, full_text=''):
        words = (query or '').lower().replace('?', '').split()
        skip = {
            'what', 'is', 'the', 'weather', 'in', 'today', 'talking', 'about',
            'temperature', 'forecast', 'like', 'how', 'whats', "what's",
            'current', 'now', 'degrees', 'can', 'you', 'search', 'browser',
            'google', 'for', 'on', 'open', 'and', 'any', 'of', 'me', 'tell',
            'vad', 'är', 'vädret', 'nu', 'idag', 'temperatur', 'grader',
        }
        city_words = [w for w in words if w not in skip and len(w) > 2]
        city = ' '.join(city_words).strip()
        blob = f'{(full_text or "").lower()} {(query or "").lower()}'
        for name in ('stockholm', 'gothenburg', 'göteborg', 'malmo', 'malmö', 'uppsala', 'london', 'paris'):
            if name in blob:
                return name.replace('ö', 'o')
        return city or 'Stockholm'

    def get_weather(self, query, full_text=''):
        city = self._extract_city_from_weather_query(query, full_text)
        is_swedish = any(c in f'{query}{full_text}' for c in 'åäöÅÄÖ')

        if OPENWEATHER_KEY:
            try:
                ow = self._weather_openweather(city, is_swedish)
                if ow:
                    return ow
            except Exception as e:
                print(f'OpenWeather error: {e}')

        try:
            om = self._weather_open_meteo(city, is_swedish)
            if om:
                return om
        except Exception as e:
            print(f'Open-Meteo error: {e}')

        try:
            return self._weather_wttr(city, is_swedish)
        except Exception as e:
            print(f'wttr.in error: {e}')
            return None

    def _weather_openweather(self, city, is_swedish):
        url = (
            f'http://api.openweathermap.org/data/2.5/weather'
            f'?q={city}&appid={OPENWEATHER_KEY}&units=metric'
        )
        data = requests.get(url, timeout=5).json()
        if data.get('cod') != 200:
            return None
        temp = round(data['main']['temp'])
        feels = round(data['main']['feels_like'])
        desc = data['weather'][0]['description']
        humidity = data['main']['humidity']
        city_name = data['name']
        country = data['sys']['country']
        if is_swedish:
            return (
                f'Det är just nu {temp}°C i {city_name}, {country}. '
                f'Känns som {feels}°C med {desc}. Luftfuktighet {humidity}%.'
            )
        return (
            f'It is currently {temp}°C in {city_name}, {country}. '
            f'Feels like {feels}°C with {desc}. Humidity is {humidity}%.'
        )

    def _weather_open_meteo(self, city, is_swedish):
        geo = requests.get(
            'https://geocoding-api.open-meteo.com/v1/search',
            params={'name': city, 'count': 1},
            timeout=5,
        ).json()
        results = geo.get('results') or []
        if not results:
            return None
        hit = results[0]
        lat, lon = hit['latitude'], hit['longitude']
        name = hit.get('name', city)
        country = hit.get('country_code', '')
        wx = requests.get(
            'https://api.open-meteo.com/v1/forecast',
            params={'latitude': lat, 'longitude': lon, 'current': 'temperature_2m,weather_code'},
            timeout=5,
        ).json()
        temp = round(wx['current']['temperature_2m'])
        code = int(wx['current'].get('weather_code', 0))
        desc = self._wmo_label(code, is_swedish)
        if is_swedish:
            return f'Det är just nu {temp}°C i {name}, {country}. {desc}.'
        return f'It is currently {temp}°C in {name}, {country}. {desc}.'

    @staticmethod
    def _wmo_label(code, is_swedish):
        labels_en = {
            0: 'Clear sky', 1: 'Mainly clear', 2: 'Partly cloudy', 3: 'Overcast',
            45: 'Foggy', 48: 'Foggy', 51: 'Light drizzle', 61: 'Rain',
            71: 'Snow', 80: 'Rain showers', 95: 'Thunderstorm',
        }
        labels_sv = {
            0: 'Klart', 1: 'Mestadels klart', 2: 'Delvis molnigt', 3: 'Mulet',
            45: 'Dimma', 61: 'Regn', 71: 'Snö', 80: 'Regnskurar', 95: 'Åska',
        }
        table = labels_sv if is_swedish else labels_en
        return table.get(code, 'Mixed conditions' if not is_swedish else 'Blandat väder')

    def _weather_wttr(self, city, is_swedish):
        import urllib.parse

        line = requests.get(
            f'https://wttr.in/{urllib.parse.quote(city)}?format=3',
            timeout=5,
            headers={'User-Agent': 'Beru/1.0'},
        ).text.strip()
        if not line or 'Unknown' in line:
            return None
        if is_swedish:
            return line.replace(':', ' — vädret i')
        return line.replace(':', ' — weather in')

    def search_wikipedia(self, query):
        try:
            from src.language import is_arabic_text

            lang = self._wiki_lang(query)
            wikipedia.set_lang(lang)

            # Only use the last question if multiple sentences
            if '.' in query and not is_arabic_text(query):
                query = query.split('.')[-1].strip()
            if '?' in query or '؟' in query:
                parts = re.split(r'[?؟]', query)
                query = parts[-2].strip() if len(parts) > 1 else query

            clean_query = query.strip('?؟').strip()
            clean_lower = clean_query.lower()

            remove_phrases = [
                'who is ', 'what is ', 'where is ', 'when is ', 'when will ',
                'tell me about ', 'who was ', 'what was ',
                'where was ', 'when was ',
                'vem är ', 'vad är ', 'var är ', 'när är ',
                'berätta om ', 'vem var ', 'vad var ',
                'من هو ', 'من هي ', 'ما هو ', 'ما هي ', 'ماذا ', 'متى ',
                'أريد ', 'اريد ', 'اعرف ', 'أعرف ', 'معلومات عن ', 'عن ',
                'ما اسباب ', 'ما أسباب ',
            ]
            for phrase in remove_phrases:
                if clean_lower.startswith(phrase) or clean_query.startswith(phrase):
                    clean_query = clean_query[len(phrase):]
                    clean_lower = clean_query.lower()
                    break

            clean_query = clean_query.strip()
            print(f"[Wikipedia {lang}: {clean_query}]")

            result = wikipedia.summary(clean_query, sentences=3, auto_suggest=True)

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

    def search_web(self, query, max_results=3):
        """DuckDuckGo text snippets — used for voice UI source=search."""
        try:
            from duckduckgo_search import DDGS

            with DDGS() as ddgs:
                hits = list(ddgs.text(query, max_results=max_results))
            bodies = [h.get('body', '').strip() for h in hits if h.get('body')]
            if not bodies:
                return None
            return ' '.join(bodies)[:500]
        except Exception as exc:
            print(f'Web search error: {exc}')
            return None

    def search(self, query, max_results=5):
        query_lower = query.lower()

        weather_words = ['weather', 'temperature', 'forecast',
                         'väder', 'vädret', 'temperatur', 'grader']
        if any(w in query_lower for w in weather_words):
            result = self.get_weather(query)
            if result:
                return result

        use_web = os.getenv('BERU_WEB_SEARCH', '1').strip().lower() in ('1', 'true', 'yes')
        if use_web:
            web = self.search_web(query)
            if web:
                return web

        wiki = self.search_wikipedia(query)
        if wiki:
            return wiki
        if use_web:
            return self.search_web(query)
        return None

    def format_response(self, result, query):
        if not result:
            return None

        from src.language import is_arabic_text

        query_lower = query.lower()
        is_swedish = any(c in query for c in 'åäöÅÄÖ')
        is_arabic = is_arabic_text(query)

        if is_arabic:
            intros = [
                'بحثت عن ذلك.',
                'إليك ما وجدته:',
                'هذا ما أعرفه من مصدر عام:',
            ]
            return f"{random.choice(intros)} {result}"

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

    def should_search(self, text, memory=None):
        from src.router import is_conversation_context_question

        from src.router import is_code_explanation_request

        if is_code_explanation_request(text):
            return False

        if memory and is_conversation_context_question(text, memory):
            return False

        text_lower = text.lower()
        if 'code' in text_lower and any(
            w in text_lower for w in ('what does', 'what do', 'explain', 'mean', 'how does')
        ):
            return False

        if memory and memory.knowledge.should_block_search(text, memory.is_owner()):
            return False

        if memory and memory.is_owner():
            if memory.is_owner_users_question(text):
                return False
            text_lower = text.lower()
            if 'friend' in text_lower and memory.is_owner_users_conversation_context():
                return False

        search_triggers = [
            # English
            'what is', 'who is', 'where is', 'when is',
            'how much', 'how many', 'what happened',
            'tell me about', 'what are', 'weather',
            'price of', 'how old', 'when was',
            'what does', 'who won', 'who is the',
            'temperature', 'forecast', 'when did',
            'world cup', 'causes of',
            # Swedish
            'vad är', 'vem är', 'var är', 'när är',
            'hur mycket', 'hur många', 'vad hände',
            'berätta om', 'vädret', 'väder',
            'temperatur', 'hur gammal är', 'när var',
            'vem vann', 'vad kostar',
            # Arabic
            'ما هو', 'ما هي', 'من هو', 'من هي', 'ماذا', 'متى', 'أين',
            'معلومات عن', 'اعرف', 'أعرف', 'اريد', 'أريد', 'اسباب', 'أسباب',
            'مجرة', 'كأس العالم', 'حرب', 'الحج', 'العمرة', 'مناسك',
        ]
        if any(trigger in text for trigger in search_triggers):
            return True
        return any(trigger in text_lower for trigger in search_triggers)