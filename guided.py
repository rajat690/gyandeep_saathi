"""Pure guided-UX logic for Gyandeep Saathi WhatsApp flows.

Returns reply payloads:
  { "text": str, "buttons": [{"id","title"}, ...]?, "list_sections": [...]? ,
    "list_button_label": str? }
  or multi-card: { "replies": [ <payload>, ... ] }

Button/list titles stay within WhatsApp limits (reply 20, list row 24).
Matching also accepts full product copy so typed replies still work.

Feedback 4.0: language stickiness (en vs hi/bho/mai), split eligibility cards,
docs list rewrite, apply flow rewrite, class Yes/No, free-text eligibility.
"""

from __future__ import annotations

import re
from typing import Any

from session import next_ticket_id

PORTAL = "https://gyandeep-rte.bihar.gov.in/"
PORTAL_FAQ = "https://gyandeep-rte.bihar.gov.in/faq"
PORTAL_SCHOOLS = "https://gyandeep-rte.bihar.gov.in/registration-school-details"
YOUTUBE_APPLY = "https://youtu.be/bNN9ddilD8c"

# Full product copy (for matching typed replies)
MENU_ELIG_FULL = "क्या बच्चा फॉर्म भर सकता है?"
MENU_APPLY = "आवेदन कैसे करें?"
MENU_STATUS = "आवेदन स्थिति"
MENU_SCHOOLS = "स्कूल कैसे चुनें?"
MENU_DOCS = "कागज़ात मदद"
MENU_GRIEVANCE = "शिकायत"
MENU_OTHERS_FULL = "अन्य (अपना सवाल लिखें)"
MENU_MAIN = "मुख्य मेनू"
MENU_LANG = "भाषा बदलें"

# WA-safe titles (list row <=24, reply <=20)
MENU_ELIG = "बच्चा फॉर्म भर सकता है?"  # 23
MENU_OTHERS = "अन्य (अपना सवाल)"  # 16

# English menu row titles (WA limits)
MENU_ELIG_EN = "Can child apply?"
MENU_APPLY_EN = "How to apply?"
MENU_STATUS_EN = "Application status"
MENU_SCHOOLS_EN = "How to choose school?"
MENU_DOCS_EN = "Documents help"
MENU_GRIEVANCE_EN = "Grievance"
MENU_OTHERS_EN = "Other (ask question)"
MENU_LANG_EN = "Change language"
MENU_MAIN_EN = "Main menu"
WRITE_OWN_EN = "Type your question"

BTN_LANG_HI = "हिन्दी"
BTN_LANG_EN = "English"
BTN_LANG_BHO = "भोजपुरी"
BTN_LANG_MAI = "मैथिली"

YES_HI = "हाँ"
NO_HI = "नहीं"
YES_EN = "Yes"
NO_EN = "No"
AGE_YES = "हाँ, इस उम्र में है"  # 19
AGE_NO = "नहीं, इस उम्र में नहीं"  # 22 list OK
AGE_UNSURE = "पक्का नहीं"
AGE_YES_EN = "Yes, in age range"
AGE_NO_EN = "No, not in range"
AGE_UNSURE_EN = "Not sure"

CLASS_1 = "Class 1"
CLASS_2_3 = "Class 2 & 3"
CLASS_LT1 = "Less than class 1"

INCOME_EWS_FULL = "कमजोर वर्ग (आय ₹2 लाख तक)"
INCOME_DG_FULL = "वंचित वर्ग (SC/ST/OBC/EBC/अल्पसंख्यक, आय ₹1 लाख तक)"
INCOME_NO = "इनमें से नहीं"
INCOME_EWS = "कमजोर वर्ग (आय 2 लाख)"  # 21
INCOME_DG = "वंचित वर्ग (आय 1 लाख)"  # 21
INCOME_EWS_EN = "Weaker (income 2L)"
INCOME_DG_EN = "DG (income 1L)"
INCOME_NO_EN = "Neither / over"

# Apply flow (Feedback 4.0)
APPLY_WEBSITE = "वेबसाइट लिंक"
APPLY_WEBSITE_EN = "Website link"
APPLY_HOW = "आवेदन कैसे करे"
APPLY_HOW_EN = "How to apply"
APPLY_YOUTUBE = "YouTube गाइड"
APPLY_YOUTUBE_EN = "YouTube guide"
DOCS_REQUIRED = "आवश्यक दस्तावेज"
DOCS_REQUIRED_EN = "Required documents"

# Legacy apply labels (still matched for typed replies)
APPLY_STEPS = "कदम-कदम बताओ"
APPLY_PORTAL = "पोर्टल लिंक"
APPLY_NEXT = "हो गया/आगे"
APPLY_PROBLEM = "समस्या"

SCHOOL_LIST = "स्कूल सूची खोलो"
SCHOOL_DIST = "दूरी का नियम"
SCHOOL_LIST_SHORT = "स्कूल सूची"
SCHOOL_LIST_EN = "Open school list"
SCHOOL_DIST_EN = "Distance rule"
SCHOOL_LIST_SHORT_EN = "School list"

# Docs (Feedback 4.0): single "list", no full list / no separate aadhaar
DOCS_LIST = "लिस्ट"
DOCS_LIST_EN = "List"
DOCS_SHORT = "लिस्ट"  # alias for matching old "छोटी लिस्ट"
DOCS_FULL = "पूरी लिस्ट (पोर्टल FAQ)"
DOCS_FULL_BTN = "पूरी लिस्ट"
DOCS_AADHAAR = "बच्चे का आधार कब?"

RETRY_ELIG = "दोबारा जाँचें"
RETRY_ELIG_EN = "Check again"
WRITE_OWN = "अपना सवाल लिखें"
WRITE_OWN_LONG = "अपना सवाल खुद लिखें"

