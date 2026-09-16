"""Orchestrate guided UX session first, else router + answerer."""

from __future__ import annotations

import re
from typing import Any

from answerer import generate_reply
from guided import (
    AGE_NO,
    AGE_UNSURE,
    AGE_YES,
    APPLY_NEXT,
    APPLY_PORTAL,
    APPLY_PROBLEM,
    APPLY_STEPS,
    CLASS_1,
    CLASS_2_3,
    CLASS_LT1,
    DOCS_AADHAAR,
    DOCS_FULL,
    DOCS_FULL_BTN,
    DOCS_SHORT,
    INCOME_DG,
    INCOME_DG_FULL,
    INCOME_EWS,
    INCOME_EWS_FULL,
    INCOME_NO,
    NO_HI,
    SCHOOL_DIST,
    SCHOOL_LIST,
    YES_HI,
    age_in_window,
    apply_portal_only,
    apply_start,
    apply_step,
    docs_aadhaar,
    docs_full,
    docs_short,
    docs_start,
    eligibility_age,
    eligibility_age_typed_prompt,
    eligibility_class,
    eligibility_declined,
    eligibility_fail_result,
    eligibility_gate,
    eligibility_income,
    eligibility_pass_result,
    grievance_ask_free,
    grievance_label_for_id,
    grievance_menu,
    grievance_ticket,
    language_prompt,
    main_menu,
    match_grievance,
    match_language,
    match_menu,
    others_free_prompt,
    parse_age_years,
    schools_distance,
    schools_list,
    schools_start,
    status_ask_id,
    topic_chooser,
)
from router import GENERAL_INFO_RE, GYAN_ID_RE, route_intent
from session import (
    clear_flow,
    get_session,
    reset_eligibility,
    set_fields,
)

_GREETINGS = {
    "hi",
    "hello",
    "hey",
    "namaste",
    "namaskar",
    "हैलो",
    "नमस्ते",
    "नमस्कार",
    "start",
    "menu",
    "मेनू",
}


