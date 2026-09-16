"""Pure guided-UX logic for Gyandeep Saathi WhatsApp flows.

Returns reply payloads:
  { "text": str, "buttons": [{"id","title"}, ...]?, "list_sections": [...]? ,
    "list_button_label": str? }

Button/list titles stay within WhatsApp limits (reply 20, list row 24).
Matching also accepts full product copy so typed replies still work.
"""

from __future__ import annotations

import re
from typing import Any

from session import next_ticket_id

PORTAL = "https://gyandeep-rte.bihar.gov.in/"
PORTAL_FAQ = "https://gyandeep-rte.bihar.gov.in/faq"
PORTAL_SCHOOLS = "https://gyandeep-rte.bihar.gov.in/registration-school-details"

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

BTN_LANG_HI = "हिन्दी"
BTN_LANG_EN = "English"
BTN_LANG_BHO = "भोजपुरी"
BTN_LANG_MAI = "मैथिली"

YES_HI = "हाँ"
NO_HI = "नहीं"
AGE_YES = "हाँ, इस उम्र में है"  # 19
AGE_NO = "नहीं, इस उम्र में नहीं"  # 22 list OK
AGE_UNSURE = "पक्का नहीं"

CLASS_1 = "Class 1"
CLASS_2_3 = "Class 2 & 3"
CLASS_LT1 = "Less than class 1"

INCOME_EWS_FULL = "कमजोर वर्ग (आय ₹2 लाख तक)"
INCOME_DG_FULL = "वंचित वर्ग (SC/ST/OBC/EBC/अल्पसंख्यक, आय ₹1 लाख तक)"
INCOME_NO = "इनमें से नहीं"
INCOME_EWS = "कमजोर वर्ग (आय 2 लाख)"  # 21
INCOME_DG = "वंचित वर्ग (आय 1 लाख)"  # 21

APPLY_STEPS = "कदम-कदम बताओ"
APPLY_PORTAL = "पोर्टल लिंक"
APPLY_NEXT = "हो गया/आगे"
APPLY_PROBLEM = "समस्या"

SCHOOL_LIST = "स्कूल सूची खोलो"
SCHOOL_DIST = "दूरी का नियम"
SCHOOL_LIST_SHORT = "स्कूल सूची"

DOCS_SHORT = "छोटी लिस्ट देखें"
DOCS_FULL = "पूरी लिस्ट (पोर्टल FAQ)"  # 23
DOCS_FULL_BTN = "पूरी लिस्ट"  # reply-safe
DOCS_AADHAAR = "बच्चे का आधार कब?"

RETRY_ELIG = "दोबारा जाँचें"
WRITE_OWN = "अपना सवाल लिखें"
WRITE_OWN_LONG = "अपना सवाल खुद लिखें"

GRIEVANCE_ROWS = [
    ("gr_portal", "पोर्टल/लॉगिन/OTP समस्या", "पोर्टल / लॉगिन / OTP समस्या"),
    ("gr_sms", "SMS/USER ID नहीं मिला", "SMS / USER ID नहीं मिला"),
    ("gr_docs", "कागज़ात / जाँच अटकी", "कागज़ात / जाँच अटकी"),
    ("gr_allot", "स्कूल आवंटन/लॉटरी समस्या", "स्कूल आवंटन / लॉटरी समस्या"),
    ("gr_refuse", "स्कूल ने प्रवेश मना किया", "स्कूल ने प्रवेश से मना किया"),
    ("gr_elig", "पात्रता / आय-वर्ग भ्रम", "पात्रता / आय-वर्ग भ्रम"),
    ("gr_other", "गलत जानकारी / अन्य", "गलत जानकारी / अन्य पोर्टल समस्या"),
    ("gr_free", WRITE_OWN_LONG, "अपना सवाल खुद लिखें (free text)"),
]


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