DOCS_LIST_TEXT_HI = (
    "जन्म प्रमाण; जाति/आय जहाँ लागू; निवास प्रमाण; अभिभावक आधार; फोटो + मोबाइल।\n"
    "बच्चे का आधार आवेदन पर ज़रूरी नहीं; बच्चे का आधार आवेदन भरते समय ज़रूरी नहीं, "
    "प्रवेश के 3 महीने के अंदर लगाना होता है।"
)
DOCS_LIST_TEXT_EN = (
    "Birth proof; caste/income where applicable; residence proof; "
    "guardian Aadhaar; photo + mobile.\n"
    "Child's Aadhaar is not required on the application; not needed while filling "
    "the form — submit within 3 months of admission."
)

_APPLY_ALL_STEPS_HI = (
    "Step 1: पोर्टल पर पंजीकरण करें और अभिभावक आधार से लॉगिन करें।\n"
    "Step 2: SMS पर USER ID आएगा। उसे सुरक्षित रखें।\n"
    "Step 3: फॉर्म भरें और कागज़ात अपलोड करें।\n"
    "Step 4: अपने प्रखंड में अधिकतम 5 स्कूल चुनें।\n"
    "Step 5: लॉटरी के बाद स्कूल में जाँच और प्रवेश।"
)
_APPLY_ALL_STEPS_EN = (
    "Step 1: Register on the portal and log in with guardian Aadhaar.\n"
    "Step 2: You will get a USER ID by SMS. Keep it safe.\n"
    "Step 3: Fill the form and upload documents.\n"
    "Step 4: Choose up to 5 schools in your block.\n"
    "Step 5: After lottery, verification and admission at school."
)

# title and full must match for gr_refuse (Feedback 4.0 dedupe)
GRIEVANCE_ROWS = [
    ("gr_portal", "पोर्टल/लॉगिन/OTP समस्या", "पोर्टल / लॉगिन / OTP समस्या"),
    ("gr_sms", "SMS/USER ID नहीं मिला", "SMS / USER ID नहीं मिला"),
    ("gr_docs", "कागज़ात / जाँच अटकी", "कागज़ात / जाँच अटकी"),
    ("gr_allot", "स्कूल आवंटन/लॉटरी समस्या", "स्कूल आवंटन / लॉटरी समस्या"),
    ("gr_refuse", "स्कूल ने प्रवेश मना किया", "स्कूल ने प्रवेश मना किया"),
    ("gr_elig", "पात्रता / आय-वर्ग भ्रम", "पात्रता / आय-वर्ग भ्रम"),
    ("gr_other", "गलत जानकारी / अन्य", "गलत जानकारी / अन्य पोर्टल समस्या"),
    ("gr_free", WRITE_OWN_LONG, "अपना सवाल खुद लिखें (free text)"),
]

GRIEVANCE_ROWS_EN = [
    ("gr_portal", "Portal/login/OTP issue", "Portal / login / OTP problem"),
    ("gr_sms", "SMS/USER ID missing", "Did not get SMS / USER ID"),
    ("gr_docs", "Docs / verification stuck", "Documents / verification stuck"),
    ("gr_allot", "Allotment/lottery issue", "School allotment / lottery issue"),
    ("gr_refuse", "School denied admission", "School denied admission"),
    ("gr_elig", "Eligibility / income doubt", "Eligibility / income-category doubt"),
    ("gr_other", "Wrong info / other", "Wrong information / other portal issue"),
    ("gr_free", WRITE_OWN_EN, "Type your own question (free text)"),
]


def _en(language: str | None) -> bool:
    return (language or "").strip().lower() == "en"


def _btn(bid: str, title: str) -> dict[str, str]:
    return {"id": bid, "title": title[:20]}


def _row(rid: str, title: str, desc: str = "") -> dict[str, str]:
    out = {"id": rid, "title": title[:24]}
    if desc:
        out["description"] = desc[:72]
    return out


def _reply(text: str, buttons: list[dict[str, str]] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"text": text}
    if buttons:
        payload["buttons"] = buttons[:3]
    return payload


def _multi(*cards: dict[str, Any]) -> dict[str, Any]:
    return {"replies": list(cards)}


def _list_reply(
    text: str,
    sections: list[dict[str, Any]],
    button_label: str = "विकल्प चुनें",
) -> dict[str, Any]:
    return {
        "text": text,
        "list_sections": sections,
        "list_button_label": button_label[:20],
    }


def _main_title(language: str | None) -> str:
    return MENU_MAIN_EN if _en(language) else MENU_MAIN


def _apply_title(language: str | None) -> str:
    return MENU_APPLY_EN[:20] if _en(language) else "आवेदन कैसे करें?"


def _grievance_title(language: str | None) -> str:
    return MENU_GRIEVANCE_EN if _en(language) else MENU_GRIEVANCE


def _status_title(language: str | None) -> str:
    return MENU_STATUS_EN[:20] if _en(language) else MENU_STATUS


def _docs_title(language: str | None) -> str:
    return MENU_DOCS_EN[:20] if _en(language) else MENU_DOCS


def language_prompt() -> dict[str, Any]:
    return _list_reply(
        "नमस्कार। मैं ज्ञानदीप साथी हूँ।\nकृपया भाषा चुनें / Choose language",
        [
            {
                "title": "Language",
                "rows": [
                    _row("lang_hi", BTN_LANG_HI),
                    _row("lang_en", BTN_LANG_EN),
                    _row("lang_bho", BTN_LANG_BHO),
                    _row("lang_mai", BTN_LANG_MAI),
                ],
            }
        ],
        "भाषा चुनें",
    )


def _menu_rows(language: str | None) -> list[dict[str, str]]:
    if _en(language):
        # No description on menu_others — avoids double "Other" / "Write your own"
        return [
            _row("menu_elig", MENU_ELIG_EN, "Eligibility check"),
            _row("menu_apply", MENU_APPLY_EN),
            _row("menu_status", MENU_STATUS_EN),
            _row("menu_schools", MENU_SCHOOLS_EN),
            _row("menu_docs", MENU_DOCS_EN),
            _row("menu_grievance", MENU_GRIEVANCE_EN),
            _row("menu_others", MENU_OTHERS_EN),
            _row("menu_lang", MENU_LANG_EN),
        ]
    return [
        _row("menu_elig", MENU_ELIG, MENU_ELIG_FULL),
        _row("menu_apply", MENU_APPLY),
        _row("menu_status", MENU_STATUS),
        _row("menu_schools", MENU_SCHOOLS),
        _row("menu_docs", MENU_DOCS),
        _row("menu_grievance", MENU_GRIEVANCE),
        _row("menu_others", MENU_OTHERS, MENU_OTHERS_FULL),
        _row("menu_lang", MENU_LANG),
    ]


