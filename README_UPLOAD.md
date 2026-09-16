# Gyandeep Saathi - GitHub upload pack (guided UX v1.1)

Copy these files into your bot repo (same folder as the WhatsApp app entrypoint), then commit.

## Commit these Python modules (required)

| File | Action | Notes |
|------|--------|--------|
| `session.py` | **ADD** | In-memory session by `wa_id` (language, flow, eligibility, grievance, ticket counter) |
| `guided.py` | **ADD** | Pure guided UX payloads (language, main menu, eligibility, apply, schools, docs, grievance, others) |
| `handler.py` | **REPLACE** | `handle_message(user_text, wa_id=None, button_id=None)` -> dict; guided first, else router+answerer |
| `app.py` | **REPLACE** | Passes `wa_id` / button id; uses `send_guided_reply` for text/buttons/list |
| `whatsapp.py` | **REPLACE** | Adds `send_reply_buttons`, `send_list_message`, `send_guided_reply`; extract returns `id` + title |
| `router.py` | **REPLACE** | Keeps status/GYAN fixes; exports `GENERAL_INFO_RE` for samanya jankari / general enquiry |
| `answerer.py` | **KEEP / REPLACE with this copy** | Status card path for GYAN ids preserved (do not regress) |
| `llm.py` | unchanged | Include only if missing in repo |

## Supporting knowledge files (commit if not already in repo)

| File | Action |
|------|--------|
| `mock_status.json` | KEEP (demo GYAN-2026-1001..1008) |
| `FAQ.txt` | KEEP |
| `intent-prompt.md` | KEEP |
| `system-prompt.md` | KEEP |

## Do not commit

- `__pycache__/`
- `.env` / WhatsApp tokens
- This `README_UPLOAD.md` is optional documentation only

## Suggested git commands

```bash
# from your bot repo root (adjust paths)
cp /path/to/github-upload/{session,guided,handler,app,whatsapp,router,answerer,llm}.py .
# optional knowledge:
# cp /path/to/github-upload/{mock_status.json,FAQ.txt,intent-prompt.md,system-prompt.md} .

git add session.py guided.py handler.py app.py whatsapp.py router.py answerer.py
# git add llm.py mock_status.json FAQ.txt intent-prompt.md system-prompt.md   # if needed

git commit -m "Add Gyandeep Saathi guided WhatsApp UX (language, 7-menu, eligibility, grievance tickets)"
```

## Smoke checks (no WhatsApp API)

```python
from handler import handle_message
from session import reset_all_sessions_for_tests
reset_all_sessions_for_tests()
print(handle_message("hi", "u1")["text"])                 # language prompt
print(handle_message("हिन्दी", "u1")["text"])              # main menu
print(handle_message("avedan stithi", "u1")["text"])     # ask GYAN id
print(handle_message("GYAN-2026-1001", "u1")["text"])    # status card
print(handle_message("samanya jankari", "u1")["text"])   # topic chooser, not FAQ wall
```

Dummy grievance tickets start at `GS-2026-0100` and increment per filing.
