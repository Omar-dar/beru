def detect_language(text):
    swedish_chars = set('åäöÅÄÖ')
    arabic_chars = set('ابتثجحخدذرزسشصضطظعغفقكلمنهوي')
    swedish_words = {
        'vad', 'heter', 'jag', 'hur', 'vem', 'är', 'det',
        'och', 'att', 'kan', 'du', 'inte', 'med', 'för',
        'på', 'om', 'men', 'har', 'en', 'ett', 'var',
        'när', 'vill', 'ska', 'vi', 'de', 'sig', 'som',
    }
    if any(c in swedish_chars for c in text):
        return 'sv'
    if any(c in arabic_chars for c in text):
        return 'ar'
    words = set(text.lower().split())
    if len(words.intersection(swedish_words)) >= 2:
        return 'sv'
    return 'en'
