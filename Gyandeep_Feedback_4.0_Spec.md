# Gyandeep Saathi — Feedback 4.0 Spec

Version: 4.0  
Date: 2026-09-16  
Audience: product + engineering (commit-ready)

## Goals

Fix live WhatsApp UX regressions and rewrite apply/docs/eligibility class flows per stakeholder Feedback 4.0.

## 1. Language stickiness

- After the user selects a language (हिन्दी / English / भोजपुरी / मैथिली), **all** subsequent guided text, reply buttons, and list row titles must stay in that language.
- English → English UI strings. Hindi / Bhojpuri / Maithili → Hindi UI strings (shared Devanagari UI).
- Do not revert to Hindi because a later free-text message is Hinglish or because a sub-flow was hardcoded.
- LLM path: inject `SessionLanguage` and continue in that language until explicit switch.

## 2. Eligibility result = two cards

When the guided (or free-text) check **passes**:

1. **Card A (text only):** eligible summary + portal register link.  
2. **Card B (buttons):** “What next?” / “आगे क्या करना चाहेंगे?” with How to apply | School list | Main menu.

Fail remains a single card with reason + FAQ + Check again / Main menu / Grievance.

## 3–4. Documents help

- Entry shows the **list** content immediately (no “full list”, no separate “बच्चे का आधार कब?”).
- List body (Hindi):

  > जन्म प्रमाण; जाति/आय जहाँ लागू; निवास प्रमाण; अभिभावक आधार; फोटो + मोबाइल।  
  > बच्चे का आधार आवेदन पर ज़रूरी नहीं; बच्चे का आधार आवेदन भरते समय ज़रूरी नहीं, प्रवेश के 3 महीने के अंदर लगाना होता है।

- Follow-up buttons: How to apply | Main menu (localized).

## 5. Grievance dedupe

One category only: **स्कूल ने प्रवेश मना किया** (EN: School denied admission). Do not show a second near-duplicate phrasing.

## 6. Free-text eligibility

If the user message clearly supplies **age**, **class**, and **income/category**, evaluate the same PASS/FAIL rules and answer immediately (split cards on PASS). Do not force the full guided quiz when enough information is present. Incomplete info → guided quiz or short help as today.

Rules (unchanged):

- Age PASS: 6 ≤ age < 8 years (6 to 7y 11m 29d window).  
- Class PASS: Class 1 or Class 2 & 3; FAIL: less than class 1.  
- Income PASS: Weaker (≤ ₹2L) or Disadvantaged (SC/ST/OBC/EBC/Minority ≤ ₹1L).

## 7. Others / write-own dedupe

Main menu English row is a single title: **Other (ask question)** — no second line “Write your own question” on the same row.

## 8. Class question

Replace three-way “which class?” with:

- Prompt: **क्या बच्चा class 1 में दाखिला लेना चाहता है?** (EN: Does the child want admission in Class 1?)  
- Buttons: Yes / No (हाँ / नहीं).  
- Yes → Class 1 PASS → income question.  
- No → follow-up: Class 2 & 3 (PASS) vs Less than class 1 (FAIL).

## 9. Apply flow (“आवेदन कैसे करें”)

1. **Intro:** `आवेदन वेबसाइट के माध्यम से ऑनलाइन किया जाता है।`  
   Buttons: Website link | How to apply (आवेदन कैसे करे) | Main menu  

2. **Website link:** `वेबसाइट लिंक: https://gyandeep-rte.bihar.gov.in/`  
   Buttons: How to apply | Required documents | Main menu  

3. **How to apply:** all five steps in **one** message (not step-by-step):  
   - Step 1: पोर्टल पर पंजीकरण करें और अभिभावक आधार से लॉगिन करें।  
   - Step 2: SMS पर USER ID आएगा। उसे सुरक्षित रखें।  
   - Step 3: फॉर्म भरें और कागज़ात अपलोड करें।  
   - Step 4: अपने प्रखंड में अधिकतम 5 स्कूल चुनें।  
   - Step 5: लॉटरी के बाद स्कूल में जाँच और प्रवेश।  
   Buttons: YouTube guide | Required documents | Main menu  

4. **YouTube:** `https://youtu.be/bNN9ddilD8c`

## Out of scope / preserved

- GYAN mock status cards and post-status buttons  
- Grievance ticket numbering `GS-2026-****`  
- Director-demo short FAQ answers (no live seat counts)  

## Deploy

Upload this pack into the GitHub bot repo and redeploy the Render web service. Do not commit `.env` or WhatsApp tokens.
