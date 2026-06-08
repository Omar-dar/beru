# Collected conversations

Full UI ↔ backend handoff: [docs/BERU_UI_BACKEND_HANDOFF.md](../../docs/BERU_UI_BACKEND_HANDOFF.md) (Netlify / guest testing). Each browser `X-Beru-Session-Id` has its own login state; Omar on Mac does not affect phone.

When `BERU_COLLECT_CONVERSATIONS=1` (default on), each chat turn is appended here as:

```text
user: Hello
beru: Hi! Who am I talking to?

user: Sara
beru: Nice to meet you, Sara!
```

One file per browser session: `{session_id}.txt` (from header `X-Beru-Session-Id`).

## Label good vs bad

After review, move files into:

- `good/` — replies you want Beru to learn from
- `bad/` — wrong replies (for corrections / training)

Or add a line in the file: `# label: bad`

## Disable collection

```bash
export BERU_COLLECT_CONVERSATIONS=0
```

## Include Omar's chats

```bash
export BERU_COLLECT_EXCLUDE_OWNER=0
```