def main_menu(language: str | None = None) -> dict[str, Any]:
    if _en(language):
        text = "Hello. I am Gyandeep Saathi.\nWhat do you want to do?"
        label = "Open menu"
        section_title = "Menu"
    else:
        text = "नमस्कार। मैं ज्ञानदीप साथी हूँ।\nआप क्या करना चाहते हैं?"
        label = "मेनू खोलें"
        section_title = "मेनू"
    return _list_reply(
        text,
        [{"title": section_title, "rows": _menu_rows(language)}],
        label,
    )


def topic_chooser(language: str | None = None) -> dict[str, Any]:
    """General enquiry / samanya jankari: topic buttons, never FAQ wall."""
    if _en(language):
        text = "You can type your question.\nOr pick a topic below:"
        label = "Pick a topic"
        section_title = "Topics"
        rows = [
            _row("menu_elig", MENU_ELIG_EN, "Eligibility check"),
            _row("menu_apply", MENU_APPLY_EN),
            _row("menu_status", MENU_STATUS_EN),
            _row("menu_schools", MENU_SCHOOLS_EN),
            _row("menu_docs", MENU_DOCS_EN),
            _row("menu_grievance", MENU_GRIEVANCE_EN),
            _row("menu_write", WRITE_OWN_EN),
        ]
    else:
        text = "आप अपना सवाल लिख सकते हैं।\nया नीचे से विषय चुनें:"
        label = "विषय चुनें"
        section_title = "विषय"
        rows = [
            _row("menu_elig", MENU_ELIG, MENU_ELIG_FULL),
            _row("menu_apply", MENU_APPLY),
            _row("menu_status", MENU_STATUS),
            _row("menu_schools", MENU_SCHOOLS),
            _row("menu_docs", MENU_DOCS),
            _row("menu_grievance", MENU_GRIEVANCE),
            _row("menu_write", WRITE_OWN),
        ]
    return _list_reply(text, [{"title": section_title, "rows": rows}], label)


def eligibility_gate(language: str | None = None) -> dict[str, Any]:
    if _en(language):
        return _reply(
            "Do you want to check if your child can apply on Gyandeep / RTE?",
            [_btn("elig_yes", YES_EN), _btn("elig_no", NO_EN)],
        )
    return _reply(
        "क्या आप जाँचना चाहते हैं कि आपका बच्चा ज्ञानदीप / आरटीई में फॉर्म भर सकता है?",
        [_btn("elig_yes", YES_HI), _btn("elig_no", NO_HI)],
    )


def eligibility_age(language: str | None = None) -> dict[str, Any]:
    if _en(language):
        return _list_reply(
            "What is the child's age?\n"
            "Usually age must be from 6 years to 7 years 11 months 29 days.",
            [
                {
                    "title": "Age",
                    "rows": [
                        _row("age_yes", AGE_YES_EN),
                        _row("age_no", AGE_NO_EN),
                        _row("age_unsure", AGE_UNSURE_EN),
                    ],
                }
            ],
            "Choose age",
        )
    return _list_reply(
        "बच्चे की उम्र क्या है?\n"
        "आमतौर पर उम्र 6 साल से 7 साल 11 महीने 29 दिन तक होनी चाहिए।",
        [
            {
                "title": "उम्र",
                "rows": [
                    _row("age_yes", AGE_YES),
                    _row("age_no", AGE_NO),
                    _row("age_unsure", AGE_UNSURE),
                ],
            }
        ],
        "उम्र चुनें",
    )


def eligibility_age_typed_prompt(language: str | None = None) -> dict[str, Any]:
    if _en(language):
        return _reply("Please type age in years (or date of birth).")
    return _reply("उम्र साल में लिखें (या जन्म तिथि)।")


def eligibility_class(language: str | None = None) -> dict[str, Any]:
    """Feedback 4.0: Class 1 Yes/No instead of 3-way class picker."""
    if _en(language):
        return _reply(
            "Does the child want admission in Class 1?",
            [_btn("class_yes", YES_EN), _btn("class_no", NO_EN)],
        )
    return _reply(
        "क्या बच्चा class 1 में दाखिला लेना चाहता है?",
        [_btn("class_yes", YES_HI), _btn("class_no", NO_HI)],
    )


def eligibility_class_followup(language: str | None = None) -> dict[str, Any]:
    """If not Class 1: Class 2&3 (PASS) vs less than class 1 (FAIL)."""
    if _en(language):
        return _reply(
            "Which class does the child want admission in?",
            [
                _btn("class_2_3", CLASS_2_3),
                _btn("class_lt1", CLASS_LT1),
            ],
        )
    return _reply(
        "बच्चा किस कक्षा में दाखिला लेना चाहता है?",
        [
            _btn("class_2_3", CLASS_2_3),
            _btn("class_lt1", CLASS_LT1),
        ],
    )


def eligibility_income(language: str | None = None) -> dict[str, Any]:
    if _en(language):
        return _list_reply(
            "Which group does the family fall in?",
            [
                {
                    "title": "Group",
                    "rows": [
                        _row("income_ews", INCOME_EWS_EN, "Weaker section, income up to ₹2 lakh"),
                        _row("income_dg", INCOME_DG_EN, "SC/ST/OBC/EBC/Minority, income up to ₹1 lakh"),
                        _row("income_no", INCOME_NO_EN),
                    ],
                }
            ],
            "Choose group",
        )
    return _list_reply(
        "परिवार किस समूह में आता है?",
        [
            {
                "title": "समूह",
                "rows": [
                    _row("income_ews", INCOME_EWS, INCOME_EWS_FULL),
                    _row("income_dg", INCOME_DG, INCOME_DG_FULL),
                    _row("income_no", INCOME_NO),
                ],
            }
        ],
        "समूह चुनें",
    )