def main_menu(language: str | None = None) -> dict[str, Any]:
    if language == "en":
        text = "Hello. I am Gyandeep Saathi.\nWhat do you want to do?"
    else:
        text = "नमस्कार। मैं ज्ञानदीप साथी हूँ।\nआप क्या करना चाहते हैं?"
    return _list_reply(
        text,
        [
            {
                "title": "मेनू",
                "rows": [
                    _row("menu_elig", MENU_ELIG, MENU_ELIG_FULL),
                    _row("menu_apply", MENU_APPLY),
                    _row("menu_status", MENU_STATUS),
                    _row("menu_schools", MENU_SCHOOLS),
                    _row("menu_docs", MENU_DOCS),
                    _row("menu_grievance", MENU_GRIEVANCE),
                    _row("menu_others", MENU_OTHERS, MENU_OTHERS_FULL),
                    _row("menu_lang", MENU_LANG),
                ],
            }
        ],
        "मेनू खोलें",
    )


def topic_chooser() -> dict[str, Any]:
    """General enquiry / samanya jankari: topic buttons, never FAQ wall."""
    return _list_reply(
        "आप अपना सवाल लिख सकते हैं।\nया नीचे से विषय चुनें:",
        [
            {
                "title": "विषय",
                "rows": [
                    _row("menu_elig", MENU_ELIG, MENU_ELIG_FULL),
                    _row("menu_apply", MENU_APPLY),
                    _row("menu_status", MENU_STATUS),
                    _row("menu_schools", MENU_SCHOOLS),
                    _row("menu_docs", MENU_DOCS),
                    _row("menu_grievance", MENU_GRIEVANCE),
                    _row("menu_write", WRITE_OWN),
                ],
            }
        ],
        "विषय चुनें",
    )


def eligibility_gate() -> dict[str, Any]:
    return _reply(
        "क्या आप जाँचना चाहते हैं कि आपका बच्चा ज्ञानदीप / आरटीई में फॉर्म भर सकता है?",
        [_btn("elig_yes", YES_HI), _btn("elig_no", NO_HI)],
    )


def eligibility_age() -> dict[str, Any]:
    # AGE_NO is 22 chars: use list (row title max 24)
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


def eligibility_age_typed_prompt() -> dict[str, Any]:
    return _reply("उम्र साल में लिखें (या जन्म तिथि)।")


def eligibility_class() -> dict[str, Any]:
    return _reply(
        "बच्चा किस कक्षा में दाखिला लेना चाहता है?",
        [
            _btn("class_1", CLASS_1),
            _btn("class_2_3", CLASS_2_3),
            _btn("class_lt1", CLASS_LT1),
        ],
    )


def eligibility_income() -> dict[str, Any]:
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


def eligibility_pass_result() -> dict[str, Any]:
    return _reply(
        "आपके जवाब के हिसाब से बच्चा फॉर्म के लिए योग्य दिखता है।\n"
        f"अगला कदम: पोर्टल पर पंजीकरण।\n{PORTAL}",
        [
            _btn("menu_apply", "आवेदन कैसे करें?"),
            _btn("menu_schools", SCHOOL_LIST_SHORT),
            _btn("menu_main", MENU_MAIN),
        ],
    )


def eligibility_fail_result(reason: str) -> dict[str, Any]:
    return _reply(
        "आपके जवाब के हिसाब से अभी पात्रता पूरी नहीं दिखती।\n"
        f"कारण: {reason}\n{PORTAL_FAQ}",
        [
            _btn("elig_retry", RETRY_ELIG),
            _btn("menu_main", MENU_MAIN),
            _btn("menu_grievance", MENU_GRIEVANCE),
        ],
    )


def eligibility_declined() -> dict[str, Any]:
    return _reply(
        "ठीक है। आगे क्या करना चाहेंगे?",
        [
            _btn("menu_apply", "आवेदन कैसे करें?"),
            _btn("menu_status", MENU_STATUS),
            _btn("menu_main", MENU_MAIN),
        ],
    )


def apply_start() -> dict[str, Any]:
    return _reply(
        "आवेदन ऑनलाइन ही होता है। कहाँ से शुरू?",
        [
            _btn("apply_steps", APPLY_STEPS),
            _btn("apply_portal", APPLY_PORTAL),
            _btn("menu_main", MENU_MAIN),
        ],
    )


