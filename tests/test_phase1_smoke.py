"""Phase 1 smoke tests — run without starting the full API server."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.markdown_format import format_for_ui, unwrap_prose_markdown_fences
from src.learning import is_learnable_exchange, append_conversation_pair
from src.memory import BeruMemory


def test_markdown_unwrap():
    wrapped = """```markdown
This code defines two interfaces.

* `id`: unique identifier
```"""
    out = unwrap_prose_markdown_fences(wrapped)
    assert '```' not in out, f"Expected unwrapped prose, got: {out!r}"
    assert 'interfaces' in out
    print("OK  markdown unwrap")

    java = """```java
public class Hello {}
```

Here is the explanation."""
    out2 = format_for_ui(java)
    assert '```java' in out2
    assert 'explanation' in out2
    print("OK  java fences preserved")


def test_memory_routing():
    from src.memory import OMAR_REMEMBER_TRIGGERS, OWNER_USERS_TRIGGERS

    remember_text = "don't give me suggestions when i ask for code, remember that".lower()
    assert any(t in remember_text for t in OMAR_REMEMBER_TRIGGERS)

    users_text = "who have you talked to".lower()
    assert any(t in users_text for t in OWNER_USERS_TRIGGERS)

    memory = BeruMemory()
    assert not memory.is_beru_activity_question("what are you")
    assert memory.is_beru_activity_question("what are you doing")
    print("OK  memory routing triggers")


def test_memory_json_clean():
    path = os.path.join(os.path.dirname(__file__), '..', 'data', 'memory.json')
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    users = data['known_users']
    names = [u.get('full_name') for u in users.values()]
    assert names.count('Sara') == 0, f"Stale Sara-only users remain: {names}"
    assert 'Sara Hassan' in names
    assert 'Sara Andersson' in names
    assert 'Omar Darwish' in names or 'Omar' in users
    print("OK  memory.json user cleanup")


def test_learning_rules():
    assert is_learnable_exchange(
        "write me a java hello world example",
        "Here is a simple Java program that prints Hello World to the console.",
        'brain',
    )
    assert not is_learnable_exchange("yes", "Okay! What is the password?", 'gate')
    assert not is_learnable_exchange("hi", "Hey!", 'memory')
    print("OK  learning rules")


def test_owner_routing():
    memory = BeruMemory()
    memory.session = {
        'identified': True,
        'name': 'Omar',
        'user_id': 'Omar',
        'is_owner': True,
        'language': 'en',
    }

    assert memory.is_owner_users_question('list all users')
    assert memory.is_owner_users_full_list_request('list all users')
    assert not memory.is_omar_recall_instructions('list all users')

    from src.knowledge import BeruKnowledge
    knowledge = BeruKnowledge()
    answer = knowledge.answer_omar_question(
        'what do you know about me', 'en', learned_facts=[]
    )
    assert answer and 'Omar Darwish' in answer
    assert 'creator' in answer.lower() or 'owner' in answer.lower()
    print('OK  owner list + profile routing')


def test_question_not_detected_as_name():
    from chat.chat import detect_full_name, detect_name, looks_like_question

    q = 'what is this document about?'
    assert looks_like_question(q)
    assert detect_full_name(q) is None
    assert detect_name(q) is None

    from src.document_index import BeruDocumentIndex
    assert BeruDocumentIndex.is_document_question('what is this docoment abot')
    assert not BeruDocumentIndex.is_document_question(
        'good i will send you a docoment can you tell me what is say'
    )
    assert BeruDocumentIndex.is_pre_upload_document_intent(
        'good i will send you a docoment can you tell me what is say'
    )
    assert BeruDocumentIndex.is_document_question('what did my cv say?')
    assert BeruDocumentIndex.is_document_question('but i does try reading it again')
    assert BeruDocumentIndex.is_remember_from_document_intent(
        'i want you to remember those info in this docoment about me'
    )
    print('OK  questions not parsed as names')


def test_document_analysis():
    from src.document_loader import extract_pdf_text
    from src.document_analysis import analyze_document_text, format_analysis_notes

    path = '/Users/omardarwish/Downloads/test pdf.pdf'
    if not os.path.exists(path):
        print('SKIP document analysis (test pdf not on machine)')
        return

    pages = extract_pdf_text(path)
    analysis = analyze_document_text(pages[0]['text'])
    assert analysis['style'] == 'feedback'
    assert analysis['appears_incomplete'] is True
    notes = format_analysis_notes(analysis, 'en')
    assert 'INCOMPLETE' in notes
    assert 'feedback' in notes.lower() or 'corrective' in notes.lower()
    print('OK  document analysis heuristics')


def test_cv_not_marked_incomplete():
    from src.document_loader import extract_pdf_text
    from src.document_analysis import analyze_document_text

    paths = [
        '/Users/omardarwish/Library/Mobile Documents/com~apple~CloudDocs/Downloads/Omar CV.pdf',
        '/Users/omardarwish/Downloads/Omar CV.pdf',
    ]
    path = next((p for p in paths if os.path.exists(p)), None)
    if not path:
        print('SKIP cv completeness (Omar CV.pdf not on machine)')
        return

    pages = extract_pdf_text(path)
    analysis = analyze_document_text(pages[0]['text'])
    assert analysis['appears_incomplete'] is False, analysis
    print('OK  cv completeness heuristic')


def test_owner_profile_summary_voice():
    from src.knowledge import BeruKnowledge

    knowledge = BeruKnowledge()
    facts = [
        "Don't give me suggestions when I ask for code, only give me when i ask",
        'Omar Darwish is a student in Software Engineering and Management at Göteborgs universitet',
        'He has experience with software development through his own projects in web, mobile, and AI',
        'He worked as a server at a restaurant in Karlstad from 2020 to 2022',
        'Omar Darwish knows several programming languages: TypeScript, JavaScript, Java, Python',
    ]
    answer = knowledge.format_omar_profile_summary('en', facts)
    assert "You're" in answer or 'You study' in answer
    assert 'separate from facts about you' in answer
    assert 'mainly' in answer
    assert 'He has experience' not in answer
    assert 'you knows' not in answer.lower()
    assert 'Want more on' in answer

    detail = knowledge._format_owner_category_detail('skills', facts, 'en')
    assert 'you know' in detail.lower()
    assert 'Want even more' in detail or 'more on your' in detail

    guest = knowledge.answer_omar_for_guest('who is omar', 'en', guest_name='Sara')
    assert 'Want to know more' in guest
    assert 'password' not in guest.lower()
    print('OK  owner profile speaks to you')


if __name__ == '__main__':
    test_markdown_unwrap()
    test_memory_routing()
    test_memory_json_clean()
    test_learning_rules()
    test_owner_routing()
    test_question_not_detected_as_name()
    test_document_analysis()
    test_cv_not_marked_incomplete()
    test_owner_profile_summary_voice()
    print("\nAll Phase 1 smoke tests passed.")
