# Gyandeep Saathi — GitHub upload pack (Feedback 4.0)

Copy these files into your bot repo (same folder as the WhatsApp app entrypoint), commit, push, then redeploy on Render.

## Commit these Python modules (required)

| File | Action | Notes |
|------|--------|--------|
| `session.py` | ADD/REPLACE | In-memory session by `wa_id` |
| `guided.py` | **REPLACE** | Feedback 4.0 guided UX (language, eligibility split, apply rewrite, docs list, free-text elig) |
| `handler.py` | **REPLACE** | Orchestrates guided flows; passes session language; free-text eligibility |
| `app.py` | REPLACE | Webhook → `handle_message` → `send_guided_reply` |
| `whatsapp.py` | **REPLACE** | Buttons/lists + **multi-card** `replies` support |
| `router.py` | REPLACE | Status/GYAN + `GENERAL_INFO_RE` |
| `answerer.py` | **REPLACE** | Status cards + `generate_reply(..., language=)` SessionLanguage injection |
| `llm.py` | KEEP | Include if missing in repo |

## Supporting knowledge / docs (commit if useful)

| File | Action |
|------|--------|
| `mock_status.json` | KEEP (demo GYAN-2026-1001..1008) |
| `FAQ.txt` | KEEP |
| `intent-prompt.md` | KEEP |
| `system-prompt.md` | **REPLACE** (language stickiness) |
| `FEEDBACK_4.0_CHANGELOG.md` | optional |
| `Gyandeep_Feedback_4.0_Spec.md` | optional product/spec |
| `BUGFIX_NOTES.md` | optional |
| `README_UPLOAD.md` | optional (this file) |

## Do not commit

- `__pycache__/`
- `.env` / WhatsApp tokens / secrets

## Suggested git commands

```bash
# from your bot repo root (adjust paths)
cp /path/to/gyandeep-feedback-4.0-upload/{session,guided,handler,app,whatsapp,router,answerer,llm}.py .
cp /path/to/gyandeep-feedback-4.0-upload/{mock_status.json,FAQ.txt,intent-prompt.md,system-prompt.md} .
# optional docs:
# cp /path/to/gyandeep-feedback-4.0-upload/{FEEDBACK_4.0_CHANGELOG.md,Gyandeep_Feedback_4.0_Spec.md,BUGFIX_NOTES.md} .

git add session.py guided.py handler.py app.py whatsapp.py router.py answerer.py system-prompt.md
git commit -m "Gyandeep Saathi Feedback 4.0: language stickiness, elig split, apply rewrite, docs list"
# then push and redeploy on Render
```

## Smoke checks (no WhatsApp API)

```python
from handler import handle_message
from session import reset_all_sessions_for_tests
reset_all_sessions_for_tests()
print(handle_message("hi", "u1")["text"])              # language prompt
print(handle_message("English", "u1")["text"])         # English main menu
print(handle_message("How to choose school?", "u1")["text"])  # stays English
print(handle_message("", "u1", button_id="menu_apply")["text"])  # website intro
r = handle_message("child age 7 class 1 ews income 2 lakh", "u2")
# may need language first:
reset_all_sessions_for_tests()
handle_message("hi", "u2"); handle_message("हिन्दी", "u2")
r = handle_message("mera beta 7 saal class 1 ews 2 lakh", "u2")
assert "replies" in r  # eligible + next action cards
```

Dummy grievance tickets start at `GS-2026-0100` and increment per filing.

YouTube apply guide: https://youtu.be/bNN9ddilD8c  
Portal: https://gyandeep-rte.bihar.gov.in/
