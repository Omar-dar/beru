from src.day_plan import activity_order, is_future_plan, reply_to_day_message


def test_future_gym_then_chill_order():
    text = 'I will go to the gym today, and then eat and chill'
    assert is_future_plan(text)
    assert activity_order(text) == ['gym', 'eat', 'chill']
    reply = reply_to_day_message(text, 'en')
    assert 'gym' in reply.lower()
    assert 'chill' in reply.lower()
    assert 'chill first' not in reply.lower()
    assert 'how did the workout' not in reply.lower()
    assert 'plan' in reply.lower() or 'workout when you go' in reply.lower()


def test_past_chill_and_gym_swedish():
    text = 'Idag chillade jag först och sen gick jag till gymmet'
    assert not is_future_plan(text)
    reply = reply_to_day_message(text, 'sv')
    assert 'chilla' in reply or 'chill' in reply.lower()
    assert 'gym' in reply.lower()