def eligibility_pass_result(language: str | None = None) -> dict[str, Any]:
    """Eligible message and next-action question in separate cards (Feedback 4.0)."""
    if _en(language):
        card1 = _reply(
            "Based on your answers, the child appears eligible to apply.\n"
            f"Next step: register on the portal.\n{PORTAL}"
        )
        card2 = _reply(
            "What would you like to do next?",
            [
                _btn("menu_apply", MENU_APPLY_EN[:20]),
                _btn("menu_schools", SCHOOL_LIST_SHORT_EN[:20]),
                _btn("menu_main", MENU_MAIN_EN[:20]),
            ],
        )
    else:
        card1 = _reply(
            "आपके जवाब के हिसाब से बच्चा फॉर्म के लिए योग्य दिखता है।\n"
            f"अगला कदम: पोर्टल पर पंजीकरण।\n{PORTAL}"
        )
        card2 = _reply(
            "आगे क्या करना चाहेंगे?",
            [
                _btn("menu_apply", "आवेदन कैसे करें?"),
                _btn("menu_schools", SCHOOL_LIST_SHORT),
                _btn("menu_main", MENU_MAIN),
            ],
        )
    return _multi(card1, card2)


def eligibility_fail_result(reason: str, language: str | None = None) -> dict[str, Any]:
    if _en(language):
        return _reply(
            "Based on your answers, eligibility does not appear complete yet.\n"
            f"Reason: {reason}\n{PORTAL_FAQ}",
            [
                _btn("elig_retry", RETRY_ELIG_EN),
                _btn("menu_main", MENU_MAIN_EN[:20]),
                _btn("menu_grievance", MENU_GRIEVANCE_EN),
            ],
        )
    return _reply(
        "आपके जवाब के हिसाब से अभी पात्रता पूरी नहीं दिखती।\n"
        f"कारण: {reason}\n{PORTAL_FAQ}",
        [
            _btn("elig_retry", RETRY_ELIG),
            _btn("menu_main", MENU_MAIN),
            _btn("menu_grievance", MENU_GRIEVANCE),
        ],
    )


def eligibility_declined(language: str | None = None) -> dict[str, Any]:
    if _en(language):
        return _reply(
            "Okay. What would you like to do next?",
            [
                _btn("menu_apply", MENU_APPLY_EN[:20]),
                _btn("menu_status", MENU_STATUS_EN[:20]),
                _btn("menu_main", MENU_MAIN_EN[:20]),
            ],
        )
    return _reply(
        "ठीक है। आगे क्या करना चाहेंगे?",
        [
            _btn("menu_apply", "आवेदन कैसे करें?"),
            _btn("menu_status", MENU_STATUS),
            _btn("menu_main", MENU_MAIN),
        ],
    )


def apply_start(language: str | None = None) -> dict[str, Any]:
    """Feedback 4.0: online-via-website intro + Website | How to apply | Main menu."""
    if _en(language):
        return _reply(
            "Application is done online through the website.",
            [
                _btn("apply_website", APPLY_WEBSITE_EN),
                _btn("apply_how", APPLY_HOW_EN),
                _btn("menu_main", MENU_MAIN_EN[:20]),
            ],
        )
    return _reply(
        "आवेदन वेबसाइट के माध्यम से ऑनलाइन किया जाता है।",
        [
            _btn("apply_website", APPLY_WEBSITE),
            _btn("apply_how", APPLY_HOW),
            _btn("menu_main", MENU_MAIN),
        ],
    )


def apply_website(language: str | None = None) -> dict[str, Any]:
    if _en(language):
        return _reply(
            f"Website link: {PORTAL}",
            [
                _btn("apply_how", APPLY_HOW_EN),
                _btn("menu_docs", DOCS_REQUIRED_EN[:20]),
                _btn("menu_main", MENU_MAIN_EN[:20]),
            ],
        )
    return _reply(
        f"वेबसाइट लिंक: {PORTAL}",
        [
            _btn("apply_how", APPLY_HOW),
            _btn("menu_docs", DOCS_REQUIRED[:20]),
            _btn("menu_main", MENU_MAIN),
        ],
    )


def apply_how_all_steps(language: str | None = None) -> dict[str, Any]:
    """All 5 steps in one answer (no kadam-by-kadam)."""
    if _en(language):
        return _reply(
            _APPLY_ALL_STEPS_EN,
            [
                _btn("apply_youtube", APPLY_YOUTUBE_EN),
                _btn("menu_docs", DOCS_REQUIRED_EN[:20]),
                _btn("menu_main", MENU_MAIN_EN[:20]),
            ],
        )
    return _reply(
        _APPLY_ALL_STEPS_HI,
        [
            _btn("apply_youtube", APPLY_YOUTUBE),
            _btn("menu_docs", DOCS_REQUIRED[:20]),
            _btn("menu_main", MENU_MAIN),
        ],
    )


def apply_youtube(language: str | None = None) -> dict[str, Any]:
    if _en(language):
        return _reply(
            f"YouTube link for application guide:\n{YOUTUBE_APPLY}",
            [
                _btn("menu_docs", DOCS_REQUIRED_EN[:20]),
                _btn("apply_how", APPLY_HOW_EN),
                _btn("menu_main", MENU_MAIN_EN[:20]),
            ],
        )
    return _reply(
        f"आवेदन गाइड YouTube लिंक:\n{YOUTUBE_APPLY}",
        [
            _btn("menu_docs", DOCS_REQUIRED[:20]),
            _btn("apply_how", APPLY_HOW),
            _btn("menu_main", MENU_MAIN),
        ],
    )


# Back-compat aliases used by older handlers / typed "पोर्टल लिंक"
def apply_portal_only(language: str | None = None) -> dict[str, Any]:
    return apply_website(language)


