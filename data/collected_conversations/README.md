# Collected conversations

Full UI ↔ backend handoff: [docs/TILD_UI_BACKEND_HANDOFF.md](../../docs/TILD_UI_BACKEND_HANDOFF.md) (Netlify / guest testing). Each browser `X-Tild-Session-Id` has its own login state; Omar on Mac does not affect phone.

When `TILD_COLLECT_CONVERSATIONS=1` (default on), each chat turn is appended here as:

```text
user: Hello
tild: Hi! Who am I talking to?

user: Sara
tild: Nice to meet you, Sara!
```

One file per browser session: `{session_id}.txt` (from header `X-Tild-Session-Id`).

## Label good vs bad

After review, move files into:

- `good/` — replies you want Tild to learn from
- `bad/` — wrong replies (for corrections / training)

Or add a line in the file: `# label: bad`

## Disable collection

```bash
export TILD_COLLECT_CONVERSATIONS=0
```

## Include Omar's chats

```bash
export TILD_COLLECT_EXCLUDE_OWNER=0
```
