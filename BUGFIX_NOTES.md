# Gyandeep Saathi — WhatsApp live feedback bugfixes

Date: 2026-09-16

## Fixes

1. **English main menu** — `main_menu(language)` / `topic_chooser(language)` use English row titles when `language=='en'` (HI titles for hi/bho/mai).

2. **School list loop** — Removed broad `menu_schools` aliases (`स्कूल`, `स्कूल सूची`, `school`). Only exact “स्कूल कैसे चुनें?”. Active guided flows run **before** text `match_menu`. Prefer `button_id=school_list`.

3. **Grievance tickets** — Bare “अन्य” no longer substring-matches `menu_others` (so “गलत जानकारी / अन्य…” is not diverted). `gr_other` creates a ticket immediately. `grievance_waiting` tickets on any text. OTP/login/SMS free text (incl. `flow==others`) creates a dummy GS ticket.

4. **Free-text FALLBACK** — Welcome `FALLBACK_HI` / menu-like LLM replies are replaced with short help, topic chooser, demo answer, or grievance ticket — never the welcome wall.

5. **Status ask-id** — `status_ask_id()` has **no** buttons.

6. **Status card buttons** — After a GYAN status card: मुख्य मेनू / शिकायत / आवेदन कैसे करें.

7. **Language switch** — `match_language` detects “switch to maithili/english/hindi/bhojpuri”; always returns `main_menu(new_lang)` so UI language updates.

8. **Director demo Q&A** — Short deterministic answers for RTE 12(1)(c), benefits, documents, deadline, nodal dept, admission notification; live seat/school/application counts → “bot can’t give live counts” + school list / portal links.

Primary files: `handler.py`, `guided.py` (answerer status card logic kept).