def apply_step(n: int, language: str | None = None) -> dict[str, Any]:
    """Deprecated step-by-step; Feedback 4.0 shows all steps at once."""
    return apply_how_all_steps(language)


def schools_start(language: str | None = None) -> dict[str, Any]:
    if _en(language):
        return _reply(
            "Choose schools from your block. Maximum 5 schools. Put the nearest first.",
            [
                _btn("school_list", SCHOOL_LIST_EN),
                _btn("school_dist", SCHOOL_DIST_EN),
                _btn("menu_main", MENU_MAIN_EN[:20]),
            ],
        )
    return _reply(
        "स्कूल प्रखंड से चुनें। अधिकतम 5 स्कूल। पास वाला पहले रखें।",
        [
            _btn("school_list", SCHOOL_LIST),
            _btn("school_dist", SCHOOL_DIST),
            _btn("menu_main", MENU_MAIN),
        ],
    )


def schools_list(language: str | None = None) -> dict[str, Any]:
    if _en(language):
        return _reply(
            f"School list (district then block):\n{PORTAL_SCHOOLS}\n"
            "Do not guess vacant seats; check the portal.",
            [
                _btn("school_dist", SCHOOL_DIST_EN),
                _btn("menu_main", MENU_MAIN_EN[:20]),
            ],
        )
    return _reply(
        f"स्कूल सूची (जिला फिर प्रखंड):\n{PORTAL_SCHOOLS}\n"
        "खाली सीट का अनुमान न लगाएँ; पोर्टल देखें।",
        [_btn("school_dist", SCHOOL_DIST), _btn("menu_main", MENU_MAIN)],
    )


def schools_distance(language: str | None = None) -> dict[str, Any]:
    if _en(language):
        return _reply(
            "Distance bands: 0-1 km, 1-3 km, 3-6 km.\nChoose the nearer school first.",
            [
                _btn("school_list", SCHOOL_LIST_EN),
                _btn("menu_main", MENU_MAIN_EN[:20]),
            ],
        )
    return _reply(
        "दूरी बैंड: 0-1 किमी, 1-3 किमी, 3-6 किमी।\nपास वाला स्कूल पहले चुनें।",
        [_btn("school_list", SCHOOL_LIST), _btn("menu_main", MENU_MAIN)],
    )


def docs_list(language: str | None = None) -> dict[str, Any]:
    """Documents list with Aadhaar timing folded in (Feedback 4.0)."""
    if _en(language):
        return _reply(
            DOCS_LIST_TEXT_EN,
            [
                _btn("menu_apply", MENU_APPLY_EN[:20]),
                _btn("menu_main", MENU_MAIN_EN[:20]),
            ],
        )
    return _reply(
        DOCS_LIST_TEXT_HI,
        [
            _btn("menu_apply", "आवेदन कैसे करें?"),
            _btn("menu_main", MENU_MAIN),
        ],
    )


def docs_start(language: str | None = None) -> dict[str, Any]:
    """Open documents help: show list directly (no full-list / aadhaar options)."""
    return docs_list(language)


def docs_short(language: str | None = None) -> dict[str, Any]:
    return docs_list(language)


def docs_full(language: str | None = None) -> dict[str, Any]:
    """Legacy full-list path → same list content (FAQ link no longer primary)."""
    return docs_list(language)


def docs_aadhaar(language: str | None = None) -> dict[str, Any]:
    """Legacy aadhaar option → folded into documents list."""
    return docs_list(language)


def grievance_menu(language: str | None = None) -> dict[str, Any]:
    rows_src = GRIEVANCE_ROWS_EN if _en(language) else GRIEVANCE_ROWS
    if _en(language):
        return _list_reply(
            "What is the grievance about?",
            [
                {
                    "title": "Grievance",
                    "rows": [_row(rid, title, full) for rid, title, full in rows_src],
                }
            ],
            "Choose category",
        )
    return _list_reply(
        "शिकायत किस बारे में है?",
        [
            {
                "title": "शिकायत",
                "rows": [_row(rid, title, full) for rid, title, full in rows_src],
            }
        ],
        "श्रेणी चुनें",
    )


def grievance_ask_free(language: str | None = None) -> dict[str, Any]:
    if _en(language):
        return _reply("Please describe your problem in 1-2 lines.")
    return _reply("अपनी समस्या 1-2 पंक्ति में लिखें।")


def grievance_ticket(
    category_label: str,
    ticket_id: str | None = None,
    language: str | None = None,
) -> dict[str, Any]:
    tid = ticket_id or next_ticket_id()
    if _en(language):
        return _reply(
            "Your grievance has been registered.\n"
            f"Ticket: {tid}\n"
            f"Category: {category_label}\n"
            "Official help: rtebiharhelp@gmail.com\n"
            "Phone: 18003454417 / 14417 (10 AM-5 PM, Mon-Sat)",
            [
                _btn("menu_status", MENU_STATUS_EN[:20]),
                _btn("menu_main", MENU_MAIN_EN[:20]),
            ],
        )
    return _reply(
        "आपकी शिकायत दर्ज हो गई।\n"
        f"टिकट: {tid}\n"
        f"श्रेणी: {category_label}\n"
        "आधिकारिक मदद: rtebiharhelp@gmail.com\n"
        "फोन: 18003454417 / 14417 (10 AM-5 PM, सोम-शनि)",
        [_btn("menu_status", MENU_STATUS), _btn("menu_main", MENU_MAIN)],
    )


def status_ask_id(language: str | None = None) -> dict[str, Any]:
    if _en(language):
        return _reply("Please send your application number (example: GYAN-2026-1001).")
    return _reply(
        "कृपया अपना आवेदन संख्या भेजें (उदाहरण: GYAN-2026-1001)।",
    )


def status_card_with_buttons(card_text: str, language: str | None = None) -> dict[str, Any]:
    if _en(language):
        return _reply(
            card_text,
            [
                _btn("menu_main", MENU_MAIN_EN[:20]),
                _btn("menu_grievance", MENU_GRIEVANCE_EN),
                _btn("menu_apply", MENU_APPLY_EN[:20]),
            ],
        )
    return _reply(
        card_text,
        [
            _btn("menu_main", MENU_MAIN),
            _btn("menu_grievance", MENU_GRIEVANCE),
            _btn("menu_apply", "आवेदन कैसे करें"),
        ],
    )


