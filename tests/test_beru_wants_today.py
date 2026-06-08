from src.knowledge import BeruKnowledge


def test_want_to_do_today_is_activity_question():
    k = BeruKnowledge()
    assert k.is_beru_activity_question('what do you want to do today')


def test_no_human_projects_in_reply():
    k = BeruKnowledge()
    reply = k.answer_beru_activity_question(
        'what do you want to do today', 'en', memory=None
    )
    assert 'chillin' not in reply.lower()
    assert 'projects i'm working on' not in reply.lower()
    assert 'busy week' not in reply.lower()
    assert 'ai' in reply.lower() or 'help' in reply.lower()
