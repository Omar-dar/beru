import re

class TildEntityRecognizer:
    def __init__(self):
        # Common Swedish and English first names
        self.common_names = {
            'erik', 'anna', 'lars', 'sara', 'johan', 'maria', 'peter',
            'emma', 'oscar', 'sofia', 'magnus', 'linda', 'david', 'karin',
            'mikael', 'helena', 'andreas', 'jessica', 'daniel', 'jenny',
            'john', 'sarah', 'mike', 'lisa', 'james', 'emily', 'robert',
            'emma', 'william', 'olivia', 'ahmed', 'fatima', 'ali', 'omar',
            'karim', 'sara', 'ibrahim', 'nour', 'hassan', 'leila',
            'marcus', 'julia', 'tobias', 'frida', 'alexander', 'maja',
            'viktor', 'alice', 'filip', 'elsa', 'simon', 'astrid'
        }

        # Swedish cities and places
        self.places = {
            'stockholm', 'göteborg', 'malmö', 'uppsala', 'västerås',
            'örebro', 'linköping', 'helsingborg', 'jönköping', 'norrköping',
            'karlstad', 'sundsvall', 'gävle', 'umeå', 'luleå', 'borås',
            'eskilstuna', 'halmstad', 'växjö', 'kalmar', 'kristianstad',
            'london', 'paris', 'berlin', 'madrid', 'rome', 'amsterdam',
            'new york', 'los angeles', 'chicago', 'dubai', 'tokyo'
        }

    def extract_entities(self, text):
        entities = {
            'persons': [],
            'places': [],
            'dates': [],
            'organizations': []
        }

        # Find dates — Swedish and English formats
        date_patterns = [
            r'\d{4}-\d{2}-\d{2}',
            r'\d{1,2}\s+(?:januari|februari|mars|april|maj|juni|juli|augusti|september|oktober|november|december)\s+\d{4}',
            r'\d{1,2}\s+(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{4}',
            r'(?:den\s+)?\d{1,2}\s+(?:jan|feb|mar|apr|maj|jun|jul|aug|sep|okt|nov|dec)',
            r'\d{1,2}/\d{1,2}/\d{2,4}',
        ]
        for pattern in date_patterns:
            found = re.findall(pattern, text.lower())
            entities['dates'].extend(found)

        # Find capitalized words that could be names or places
        words = text.split()
        for i, word in enumerate(words):
            clean = word.strip('.,!?;:()[]"\'')
            clean_lower = clean.lower()

            # Check known names
            if clean_lower in self.common_names:
                if clean_lower not in [p.lower() for p in entities['persons']]:
                    entities['persons'].append(clean)

            # Check known places
            if clean_lower in self.places:
                if clean_lower not in [p.lower() for p in entities['places']]:
                    entities['places'].append(clean)

            # Detect unknown capitalized words as potential names
            if (clean and clean[0].isupper() and
                len(clean) > 1 and
                clean_lower not in {'i', 'a', 'the', 'och', 'att', 'det', 'en', 'ett',
                                    'på', 'av', 'för', 'med', 'till', 'från', 'om',
                                    'men', 'är', 'var', 'har', 'hade', 'den', 'de'} and
                i > 0):  # Not first word of sentence
                if clean not in entities['persons'] and clean not in entities['places']:
                    entities['persons'].append(clean)

        # Remove duplicates
        entities['persons'] = list(dict.fromkeys(entities['persons']))
        entities['places'] = list(dict.fromkeys(entities['places']))
        entities['dates'] = list(dict.fromkeys(entities['dates']))

        return entities

    def format_entities(self, entities, language='en'):
        if not any(entities.values()):
            return None

        if language == 'sv':
            result = "Jag identifierade följande:\n"
            if entities['persons']:
                result += f"\nPersoner: {', '.join(entities['persons'])}"
            if entities['places']:
                result += f"\nPlatser: {', '.join(entities['places'])}"
            if entities['dates']:
                result += f"\nDatum: {', '.join(entities['dates'])}"
        else:
            result = "I identified the following:\n"
            if entities['persons']:
                result += f"\nPersons: {', '.join(entities['persons'])}"
            if entities['places']:
                result += f"\nPlaces: {', '.join(entities['places'])}"
            if entities['dates']:
                result += f"\nDates: {', '.join(entities['dates'])}"

        return result