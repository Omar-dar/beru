"""Format Tild responses for ChatGPT-style markdown UI (tild-ui)."""

import re
import textwrap

# Training-data leaks that break UI rendering
_TRAINING_MARKERS = re.compile(r'^### (Human|Tild):\s*', re.MULTILINE)

# Detect indented code-like blocks not already in fences
_CODE_BLOCK = re.compile(
    r'(?:^|\n)((?:[ \t]+(?:def |class |import |from |public |private |function |const |let |var ).+(?:\n(?:[ \t]+.+))+))',
    re.MULTILINE,
)

# Whole reply wrapped in ```markdown / ```md (prose, not code)
_PROSE_MARKDOWN_FENCE = re.compile(
    r'^```(?:markdown|md)\s*\n(.*)\n```\s*$',
    re.DOTALL | re.IGNORECASE,
)


def unwrap_prose_markdown_fences(text):
    """
    Deep brain sometimes wraps explanations in ```markdown fences.
    The GUI should render that as normal prose, not a code block.
    """
    if not text:
        return text

    stripped = text.strip()
    match = _PROSE_MARKDOWN_FENCE.match(stripped)
    if match:
        return match.group(1).strip()

    return text


def format_response_for_ui(text):
    """
    Normalize a reply string before sending to tild-ui.
    The UI expects ONE markdown string in ChatResponse.response.
    """
    if not text:
        return text

    text = text.strip()
    text = _TRAINING_MARKERS.sub('', text)
    text = text.replace('\r\n', '\n')
    text = unwrap_prose_markdown_fences(text)

    # Collapse excessive blank lines (keeps markdown readable)
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text


def ensure_code_fences(text, default_language='python'):
    """
    If the model returned indented code without fences, wrap it.
    Only applied when there are clear code signals and no existing fences.
    """
    if not text or '```' in text:
        return text

    match = _CODE_BLOCK.search(text)
    if not match:
        return text

    block = match.group(1).rstrip()
    dedented = textwrap.dedent(block)
    fenced = f'```{default_language}\n{dedented}\n```'
    return text[: match.start(1)] + fenced + text[match.end(1) :]


def format_for_ui(text):
    """Full UI formatting pass: normalize markdown + code fences."""
    text = format_response_for_ui(text)
    text = ensure_code_fences(text)
    return text