def others_free_prompt(language: str | None = None) -> dict[str, Any]:
    if _en(language):
        return _reply(
            "Type your question. Or open the main menu to pick a topic.",
            [
                _btn("menu_main", MENU_MAIN_EN[:20]),
                _btn("menu_elig", "Eligibility"),
            ],
        )
    return _reply(
        "अपना सवाल लिखें। या विषय चुनने के लिए मुख्य मेनू खोलें।",
        [_btn("menu_main", MENU_MAIN), _btn("menu_elig", "पात्रता जाँच")],
    )


def short_help_reply(language: str | None = None) -> dict[str, Any]:
    if _en(language):
        return _reply(
            "Please pick a topic from the menu, or type a short question.\n"
            f"Portal: {PORTAL}",
            [
                _btn("menu_main", MENU_MAIN_EN[:20]),
                _btn("menu_grievance", MENU_GRIEVANCE_EN),
                _btn("menu_status", MENU_STATUS_EN[:20]),
            ],
        )
    return _reply(
        "कृपया मेनू से विषय चुनें, या छोटा सवाल लिखें।\n"
        f"पोर्टल: {PORTAL}",
        [
            _btn("menu_main", MENU_MAIN),
            _btn("menu_grievance", MENU_GRIEVANCE),
            _btn("menu_status", MENU_STATUS),
        ],
    )


_NORM_SPACE = re.compile(r"\s+")


def _norm(s: str) -> str:
    return _NORM_SPACE.sub(" ", (s or "").strip().lower())


_LANG_NAME_TO_CODE = {
    "english": "en",
    "eng": "en",
    "hindi": "hi",
    "hin": "hi",
    "bhojpuri": "bho",
    "maithili": "mai",
    "हिन्दी": "hi",
    "हिंदी": "hi",
    "भोजपुरी": "bho",
    "मैथिली": "mai",
    "अंग्रेज़ी": "en",
    "अंग्रेजी": "en",
}

_SWITCH_LANG_RE = re.compile(
    r"""
    (?:
        switch\s+to
        | reply\s+in
        | give\s+(?:the\s+)?reply\s+in
        | change\s+(?:to\s+)?(?:language\s+to\s+)?
        | language\s*[:=]\s*
    )\s*
    (english|eng|hindi|hin|bhojpuri|maithili|हिन्दी|हिंदी|भोजपुरी|मैथिली|अंग्रेज़ी|अंग्रेजी)
    |
    (english|hindi|bhojpuri|maithili)\s+mein
    """,
    re.IGNORECASE | re.VERBOSE,
)


def match_language(text: str, bid: str | None = None) -> str | None:
    if bid in ("lang_hi", "lang_en", "lang_bho", "lang_mai"):
        return bid.replace("lang_", "")
    t = _norm(text)
    if not t:
        return None

    m = _SWITCH_LANG_RE.search(t)
    if m:
        raw = (m.group(1) or m.group(2) or "").strip().lower()
        code = _LANG_NAME_TO_CODE.get(raw) or _LANG_NAME_TO_CODE.get(raw.title())
        if not code:
            for k, v in _LANG_NAME_TO_CODE.items():
                if _norm(k) == raw:
                    code = v
                    break
        if code:
            return code

    mapping = [
        (("hi",), ["हिन्दी", "हिंदी", "hindi", "hin"]),
        (("en",), ["english", "eng", "अंग्रेज़ी", "अंग्रेजी"]),
        (("bho",), ["भोजपुरी", "bhojpuri"]),
        (("mai",), ["मैथिली", "maithili"]),
    ]
    for codes, words in mapping:
        for w in words:
            if t == _norm(w):
                return codes[0]
    return None


def match_menu(text: str, bid: str | None = None) -> str | None:
    if bid and bid.startswith("menu_"):
        return bid
    if bid == "elig_retry":
        return "elig_retry"
    t = _norm(text)
    if not t:
        return None

    if t == _norm(MENU_SCHOOLS) or t == _norm("स्कूल कैसे चुनें"):
        return "menu_schools"
    if t == _norm(MENU_SCHOOLS_EN) or t == _norm("how to choose school"):
        return "menu_schools"

    if t == _norm("अन्य") or t == _norm("others"):
        return "menu_others"

    pairs = [
        (
            "menu_elig",
            [
                MENU_ELIG,
                MENU_ELIG_FULL,
                MENU_ELIG_EN,
                "पात्रता",
                "eligibility",
                "eligible",
                "form bhar",
                "फॉर्म भर",
                "पात्रता जाँच",
            ],
        ),
        (
            "menu_apply",
            [
                MENU_APPLY,
                MENU_APPLY_EN,
                "आवेदन कैसे",
                "how to apply",
                "apply",
                "आवेदन करें",
                APPLY_HOW,
                APPLY_HOW_EN,
            ],
        ),
        (
            "menu_status",
            [
                MENU_STATUS,
                MENU_STATUS_EN,
                "आवेदन स्थिति",
                "status",
                "avedan stithi",
                "aavedan stithi",
                "application status",
                "form status",
            ],
        ),
        (
            "menu_docs",
            [
                MENU_DOCS,
                MENU_DOCS_EN,
                "कागज़ात",
                "documents",
                "document",
                DOCS_REQUIRED,
                DOCS_REQUIRED_EN,
                "आवश्यक दस्तावेज",
                "required documents",
            ],
        ),
        (
            "menu_grievance",
            [MENU_GRIEVANCE, MENU_GRIEVANCE_EN, "शिकायत", "shikayat", "grievance"],
        ),
        (
            "menu_others",
            [MENU_OTHERS, MENU_OTHERS_FULL, MENU_OTHERS_EN],
        ),
        ("menu_main", [MENU_MAIN, MENU_MAIN_EN, "main menu", "शुरू से", "home"]),
        ("menu_lang", [MENU_LANG, MENU_LANG_EN, "change language", "भाषा बदलें"]),
        ("menu_write", [WRITE_OWN, WRITE_OWN_EN, WRITE_OWN_LONG, "अपना सवाल"]),
        ("elig_retry", [RETRY_ELIG, RETRY_ELIG_EN, "दोबारा"]),
    ]
    for mid, words in pairs:
        for w in words:
            wn = _norm(w)
            if not wn:
                continue
            if t == wn or wn in t:
                return mid
    return None


