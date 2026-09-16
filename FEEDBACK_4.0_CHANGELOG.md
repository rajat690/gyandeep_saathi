# Feedback 4.0 Changelog — Gyandeep Saathi

Date: 2026-09-16 (Asia/Calcutta)

Maps each Feedback 4.0 item to code/doc changes in this upload pack.

| # | Feedback item | What changed |
|---|---------------|--------------|
| 1 | **Language stickiness** — after language select, bot must not revert to Hindi; option/button/list titles in selected language (Hindi titles when Hindi selected) | All guided payloads (`eligibility_*`, `apply_*`, `schools_*`, `docs_*`, `grievance_*`, `status_*`, demo answers) take `language` and localize EN vs HI (hi/bho/mai share Hindi UI). `handler.py` passes session language everywhere. `system-prompt.md` + `answerer.generate_reply(..., language=)` inject `SessionLanguage` so LLM does not revert. |
| 2 | **Eligible message split** — eligible result and next-action question in different cards | `eligibility_pass_result()` returns `{"replies": [card1, card2]}`. `whatsapp.send_guided_reply` sends each card as a separate WhatsApp message. |
| 3 | **School/docs list** — remove "full list"; rename choti/small list to **"list"** | Documents entry shows the list directly. Removed `पूरी लिस्ट` and renamed short list to `लिस्ट` / `List`. (Applies to documents help UI per feedback screenshots.) |
| 4 | **Documents** — remove "बच्चे का आधार कब?"; fold Aadhaar timing into list text | `docs_list()` text includes birth/caste/income/residence/guardian Aadhaar/photo+mobile **and** Aadhaar-not-required-at-apply / submit within 3 months of admission. Legacy `docs_aadhaar` / `docs_full` redirect to the same list. |
| 5 | **Deduplicate grievance** — remove duplicate "स्कूल ने प्रवेश मना किया" vs "स्कूल ने प्रवेश से मना किया" | `GRIEVANCE_ROWS` `gr_refuse` title and full both set to `स्कूल ने प्रवेश मना किया`. English row: `School denied admission`. |
| 6 | **Free-text eligibility** — if user gives all necessary info, check rules and answer; don't force full quiz | `extract_eligibility_facts` + `try_free_text_eligibility` parse age/class/income from free text. Used before quiz start and in LLM/others fallback. Enough facts → pass (split cards) or fail with reason. |
| 7 | **Double answers / Other** — "Other (ask question)" / "Write your own question" showing twice | Removed description from English `menu_others` row (title alone). Topic chooser keeps a single `Type your question` write row, not duplicated with Others description. |
| 8 | **Class question** — "Kya bachha class 1 me dakhila lena chahta hai" with Yes/No | `eligibility_class()` Yes/No. Yes → Class 1 PASS → income. No → `eligibility_class_followup()` Class 2&3 (PASS) vs Less than class 1 (FAIL). Prior PASS/FAIL logic preserved. |
| 9 | **Apply flow rewrite** ("आवेदन कैसे करें") | `apply_start`: online-via-website + Website link / How to apply / Main menu. Website → portal URL + how to apply / Required documents / Main menu. How to apply → **all 5 steps in one message** + YouTube / Required documents / Main menu. YouTube → `https://youtu.be/bNN9ddilD8c`. Step-by-step kadam/aage removed from primary UX. |

## Primary files
- `guided.py`, `handler.py`, `whatsapp.py`, `answerer.py`, `system-prompt.md`

## Preserved (unless conflicting)
- Status card / GYAN mock lookup
- Grievance ticket IDs (`GS-2026-0100+`)
- Director-demo short answers
