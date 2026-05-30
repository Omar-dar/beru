"""Heuristics to describe uploaded PDF text before answering."""

import re

INCOMPLETE_TAIL_PHRASES = (
    'here is the',
    'here are the',
    'the following',
    'as follows',
    'below is',
    'without using specific',
    'in the next section',
    'see below',
    'correct sequence of operations',
)

FEEDBACK_MARKERS = (
    'not quite correct',
    'not correct',
    'is wrong',
    'incorrect',
    "you've provided",
    'you have provided',
    'your expression',
    'your answer',
    'mixed up',
    "doesn't seem to be correctly",
    'does not seem to be correctly',
    'trying to perform',
    'the expression you',
)

TUTORIAL_MARKERS = (
    'this tutorial',
    'in this lesson',
    'we will learn',
    'step by step',
    'introduction to',
    'lecture notes',
    'chapter ',
)

STRUCTURED_DOC_MARKERS = (
    'profil', 'profile', 'curriculum vitae', 'cv',
    'utbildning', 'education', 'arbetslivserfarenhet', 'work experience',
    'tekniska färdigheter', 'technical skills', 'skills',
    'projekt', 'projects', 'språk', 'languages',
    'github', 'portfolio', 'körkort',
)


def _looks_like_structured_document(text_lower):
    return sum(1 for m in STRUCTURED_DOC_MARKERS if m in text_lower) >= 2


def analyze_document_text(text):
    """Return metadata hints for document Q&A."""
    text_stripped = (text or '').strip()
    text_lower = text_stripped.lower()

    appears_incomplete = False
    incomplete_reason = ''

    if text_stripped and text_stripped[-1] not in '.!?':
        # CVs/resumes often end on a language line or bullet — not a cut-off PDF.
        if not _looks_like_structured_document(text_lower):
            appears_incomplete = True
            incomplete_reason = 'The extracted text does not end with a complete sentence.'

    tail = text_lower[-160:]
    for phrase in INCOMPLETE_TAIL_PHRASES:
        if phrase in tail:
            appears_incomplete = True
            incomplete_reason = (
                'The document ends abruptly, likely before the next section or solution.'
            )
            break

    style = 'general'
    style_detail = ''

    feedback_score = sum(1 for m in FEEDBACK_MARKERS if m in text_lower)
    tutorial_score = sum(1 for m in TUTORIAL_MARKERS if m in text_lower)

    if feedback_score >= 1 and re.search(r'\b(your|you\'ve|you have)\b', text_lower):
        style = 'feedback'
        style_detail = (
            'Corrective feedback on a submitted expression or answer — '
            'not a full standalone tutorial.'
        )
    elif feedback_score >= 2:
        style = 'feedback'
        style_detail = (
            'Corrective feedback on a submitted expression or answer — '
            'not a full standalone tutorial.'
        )
    elif tutorial_score >= 1:
        style = 'tutorial'
        style_detail = 'Instructional or tutorial-style content.'

    return {
        'appears_incomplete': appears_incomplete,
        'incomplete_reason': incomplete_reason,
        'style': style,
        'style_detail': style_detail,
    }


def format_analysis_notes(analysis, language='en'):
    """Short notes injected above raw PDF text for the deep brain."""
    if not analysis:
        return ''

    lines = []

    if analysis['style'] == 'feedback':
        if language == 'sv':
            lines.append(
                'DOKUMENTTYP: Rättnings-/feedbacktext om ett inlämnat uttryck eller svar — '
                'inte en fristående tutorial.'
            )
        else:
            lines.append(
                'DOCUMENT TYPE: Corrective feedback on submitted work — NOT a full standalone tutorial.'
            )
            if analysis['style_detail']:
                lines.append(analysis['style_detail'])
    elif analysis['style'] == 'tutorial':
        if language == 'sv':
            lines.append('DOKUMENTTYP: Tutorial / instruktionsmaterial.')
        else:
            lines.append('DOCUMENT TYPE: Tutorial / instructional material.')
            if analysis['style_detail']:
                lines.append(analysis['style_detail'])

    if analysis['appears_incomplete']:
        reason = analysis['incomplete_reason']
        if language == 'sv':
            lines.append(f'FULLSTÄNDIGHET: Dokumentet verkar ofullständigt. {reason}')
            lines.append(
                'Säg det tydligt i svaret — hitta inte på steg eller innehåll efter där texten slutar.'
            )
        else:
            lines.append(f'COMPLETENESS: Document appears INCOMPLETE. {reason}')
            lines.append(
                'State this clearly in your answer — do NOT invent steps or content after the text cuts off.'
            )

    return '\n'.join(lines)