_APPLY_STEPS_TEXT = [
    "कदम 1/5: पोर्टल पर पंजीकरण करें और अभिभावक आधार से लॉगिन करें।",
    "कदम 2/5: SMS पर USER ID आएगा। उसे सुरक्षित रखें।",
    "कदम 3/5: फॉर्म भरें और कागज़ात अपलोड करें।",
    "कदम 4/5: अपने प्रखंड में अधिकतम 5 स्कूल चुनें।",
    "कदम 5/5: लॉटरी के बाद स्कूल में जाँच और प्रवेश।",
]


def apply_step(n: int) -> dict[str, Any]:
    n = max(0, min(n, 4))
    text = _APPLY_STEPS_TEXT[n] + f"\n{PORTAL}"
    if n >= 4:
        buttons = [
            _btn("menu_status", MENU_STATUS),
            _btn("menu_docs", MENU_DOCS),
            _btn("menu_main", MENU_MAIN),
        ]
    else:
        buttons = [
            _btn("apply_next", APPLY_NEXT),
            _btn("apply_problem", APPLY_PROBLEM),
            _btn("menu_main", MENU_MAIN),
        ]
    return _reply(text, buttons)


def apply_portal_only() -> dict[str, Any]:
    return _reply(
        f"पोर्टल खोलें और पंजीकरण शुरू करें:\n{PORTAL}",
        [_btn("apply_steps", APPLY_STEPS), _btn("menu_main", MENU_MAIN)],
    )


def schools_start() -> dict[str, Any]:
    return _reply(
        "स्कूल प्रखंड से चुनें। अधिकतम 5 स्कूल। पास वाला पहले रखें।",
        [
            _btn("school_list", SCHOOL_LIST),
            _btn("school_dist", SCHOOL_DIST),
            _btn("menu_main", MENU_MAIN),
        ],
    )


def schools_list() -> dict[str, Any]:
    return _reply(
        f"स्कूल सूची (जिला फिर प्रखंड):\n{PORTAL_SCHOOLS}\n"
        "खाली सीट का अनुमान न लगाएँ; पोर्टल देखें।",
        [_btn("school_dist", SCHOOL_DIST), _btn("menu_main", MENU_MAIN)],
    )


def schools_distance() -> dict[str, Any]:
    return _reply(
        "दूरी बैंड: 0-1 किमी, 1-3 किमी, 3-6 किमी।\nपास वाला स्कूल पहले चुनें।",
        [_btn("school_list", SCHOOL_LIST), _btn("menu_main", MENU_MAIN)],
    )


def docs_start() -> dict[str, Any]:
    return _reply(
        "आपको कागज़ात में क्या चाहिए?",
        [
            _btn("docs_short", DOCS_SHORT),
            _btn("docs_full", DOCS_FULL_BTN),
            _btn("docs_aadhaar", DOCS_AADHAAR),
        ],
    )


def docs_short() -> dict[str, Any]:
    return _reply(
        "जन्म प्रमाण; जाति/आय जहाँ लागू; निवास प्रमाण; अभिभावक आधार; फोटो + मोबाइल।\n"
        "बच्चे का आधार आवेदन पर ज़रूरी नहीं; प्रवेश के 3 महीने में।",
        [
            _btn("docs_full", DOCS_FULL_BTN),
            _btn("docs_aadhaar", DOCS_AADHAAR),
            _btn("menu_main", MENU_MAIN),
        ],
    )


def docs_full() -> dict[str, Any]:
    return _reply(
        f"पूर्ण कागज़ात सूची पोर्टल FAQ पर देखें:\n{PORTAL_FAQ}",
        [_btn("docs_short", DOCS_SHORT), _btn("menu_main", MENU_MAIN)],
    )


def docs_aadhaar() -> dict[str, Any]:
    return _reply(
        "बच्चे का आधार आवेदन भरते समय ज़रूरी नहीं।\n"
        "प्रवेश के 3 महीने के अंदर लगाना होता है।",
        [_btn("docs_short", DOCS_SHORT), _btn("menu_main", MENU_MAIN)],
    )


