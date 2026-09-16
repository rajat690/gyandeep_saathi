# Gyandeep Saathi — Bugfix / feedback notes

Date: 2026-09-16 (Asia/Calcutta)

## Feedback 4.0 (this pack)

See `FEEDBACK_4.0_CHANGELOG.md` and `Gyandeep_Feedback_4.0_Spec.md`.

Highlights:
1. Language stickiness across all guided flows + LLM SessionLanguage injection.
2. Eligibility pass = two WhatsApp cards (result, then next action).
3. Documents: single localized "list"; Aadhaar timing folded in; no full-list / no separate Aadhaar option.
4. Grievance `gr_refuse` deduped to one label.
5. Free-text eligibility when age + class + income are present.
6. English "Other" row no longer doubles as "Write your own question".
7. Class gate is Class-1 Yes/No (+ follow-up).
8. Apply flow: website intro → link → all-5-steps → YouTube.

## Prior live-feedback fixes (still in tree)

1. **English main menu** — `main_menu(language)` / `topic_chooser(language)` use English row titles when `language=='en'` (HI titles for hi/bho/mai).
2. **School list loop** — Active guided flows run before text `match_menu`; exact school-menu matching.
3. **Grievance tickets** — Bare "अन्य" exact-only for menu_others; OTP/login/SMS free text → ticket.
4. **Free-text FALLBACK** — Welcome/menu-like LLM replies replaced with short help / demo / ticket.
5. **Status ask-id** — no buttons after ask-for-id.
6. **Status card buttons** — Main menu / Grievance / How to apply.
7. **Language switch** — `match_language` + `main_menu(new_lang)`.
8. **Director demo Q&A** — short deterministic answers; no live counts.

Primary files: `handler.py`, `guided.py`, `whatsapp.py`, `answerer.py`.