def parse_age_years(text: str) -> float | None:
    t = (text or "").strip()
    m = re.search(r"(\d+(?:\.\d+)?)\s*(साल|वर्ष|year|yrs|yr)?", t, re.I)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            return None
    m2 = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", t)
    if m2:
        d, mo, y = int(m2.group(1)), int(m2.group(2)), int(m2.group(3))
        if y > 1900:
            age = 2026 - y
            if (mo, d) > (9, 16):
                age -= 1
            return float(age)
    m3 = re.search(r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})", t)
    if m3:
        y, mo, d = int(m3.group(1)), int(m3.group(2)), int(m3.group(3))
        age = 2026 - y
        if (mo, d) > (9, 16):
            age -= 1
        return float(age)
    return None


def age_in_window(years: float) -> bool:
    return 6.0 <= years < 8.0


def extract_eligibility_facts(text: str) -> dict[str, bool | None]:
    """Pull age/class/income signals from free text. None = unknown."""
    t = _norm(text)
    age_ok: bool | None = None
    class_ok: bool | None = None
    income_ok: bool | None = None

    years = parse_age_years(text)
    if years is not None and (
        re.search(r"\b(age|years?|साल|वर्ष|yrs?)\b", t, re.I)
        or re.search(r"\b[6-9]\b", t)
        or re.search(r"\d{1,2}[/-]\d{1,2}[/-]\d{4}", text or "")
    ):
        age_ok = age_in_window(years)
    elif years is not None and 5 <= years <= 12:
        # Bare number in plausible age range when eligibility-ish context
        age_ok = age_in_window(years)

    if re.search(r"less\s*than\s*class\s*1|class\s*0|nursery|anganwadi|अंगनवाड़ी|कक्षा\s*से\s*कम", t):
        class_ok = False
    elif re.search(r"class\s*2\s*(&|and|और)?\s*3|class\s*[23]|कक्षा\s*[23]", t):
        class_ok = True
    elif re.search(r"class\s*1\b|कक्षा\s*1|first\s*class", t):
        class_ok = True

    if re.search(
        r"इनमें\s*से\s*नहीं|income\s*(above|over|more)|आय\s*(ज्यादा|अधिक)|not\s*ews|not\s*eligible\s*income",
        t,
    ):
        income_ok = False
    elif re.search(
        r"ews|weaker|कमजोर|2\s*lakh|2\s*लाख|₹?\s*2\s*,?\s*00\s*,?\s*000|"
        r"वंचित|disadvantaged|\bsc\b|\bst\b|\bobc\b|\bebc\b|minority|अल्पसंख्यक|"
        r"1\s*lakh|1\s*लाख",
        t,
    ):
        income_ok = True

    return {"age_ok": age_ok, "class_ok": class_ok, "income_ok": income_ok}


def try_free_text_eligibility(
    text: str, language: str | None = None
) -> dict[str, Any] | None:
    """If free text has age + class + income, answer without guided quiz."""
    facts = extract_eligibility_facts(text)
    if any(facts[k] is None for k in ("age_ok", "class_ok", "income_ok")):
        return None
    if facts["age_ok"] and facts["class_ok"] and facts["income_ok"]:
        return eligibility_pass_result(language)
    reasons: list[str] = []
    if _en(language):
        if not facts["age_ok"]:
            reasons.append("age is outside the allowed window")
        if not facts["class_ok"]:
            reasons.append("class must be Class 1 or Class 2 & 3")
        if not facts["income_ok"]:
            reasons.append("income/category condition not met")
        reason = "; ".join(reasons) + "."
    else:
        if not facts["age_ok"]:
            reasons.append("उम्र निर्धारित सीमा में नहीं है")
        if not facts["class_ok"]:
            reasons.append("कक्षा Class 1 या Class 2 & 3 होनी चाहिए")
        if not facts["income_ok"]:
            reasons.append("आय/वर्ग शर्त पूरी नहीं होती")
        reason = "। ".join(reasons) + "।"
    return eligibility_fail_result(reason, language)


def grievance_label_for_id(bid: str, language: str | None = None) -> str:
    rows = GRIEVANCE_ROWS_EN if _en(language) else GRIEVANCE_ROWS
    for rid, title, full in rows:
        if rid == bid:
            if rid == "gr_free":
                return "Typed question" if _en(language) else "स्वयं लिखा"
            return full
    return "Typed question" if _en(language) else "स्वयं लिखा"


def match_grievance(text: str, bid: str | None = None) -> str | None:
    if bid and bid.startswith("gr_"):
        return bid
    t = _norm(text)
    # Match both HI and EN row labels
    for rows in (GRIEVANCE_ROWS, GRIEVANCE_ROWS_EN):
        for rid, title, full in rows:
            if t == _norm(title) or t == _norm(full):
                return rid
            tn = _norm(title)
            fn = _norm(full)
            if len(tn) >= 6 and (tn in t or fn in t):
                return rid
    # Legacy duplicate phrasing
    if "स्कूल ने प्रवेश" in (text or "") and "मना" in (text or ""):
        return "gr_refuse"
    return None


_GRIEVANCE_LIKE_RE = re.compile(
    r"""
    \b(
        otp
        | login
        | log\s*in
        | user\s*id
        | userid
        | sms
        | password
        | portal\s*(problem|issue|error|not\s*working)?
        | did\s+not\s+receive
        | didn't\s+receive
        | not\s+received
        | cannot\s+login
        | can't\s+login
        | unable\s+to\s+(login|log\s*in)
    )\b
    | ओटीपी
    | लॉगिन
    | लॉग\s*इन
    | एसएमएस
    | यूज़र\s*आईडी
    | यूजर\s*आईडी
    """,
    re.IGNORECASE | re.VERBOSE,
)