def grievance_menu() -> dict[str, Any]:
    return _list_reply(
        "शिकायत किस बारे में है?",
        [
            {
                "title": "शिकायत",
                "rows": [
                    _row(rid, title, full) for rid, title, full in GRIEVANCE_ROWS
                ],
            }
        ],
        "श्रेणी चुनें",
    )


def grievance_ask_free() -> dict[str, Any]:
    return _reply("अपनी समस्या 1-2 पंक्ति में लिखें।")


def grievance_ticket(category_label: str, ticket_id: str | None = None) -> dict[str, Any]:
    tid = ticket_id or next_ticket_id()
    return _reply(
        "आपकी शिकायत दर्ज हो गई।\n"
        f"टिकट: {tid}\n"
        f"श्रेणी: {category_label}\n"
        "आधिकारिक मदद: rtebiharhelp@gmail.com\n"
        "फोन: 18003454417 / 14417 (10 AM-5 PM, सोम-शनि)",
        [_btn("menu_status", MENU_STATUS), _btn("menu_main", MENU_MAIN)],
    )


def status_ask_id() -> dict[str, Any]:
    return _reply(
        "कृपया अपना आवेदन संख्या भेजें (उदाहरण: GYAN-2026-1001)।",
        [_btn("menu_main", MENU_MAIN), _btn("menu_grievance", MENU_GRIEVANCE)],
    )


def others_free_prompt() -> dict[str, Any]:
    return _reply(
        "अपना सवाल लिखें। या विषय चुनने के लिए मुख्य मेनू खोलें।",
        [_btn("menu_main", MENU_MAIN), _btn("menu_elig", "पात्रता जाँच")],
    )


_NORM_SPACE = re.compile(r"\s+")


def _norm(s: str) -> str:
    return _NORM_SPACE.sub(" ", (s or "").strip().lower())


def match_language(text: str, bid: str | None = None) -> str | None:
    if bid in ("lang_hi", "lang_en", "lang_bho", "lang_mai"):
        return bid.replace("lang_", "")
    t = _norm(text)
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
    pairs = [
        (
            "menu_elig",
            [
                MENU_ELIG,
                MENU_ELIG_FULL,
                "पात्रता",
                "eligibility",
                "eligible",
                "form bhar",
                "फॉर्म भर",
                "पात्रता जाँच",
            ],
        ),
        ("menu_apply", [MENU_APPLY, "आवेदन कैसे", "how to apply", "apply", "आवेदन करें"]),
        (
            "menu_status",
            [
                MENU_STATUS,
                "आवेदन स्थिति",
                "status",
                "avedan stithi",
                "aavedan stithi",
                "application status",
                "form status",
            ],
        ),
        ("menu_schools", [MENU_SCHOOLS, SCHOOL_LIST_SHORT, "स्कूल", "school", "स्कूल सूची"]),
        ("menu_docs", [MENU_DOCS, "कागज़ात", "documents", "document"]),
        ("menu_grievance", [MENU_GRIEVANCE, "शिकायत", "shikayat", "grievance"]),
        ("menu_others", [MENU_OTHERS, MENU_OTHERS_FULL, "अन्य", "others"]),
        ("menu_main", [MENU_MAIN, "main menu", "शुरू से", "home"]),
        ("menu_lang", [MENU_LANG, "change language", "भाषा"]),
        ("menu_write", [WRITE_OWN, "अपना सवाल"]),
        ("elig_retry", [RETRY_ELIG, "दोबारा"]),
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


def grievance_label_for_id(bid: str) -> str:
    for rid, title, full in GRIEVANCE_ROWS:
        if rid == bid:
            if rid == "gr_free":
                return "स्वयं लिखा"
            return full
    return "स्वयं लिखा"


def match_grievance(text: str, bid: str | None = None) -> str | None:
    if bid and bid.startswith("gr_"):
        return bid
    t = _norm(text)
    for rid, title, full in GRIEVANCE_ROWS:
        if t == _norm(title) or t == _norm(full):
            return rid
        if _norm(title) in t or _norm(full) in t:
            return rid
    return None
