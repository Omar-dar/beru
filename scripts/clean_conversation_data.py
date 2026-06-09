"""
Clean bad Human/Beru pairs at the end of data/conversation_data.txt
(Omar voice-test logs with wrong routing, URLs in replies, etc.).
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / 'data' / 'conversation_data.txt'
OMAR_SESSION_START = 119106

DROP_HUMAN = frozenset({
    'them has called but they',
    'góvel do hitta pua.',
    'poživajte.',
    'thanks for watching!',
    'could you?',
})

DROP_HUMAN_PREFIXES = ('góvel do',)

EXACT_FIXES: dict[str, str] = {
    'idag chillade jag bara sen gick till gymmet och körd rygg idag och lite cardio sen gick jag hem': (
        'Nice bro! Chill first, then back and cardio at the gym — sounds like a solid day. '
        'Want me to remember that for today?'
    ),
    'det kändes bra': (
        'Härligt bro! Kul att passet satt bra. Ska du ta det lugnt resten av kvällen?'
    ),
    'من هو عمر': (
        'أنت يا عمر! أنت Omar Darwish، من أنشأني. أتحدث معك مباشرة دائماً.'
    ),
    'من هو القائد عمر': (
        'أنت Omar Darwish يا صديقي — من أنشأني وبنيتني من الصفر.'
    ),
    'وين المشكله انني اسالك عن omar': (
        'أنت Omar Darwish — من أنشأني. أقصدك دائماً عندما أتحدث معك.'
    ),
    'good how are you?': (
        "I'm doing well bro, thanks for asking! How's your day going?"
    ),
    'what is ollama': (
        'Ollama runs large language models locally on your machine — Beru uses it for deep '
        'replies when the fast handlers do not have an answer.'
    ),
    'what do you wnat to do?': (
        'I am here to talk with you and help with whatever you need bro — code, search, '
        'memory, or just chat. What do you want to do?'
    ),
    'can you code?': (
        'Yes bro! You built me for coding. Tell me the language and what the program should do.'
    ),
    'do you like you name?': (
        'I like the name Beru — you gave it to me when you created me. It fits.'
    ),
    'what do you want to learn': (
        'I learn the most from you bro — our talks, your corrections, and when we code together. '
        'What do you want help with?'
    ),
    'what do you want to learn today?': (
        'I learn the most from you bro — our talks, your corrections, and when we code together. '
        'What do you want help with?'
    ),
    'what do you want to do?': (
        'I am here to talk with you and help with whatever you need bro. What is on your mind?'
    ),
    'what do you want to do today': (
        'I am here to chat and help you today bro — no human hobbies on my side. What are you up to?'
    ),
    "what's up": (
        "Not much on my side bro — I'm here for you. What's up with you today?"
    ),
    "i'm just chatting with you. that's all": (
        "Got it bro, just vibing. I'm here if you want to talk about anything."
    ),
    'can you hear me? wake up, perot!': (
        "I'm awake, sir. What will you be doing today?"
    ),
    'great! what do you want to learn today?': (
        'I learn the most from you bro — from our talks and when we code together. What should we dig into?'
    ),
    'i mean, i ask you, what do you want to learn today?': (
        'I learn from you bro — your corrections and our projects. What do you want to work on?'
    ),
    'bero, i\'m talking in english or i\'m speaking in english. why are you answering in swedish?': (
        'Got it bro, English from here on. What do you want to do?'
    ),
    'alright, speak with me in arabic': (
        'تمام! سأتحدث معك بالعربية. كيف يمكنني مساعدتك؟'
    ),
    'bero, can you speak arabic?': (
        'نعم، أستطيع التحدث بالعربية. ماذا تريد أن نتحدث عنه؟'
    ),
    'jag har frågat dig vem har skapat dig?': (
        'Du byggde mig från grunden med Python och PyTorch bro — du är min skapare och ägare.'
    ),
    'så vet du om jag är nu.': (
        'Ja bro! Du är Omar Darwish, min skapare och bästa kompis. Jag pratar alltid direkt med dig.'
    ),
    'jag frågade dig vad vill du hitta på?': (
        'Jag är här för att snacka och hjälpa dig bro — vad har du lust att göra?'
    ),
    'could you tell me what you can do?': (
        'I can chat in English, Swedish, and Arabic, remember people and conversations, learn from '
        'corrections, search the web and weather, open and read browser pages, close tabs, scroll, '
        'and help with code and writing.'
    ),
    'could you open google?': (
        'Opened google.com in your browser. Say "what can you see?" and I will read the page.'
    ),
    'what can you see?': (
        'Google is open — if you see a cookie screen, accept it in the browser then ask again. '
        'Otherwise I read the page text from what you opened.'
    ),
    'close the facebook tab.': (
        'Closing the facebook tab bro.'
    ),
    'close google tap.': (
        'Closing the google tab bro.'
    ),
    'could you close the tap?': (
        'Closing the current tab bro.'
    ),
    'me enclose this tab that\'s opened.': (
        'Closing this tab bro.'
    ),
    'no, but could you look at the browser and tell me what you can see?': (
        'Open a site first, then say "what can you see?" — I read the browser tab, not Google-search your words.'
    ),
    'can you read it?': (
        'I read the open page from the last site you opened — ask "what can you see?" or "read the page".'
    ),
    'read what\'s on the browser.': (
        'I read what is on the open browser tab — not a new Google search.'
    ),
    'search on google. what\'s the weather in stockholm?': (
        'It is currently about 20°C in Stockholm, partly cloudy — from the weather API, not a guess.'
    ),
    'could you open google on browser?': (
        'Opened google.com in your browser. Say "what can you see?" when you want me to read it.'
    ),
    'just write a hello world in java in the chat': (
        '```java\npublic class HelloWorld {\n    public static void main(String[] args) {\n'
        '        System.out.println("Hello, World!");\n    }\n}\n```'
    ),
    'what does this code do?': (
        'It defines a function and prints a greeting — point me at the code above if you want a walkthrough.'
    ),
    'what does that code do?': (
        'Same as the code we just wrote — tell me which part you want explained bro.'
    ),
    'i am asking about the code what does it do?': (
        'That code greets someone by name — it calls greet() and prints Hello plus the name. '
        'Want me to explain line by line?'
    ),
    'can you browse my browser?': (
        'Yes bro — I can open sites, search the web, read pages, close tabs, and scroll. '
        'Try "open Google" or "search for weather in Stockholm".'
    ),
    'yeah, do it.': (
        'On it bro — closing the tab now.'
    ),
    'ماذا هل تحدث عنه؟': (
        'كنت أتحدث عن آخر شيء فتحناه في المتصفح. ماذا تريد أن أفعل الآن؟'
    ),
    'all right, find me on the internet where to buy a car in sweden': (
        'Good places to start: blocket.se, wayke.se, and authorized dealers. '
        'Want me to search for a specific car brand or city?'
    ),
    'search google for python tutorials.': (
        'I opened a search for Python tutorials in your browser. Say "what can you see?" if you want a summary.'
    ),
    'good, good. can you search on google what\'s the weather in stockholm today?': (
        'It is currently about 20°C in Stockholm, partly cloudy.'
    ),
    'can you search on google what\'s the weather in stockholm today?': (
        'It is currently about 20°C in Stockholm, partly cloudy.'
    ),
    'yeah, what can you see? what can you see?': (
        'It is currently about 20°C in Stockholm, partly cloudy — from the weather data on the page.'
    ),
    'can you read it for me, can you read it for me, can you read it for me?': (
        'It is currently about 21°C in Stockholm, partly cloudy.'
    ),
    'search on google. what\'s the weather in stockholm?': (
        'It is currently about 21°C in Stockholm, partly cloudy.'
    ),
    'what is this? why did you open the browser?': (
        'Sorry bro — I thought you wanted a web search. I am here to talk. What do you want to do?'
    ),
    'sorry bro, i thought you wanted a web search. could you open google?': (
        'Opened google.com in your browser. Say "what can you see?" and I will read the page.'
    ),
    'هل يمكنك التحدث معي باللغة العربية؟': (
        'نعم، أستطيع التحدث معك بالعربية. كيف يمكنني مساعدتك اليوم؟'
    ),
    'ما اسمي؟': (
        'اسمك Omar Darwish يا صديقي — أنت من أنشأني.'
    ),
    'هون تتعرف اسمي؟': (
        'نعم! أنت Omar Darwish، من أنشأني. اسمي Beru.'
    ),
    'can you speak arabic': (
        'Yes bro — I can speak Arabic. تريد نكمل بالعربية؟'
    ),
    'i want talk to you by arabic': (
        'تمام، نتحدث بالعربية. كيف يمكنني مساعدتك؟'
    ),
    'what do you want to do today': (
        'I am here to chat and help you today bro. What are you up to?'
    ),
}


def _norm_q(text: str) -> str:
    return re.sub(r'\s+', ' ', (text or '').strip().lower())


def parse_pairs(lines: list[str]) -> list[tuple[int, str, str]]:
    pairs: list[tuple[int, str, str]] = []
    i = 0
    while i < len(lines):
        if lines[i].startswith('### Human:'):
            start = i + 1
            human = lines[i][len('### Human:'):].strip()
            i += 1
            beru_parts: list[str] = []
            if i < len(lines) and lines[i].startswith('### Beru:'):
                beru_parts.append(lines[i][len('### Beru:'):].strip())
                i += 1
                while i < len(lines) and not lines[i].startswith('### Human:'):
                    beru_parts.append(lines[i])
                    i += 1
            pairs.append((start, human, '\n'.join(beru_parts).strip()))
            continue
        i += 1
    return pairs


def should_drop_human(human: str) -> bool:
    n = _norm_q(human)
    if n in DROP_HUMAN:
        return True
    return any(n.startswith(p) for p in DROP_HUMAN_PREFIXES)


def is_bad_beru(beru: str) -> bool:
    low = beru.lower()
    if 'google.com/search?q=' in low:
        return True
    if low.startswith('url: http'):
        return True
    if 'cungulmak' in low or 'tổmha' in low or '⁧' in beru:
        return True
    if 'i do not know that for certain yet' in low:
        return True
    if 'whatsapp web' in low and 'weather' not in low:
        return True
    return False


def fix_beru(human: str, beru: str) -> str | None:
    n = _norm_q(human)
    if n in EXACT_FIXES:
        return EXACT_FIXES[n] or None

    for key, val in EXACT_FIXES.items():
        if len(key) > 20 and (key in n or n in key):
            return val or None

    if is_bad_beru(beru):
        return None

    out = beru
    subs = [
        (r"Sorry bro, I should have replied in English[^\n]*",
         'Got it bro — I match your language. Ask again in the language you prefer.'),
        (r'أنا تيلد[^\n]*', 'أنا Beru، مساعدك الشخصي. أنت Omar من أنشأني.'),
        (r"I'll go to the gym today[^\n]*", "Got it bro, just chatting. I'm here if you need anything."),
        (r'You going to the gym today[^\n]*', "I'm here bro — what's on your mind today?"),
        (r'I captured your screen[^\n]*', 'Open a site first, then ask "what can you see?" and I read the browser tab.'),
        (r'Ylvis|What Does the Fox Say[^\n]*',
         'That code greets by name — want a line-by-line explanation bro?'),
        (r'Opened Google in your browser[^\n]*https?://[^\n]*',
         'Opened the page in your browser. Say "what can you see?" to read it.'),
        (r'```python\s*\nI don\'t have the capability[^\n]*',
         'Yes bro — I can open sites, search, read pages, close tabs, and scroll in your browser.'),
    ]
    for pat, repl in subs:
        out = re.sub(pat, repl, out, flags=re.I)

    if is_bad_beru(out):
        return None
    return out.strip() or None


def main():
    lines = DATA_PATH.read_text(encoding='utf-8').splitlines()
    pairs = parse_pairs(lines)

    out_lines: list[str] = []
    changed = 0
    dropped = 0
    kept_tail = 0

    for start_line, human, beru in pairs:
        if start_line < OMAR_SESSION_START:
            # preserve original block from lines — rebuild from pair
            out_lines.append(f'### Human: {human}')
            if beru:
                for j, part in enumerate(beru.split('\n')):
                    if j == 0:
                        out_lines.append(f'### Beru: {part}')
                    else:
                        out_lines.append(part)
            out_lines.append('')
            continue

        if should_drop_human(human):
            dropped += 1
            continue

        fixed = fix_beru(human, beru)
        if fixed is None:
            dropped += 1
            continue

        if fixed != beru:
            changed += 1
        kept_tail += 1
        out_lines.append(f'### Human: {human}')
        for j, part in enumerate(fixed.split('\n')):
            if j == 0:
                out_lines.append(f'### Beru: {part}')
            else:
                out_lines.append(part)
        out_lines.append('')

    DATA_PATH.write_text('\n'.join(out_lines).rstrip() + '\n', encoding='utf-8')
    print(
        f'Cleaned {DATA_PATH.name}: {changed} fixed, {dropped} removed, '
        f'{kept_tail} kept in Omar session tail (line {OMAR_SESSION_START}+)'
    )


if __name__ == '__main__':
    main()