def is_grievance_like(text: str) -> bool:
    return bool(_GRIEVANCE_LIKE_RE.search(text or ""))


_DEMO_LIVE_COUNTS_RE = re.compile(
    r"""
    \b(
        total\s+(seats?|schools?|applications?|admissions?)
        | how\s+many\s+(seats?|schools?|applications?|admissions?)
        | (seats?|schools?|applications?|admissions?)\s+(by\s+)?district
        | district[- ]wise\s+(seats?|schools?|applications?|admissions?)
        | live\s+(count|data|numbers?)
    )\b
    | कुल\s+(सीट|स्कूल|आवेदन|प्रवेश)
    | जिले\s*(वार|के)\s*(सीट|स्कूल|आवेदन)
    | कितने\s+(स्कूल|सीट|आवेदन)
    """,
    re.IGNORECASE | re.VERBOSE,
)

_DEMO_PATTERNS: list[tuple[re.Pattern[str], str, str]] = [
    (
        re.compile(
            r"\b(rte\s*12\s*\(?\s*1\s*\)?\s*\(?\s*c\)?|section\s*12|12\s*\(1\)\s*\(c\))\b"
            r"|आरटीई\s*12|धारा\s*12",
            re.I,
        ),
        "RTE 12(1)(c) private schools में कमजोर/वंचित वर्ग के बच्चों के लिए 25% सीट आरक्षण है।\n"
        f"विवरण: {PORTAL_FAQ}",
        "RTE 12(1)(c) reserves 25% seats in private schools for weaker/disadvantaged children.\n"
        f"Details: {PORTAL_FAQ}",
    ),
    (
        re.compile(
            r"\b(benefits?|what\s+are\s+the\s+benefits|facility|facilities)\b"
            r"|लाभ|सुविधा",
            re.I,
        ),
        "मुख्य लाभ: निजी स्कूल में निःशुल्क शिक्षा (निर्धारित कक्षा तक), किताब/यूनिफॉर्म आदि नियम अनुसार।\n"
        f"पोर्टल FAQ: {PORTAL_FAQ}",
        "Main benefits: free education in private school (up to prescribed class), "
        f"books/uniform as per rules.\nPortal FAQ: {PORTAL_FAQ}",
    ),
    (
        re.compile(
            r"\b(documents?|document\s+list|what\s+documents|papers?\s+required)\b"
            r"|कागज़ात|दस्तावेज|दस्तावेज़",
            re.I,
        ),
        DOCS_LIST_TEXT_HI + f"\n{PORTAL_FAQ}",
        DOCS_LIST_TEXT_EN + f"\n{PORTAL_FAQ}",
    ),
    (
        re.compile(
            r"\b(deadline|last\s+date|closing\s+date|when\s+to\s+apply|application\s+period)\b"
            r"|अंतिम\s*तिथि|आखिरी\s*तारीख|कब\s*तक\s*आवेदन",
            re.I,
        ),
        "आवेदन की अंतिम तिथि पोर्टल पर अधिसूचना में देखें — बॉट में live date नहीं है।\n"
        f"{PORTAL}",
        "Check the application last date in the portal notification — the bot has no live date.\n"
        f"{PORTAL}",
    ),
    (
        re.compile(
            r"\b(nodal\s+(department|officer|agency)|which\s+department|implementing\s+agency)\b"
            r"|नोडल\s*(विभाग|अधिकारी)|कौन\s*विभाग",
            re.I,
        ),
        "ज्ञानदीप / RTE बिहार शिक्षा विभाग के अंतर्गत संचालित है।\n"
        f"आधिकारिक जानकारी: {PORTAL_FAQ}",
        "Gyandeep / RTE Bihar is run under the Education Department.\n"
        f"Official info: {PORTAL_FAQ}",
    ),
    (
        re.compile(
            r"\b(admission\s+notification|notification|admit\s+notice|admission\s+notice)\b"
            r"|प्रवेश\s*अधिसूचना|अधिसूचना",
            re.I,
        ),
        "प्रवेश/आवेदन अधिसूचना पोर्टल पर प्रकाशित होती है।\n"
        f"देखें: {PORTAL}",
        "Admission/application notifications are published on the portal.\n"
        f"See: {PORTAL}",
    ),
]


def try_demo_answer(text: str, language: str | None = None) -> dict[str, Any] | None:
    t = text or ""
    if not t.strip():
        return None
    if _DEMO_LIVE_COUNTS_RE.search(t):
        if _en(language):
            return _reply(
                "The bot cannot give live seat/school/application counts.\n"
                f"School list: {PORTAL_SCHOOLS}\n"
                f"Portal: {PORTAL}",
                [
                    _btn("school_list", SCHOOL_LIST_EN),
                    _btn("menu_main", MENU_MAIN_EN[:20]),
                ],
            )
        return _reply(
            "लाइव सीट/स्कूल/आवेदन संख्या अभी बॉट नहीं दे सकता।\n"
            f"स्कूल सूची: {PORTAL_SCHOOLS}\n"
            f"पोर्टल: {PORTAL}",
            [
                _btn("school_list", SCHOOL_LIST),
                _btn("menu_main", MENU_MAIN),
            ],
        )
    for pat, ans_hi, ans_en in _DEMO_PATTERNS:
        if pat.search(t):
            ans = ans_en if _en(language) else ans_hi
            if _en(language):
                return _reply(
                    ans,
                    [
                        _btn("menu_main", MENU_MAIN_EN[:20]),
                        _btn("menu_apply", MENU_APPLY_EN[:20]),
                        _btn("menu_docs", MENU_DOCS_EN[:20]),
                    ],
                )
            return _reply(
                ans,
                [
                    _btn("menu_main", MENU_MAIN),
                    _btn("menu_apply", "आवेदन कैसे करें"),
                    _btn("menu_docs", MENU_DOCS),
                ],
            )
    return None