def _as_dict(reply: str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(reply, dict):
        return reply
    return {"text": reply}


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def _start_flow(wa_id: str | None, menu_id: str) -> dict[str, Any]:
    if menu_id == "menu_elig" or menu_id == "elig_retry":
        reset_eligibility(wa_id)
        return eligibility_gate()
    if menu_id == "menu_apply":
        set_fields(wa_id, flow="apply", apply_step=0, last_topic="apply", awaiting_status_id=False)
        return apply_start()
    if menu_id == "menu_status":
        set_fields(wa_id, flow="status", awaiting_status_id=True, last_topic="status")
        return status_ask_id()
    if menu_id == "menu_schools":
        set_fields(wa_id, flow="schools", schools_step=0, last_topic="schools")
        return schools_start()
    if menu_id == "menu_docs":
        set_fields(wa_id, flow="docs", docs_step=0, last_topic="docs")
        return docs_start()
    if menu_id == "menu_grievance":
        set_fields(
            wa_id,
            flow="grievance",
            grievance_waiting=False,
            grievance_category=None,
            last_topic="grievance",
        )
        return grievance_menu()
    if menu_id in ("menu_others", "menu_write"):
        set_fields(wa_id, flow="others", last_topic="others")
        return topic_chooser() if menu_id == "menu_others" else others_free_prompt()
    if menu_id == "menu_lang":
        set_fields(wa_id, flow="language")
        return language_prompt()
    if menu_id == "menu_main":
        clear_flow(wa_id, keep_language=True)
        set_fields(wa_id, flow="main")
        sess = get_session(wa_id)
        return main_menu(sess.get("language"))
    return main_menu(get_session(wa_id).get("language"))


def _handle_eligibility(wa_id: str | None, text: str, bid: str | None) -> dict[str, Any] | None:
    sess = get_session(wa_id)
    step = sess.get("eligibility_step")
    t = _norm(text)

    if step == "gate":
        if bid == "elig_yes" or t in (_norm(YES_HI), "yes", "y"):
            set_fields(wa_id, eligibility_step="age")
            return eligibility_age()
        if bid == "elig_no" or t in (_norm(NO_HI), "no", "n"):
            clear_flow(wa_id, keep_language=True)
            return eligibility_declined()
        return eligibility_gate()

    if step == "age":
        if bid == "age_yes" or t == _norm(AGE_YES) or t in ("हाँ, इस उम्र में है",):
            set_fields(wa_id, eligibility_answers={"age_ok": True}, eligibility_step="class")
            return eligibility_class()
        if bid == "age_no" or t == _norm(AGE_NO):
            set_fields(wa_id, eligibility_answers={"age_ok": False}, eligibility_step="done")
            clear_flow(wa_id, keep_language=True)
            return eligibility_fail_result("उम्र निर्धारित सीमा में नहीं है।")
        if bid == "age_unsure" or t == _norm(AGE_UNSURE):
            set_fields(wa_id, eligibility_step="age_typed")
            return eligibility_age_typed_prompt()
        return eligibility_age()

    if step == "age_typed":
        years = parse_age_years(text)
        if years is None:
            return eligibility_age_typed_prompt()
        if age_in_window(years):
            set_fields(wa_id, eligibility_answers={"age_ok": True}, eligibility_step="class")
            return eligibility_class()
        set_fields(wa_id, eligibility_answers={"age_ok": False}, eligibility_step="done")
        clear_flow(wa_id, keep_language=True)
        return eligibility_fail_result("उम्र निर्धारित सीमा में नहीं है।")

    if step == "class":
        if bid == "class_1" or t == _norm(CLASS_1):
            set_fields(wa_id, eligibility_answers={"class_ok": True}, eligibility_step="income")
            return eligibility_income()
        if bid == "class_2_3" or t == _norm(CLASS_2_3) or "class 2" in t:
            set_fields(wa_id, eligibility_answers={"class_ok": True}, eligibility_step="income")
            return eligibility_income()
        if bid == "class_lt1" or t == _norm(CLASS_LT1) or "less than" in t:
            set_fields(wa_id, eligibility_answers={"class_ok": False}, eligibility_step="done")
            clear_flow(wa_id, keep_language=True)
            return eligibility_fail_result("कक्षा Class 1 या Class 2 & 3 होनी चाहिए।")
        return eligibility_class()

    if step == "income":
        if bid == "income_ews" or t in (_norm(INCOME_EWS), _norm(INCOME_EWS_FULL)) or "कमजोर" in t:
            set_fields(wa_id, eligibility_answers={"income_ok": True}, eligibility_step="done")
            clear_flow(wa_id, keep_language=True)
            return eligibility_pass_result()
        if bid == "income_dg" or t in (_norm(INCOME_DG), _norm(INCOME_DG_FULL)) or "वंचित" in t:
            set_fields(wa_id, eligibility_answers={"income_ok": True}, eligibility_step="done")
            clear_flow(wa_id, keep_language=True)
            return eligibility_pass_result()
        if bid == "income_no" or t == _norm(INCOME_NO) or "इनमें से नहीं" in text:
            set_fields(wa_id, eligibility_answers={"income_ok": False}, eligibility_step="done")
            clear_flow(wa_id, keep_language=True)
            return eligibility_fail_result("आय/वर्ग शर्त पूरी नहीं होती।")
        return eligibility_income()

    return None


def _handle_apply(wa_id: str | None, text: str, bid: str | None) -> dict[str, Any] | None:
    sess = get_session(wa_id)
    step = sess.get("apply_step")
    t = _norm(text)

    if bid == "apply_portal" or t == _norm(APPLY_PORTAL):
        return apply_portal_only()
    if bid == "apply_problem" or t == _norm(APPLY_PROBLEM):
        set_fields(wa_id, flow="grievance", grievance_waiting=False, last_topic="grievance")
        return grievance_menu()
    if bid == "apply_steps" or t == _norm(APPLY_STEPS):
        set_fields(wa_id, apply_step=0)
        return apply_step(0)
    if bid == "apply_next" or t == _norm(APPLY_NEXT) or t in ("आगे", "हो गया"):
        n = int(sess.get("apply_step") or 0) + 1
        set_fields(wa_id, apply_step=n)
        return apply_step(n)

    if step is None or step == 0:
        return apply_start()
    return apply_step(int(step))


def _handle_schools(wa_id: str | None, text: str, bid: str | None) -> dict[str, Any] | None:
    t = _norm(text)
    if bid == "school_list" or t == _norm(SCHOOL_LIST) or "स्कूल सूची" in text:
        set_fields(wa_id, schools_step=1)
        return schools_list()
    if bid == "school_dist" or t == _norm(SCHOOL_DIST) or "दूरी" in text:
        set_fields(wa_id, schools_step=2)
        return schools_distance()
    return schools_start()


def _handle_docs(wa_id: str | None, text: str, bid: str | None) -> dict[str, Any] | None:
    t = _norm(text)
    if bid == "docs_short" or t == _norm(DOCS_SHORT) or "छोटी" in text:
        return docs_short()
    if bid == "docs_full" or t in (_norm(DOCS_FULL), _norm(DOCS_FULL_BTN)) or "पूरी लिस्ट" in text:
        return docs_full()
    if bid == "docs_aadhaar" or t == _norm(DOCS_AADHAAR) or "आधार" in text:
        return docs_aadhaar()
    return docs_start()


def _handle_grievance(wa_id: str | None, text: str, bid: str | None) -> dict[str, Any] | None:
    sess = get_session(wa_id)
    if sess.get("grievance_waiting"):
        label = sess.get("grievance_category") or "स्वयं लिखा"
        clear_flow(wa_id, keep_language=True)
        return grievance_ticket(label)

    gid = match_grievance(text, bid)
    if not gid and bid and bid.startswith("gr_"):
        gid = bid
    if gid == "gr_free":
        set_fields(wa_id, grievance_waiting=True, grievance_category="स्वयं लिखा")
        return grievance_ask_free()
    if gid:
        label = grievance_label_for_id(gid)
        clear_flow(wa_id, keep_language=True)
        return grievance_ticket(label)
    return grievance_menu()


def _llm_fallback(user_text: str) -> dict[str, Any]:
    route = route_intent(user_text)
    print(f"Router result: {route}", flush=True)
    return _as_dict(generate_reply(user_text, route))


def handle_message(
    user_text: str,
    wa_id: str | None = None,
    button_id: str | None = None,
) -> dict[str, Any]:
    """Return {text, buttons?, list_sections?, list_button_label?}."""
    text = (user_text or "").strip()
    bid = (button_id or "").strip() or None

    if not text and not bid:
        return _as_dict(
            "नमस्कार। कृपया अपना प्रश्न लिखें। स्थिति, जानकारी, या शिकायत।"
        )

    # Prefer interactive id as selection signal when title also present
    effective_text = text
    if bid and not text:
        effective_text = bid

    sess = get_session(wa_id)
    lowered = _norm(effective_text)

    # GYAN application id: always preserve deterministic status card path
    gyan = GYAN_ID_RE.search(text or "")
    if gyan:
        set_fields(wa_id, awaiting_status_id=False, flow=None, last_topic="status")
        return _llm_fallback(text)

    # Language selection (first-time or change)
    lang = match_language(effective_text, bid)
    if lang:
        prev = sess.get("language")
        set_fields(wa_id, language=lang)
        # First pick / language flow -> main menu; mid-chat switch stays on topic
        if prev is None or sess.get("flow") in (None, "language"):
            set_fields(wa_id, flow="main")
            return main_menu(lang)
        names = {"hi": "हिन्दी", "en": "English", "bho": "भोजपुरी", "mai": "मैथिली"}
        return {"text": f"ठीक है। अब जवाब {names.get(lang, lang)} में होंगे।"}

    # Cold greeting / restart -> language if unset, else main menu
    if lowered in _GREETINGS or bid in ("menu_main",):
        if bid == "menu_main" or lowered in {"menu", "मेनू", "start"}:
            clear_flow(wa_id, keep_language=True)
            set_fields(wa_id, flow="main")
            return main_menu(sess.get("language"))
        if not sess.get("language"):
            set_fields(wa_id, flow="language")
            return language_prompt()
        clear_flow(wa_id, keep_language=True)
        set_fields(wa_id, flow="main")
        return main_menu(sess.get("language"))

    # Global menu shortcuts (button id or title)
    menu_id = match_menu(effective_text, bid)
    if menu_id in (
        "menu_elig",
        "menu_apply",
        "menu_status",
        "menu_schools",
        "menu_docs",
        "menu_grievance",
        "menu_others",
        "menu_write",
        "menu_lang",
        "menu_main",
        "elig_retry",
    ):
        return _start_flow(wa_id, menu_id)

    # General enquiry synonyms -> topic chooser (never FAQ wall)
    if GENERAL_INFO_RE.search(text or effective_text):
        set_fields(wa_id, flow="others", last_topic="others")
        return topic_chooser()

    # Continue active guided flow
    flow = sess.get("flow")
    if flow == "language":
        set_fields(wa_id, flow="language")
        return language_prompt()

    if flow == "eligibility":
        out = _handle_eligibility(wa_id, effective_text, bid)
        if out:
            return out

    if flow == "apply":
        out = _handle_apply(wa_id, effective_text, bid)
        if out:
            return out

    if flow == "schools":
        out = _handle_schools(wa_id, effective_text, bid)
        if out:
            return out

    if flow == "docs":
        out = _handle_docs(wa_id, effective_text, bid)
        if out:
            return out

    if flow == "grievance":
        out = _handle_grievance(wa_id, effective_text, bid)
        if out:
            return out

    if flow == "status" or sess.get("awaiting_status_id"):
        # No GYAN id in this turn: keep asking
        return status_ask_id()

    if flow == "others":
        # Free text while in others: try menu match already done; else topic chooser again
        # or short LLM if it looks like a real question
        if len(effective_text.split()) >= 4:
            return _llm_fallback(text)
        return topic_chooser()

    if flow == "main":
        return main_menu(sess.get("language"))

    # No language yet and not greeting: still ask language first
    if not sess.get("language"):
        set_fields(wa_id, flow="language")
        return language_prompt()

    # Fall through to router + answerer (status phrases etc.)
    return _llm_fallback(text)
