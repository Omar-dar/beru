from ddgs import DDGS

class TildSearch:
    def __init__(self):
        pass

    def improve_query(self, query):
        query_lower = query.lower()
        # Improve weather queries
        if 'weather' in query_lower:
            if 'temperature' not in query_lower:
                query = query + " temperature forecast"
        return query

    def search(self, query, max_results=5):
        try:
            query = self.improve_query(query)
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
            if not results:
                return None
            # Try to find most relevant result
            for result in results:
                body = result['body']
                if len(body) > 50:
                    if len(body) > 200:
                        body = body[:200] + "..."
                    return body
            return None
        except Exception as e:
            print(f"Search error: {e}")
            return None

    def should_search(self, text):
        search_triggers = [
            'what is', 'who is', 'where is', 'when is',
            'how much', 'how many', 'what happened',
            'tell me about', 'what are', 'latest',
            'current', 'today', 'news', 'weather',
            'price of', 'how old', 'when was',
            'what does', 'who won', 'who is the',
            'temperature', 'forecast', 'score',
        ]
        text_lower = text.lower()
        return any(trigger in text_lower for trigger in search_triggers)