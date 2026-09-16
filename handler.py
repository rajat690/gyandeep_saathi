"""Orchestrate guided UX session first, else router + answerer."""

from __future__ import annotations

import re
from typing import Any

from answerer import FALLBACK_HI, _looks_like_menu, format_status_card, generate_reply, lookup_status
from guided import (
    AGE_NO,
    AGE_NO_EN,
    AGE_UNSURE,
    AGE_UNSURE_EN,
    AGE_YES,
    AGE_YES_EN,
    APPLY_HOW,
    APPLY_HOW_EN,
    APPLY_NEXT,
    APPLY_PORTAL,
    APPLY_PROBLEM,
    APPLY_STEPS,
    APPLY_WEBSITE,
    APPLY_WEBSITE_EN,
    APPLY_YOUTUBE,
    APPLY_YOUTUBE_EN,
    CLASS_1,
    CLASS_2_3,
    CLASS_LT1,
    DOCS_AADHAAR,
    DOCS_FULL,
    DOCS_FULL_BTN,
    DOCS_LIST,
    DOCS_LIST_EN,
    DOCS_SHORT,
    INCOME_DG,
    INCOME_DG_EN,
    INCOME_DG_FULL,
    INCOME_EWS,
    INCOME_EWS_EN,
    INCOME_EWS_FULL,
    INCOME_NO,
    INCOME_NO_EN,
    NO_EN,
    NO_HI,
    SCHOOL_DIST,
    SCHOOL_DIST_EN,
    SCHOOL_LIST,
    SCHOOL_LIST_EN,
    YES_EN,
    YES_HI,
    age_in_window,
    apply_how_all_steps,
    apply_start,
    apply_website,
    apply_youtube,
    docs_list,
    docs_start,
    eligibility_age,
    eligibility_age_typed_prompt,
    eligibility_class,
    eligibility_class_followup,
    eligibility_declined,
    eligibility_fail_result,
    eligibility_gate,
    eligibility_income,
    eligibility_pass_result,
    grievance_ask_free,
    grievance_label_for_id,
    grievance_menu,
    grievance_ticket,
    is_grievance_like,
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
    short_help_reply,
    status_ask_id,
    status_card_with_buttons,
    topic_chooser,
    try_demo_answer,
    try_free_text_eligibility,
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


def _lang(wa_id: str | None) -> str | None:
    return get_session(wa_id).get("language")


def _yes(t: str, bid: str | None, yes_bid: str) -> bool:
    return bid == yes_bid or t in (_norm(YES_HI), _norm(YES_EN), "yes", "y", "haan", "ha")


def _no(t: str, bid: str | None, no_bid: str) -> bool:
    return bid == no_bid or t in (_norm(NO_HI), _norm(NO_EN), "no", "n", "nahi", "nahin")


def _start_flow(wa_id: str | None, menu_id: str, trigger_text: str = "") -> dict[str, Any]:
    lang = _lang(wa_id)
    if menu_id == "menu_elig" or menu_id == "elig_retry":
        # Feedback 4.0: free-text with full facts → answer without quiz
        free = try_free_text_eligibility(trigger_text, lang)
        if free:
            clear_flow(wa_id, keep_language=True)
            return free
        reset_eligibility(wa_id)
        return eligibility_gate(lang)
    if menu_id == "menu_apply":
        set_fields(wa_id, flow="apply", apply_step=0, last_topic="apply", awaiting_status_id=False)
        return apply_start(lang)
    if menu_id == "menu_status":
        set_fields(wa_id, flow="status", awaiting_status_id=True, last_topic="status")
        return status_ask_id(lang)
    if menu_id == "menu_schools":
        set_fields(wa_id, flow="schools", schools_step=0, last_topic="schools")
        return schools_start(lang)
    if menu_id == "menu_docs":
        set_fields(wa_id, flow="docs", docs_step=0, last_topic="docs")
        return docs_start(lang)
    if menu_id == "menu_grievance":
        set_fields(
            wa_id,
            flow="grievance",
            grievance_waiting=False,
            grievance_category=None,
            last_topic="grievance",
        )
        return grievance_menu(lang)
    if menu_id in ("menu_others", "menu_write"):
        set_fields(wa_id, flow="others", last_topic="others")
        return topic_chooser(lang) if menu_id == "menu_others" else others_free_prompt(lang)
    if menu_id == "menu_lang":
        set_fields(wa_id, flow="language")
        return language_prompt()
    if menu_id == "menu_main":
        clear_flow(wa_id, keep_language=True)
        set_fields(wa_id, flow="main")
        return main_menu(lang)
    return main_menu(lang)


def _handle_eligibility(wa_id: str | None, text: str, bid: str | None) -> dict[str, Any] | None:
    sess = get_session(wa_id)
    step = sess.get("eligibility_step")
    t = _norm(text)
    lang = sess.get("language")

    if step == "gate":
        if _yes(t, bid, "elig_yes"):
            set_fields(wa_id, eligibility_step="age")
            return eligibility_age(lang)
        if _no(t, bid, "elig_no"):
            clear_flow(wa_id, keep_language=True)
            return eligibility_declined(lang)
        return eligibility_gate(lang)

    if step == "age":
        if bid == "age_yes" or t in (_norm(AGE_YES), _norm(AGE_YES_EN)):
            set_fields(wa_id, eligibility_answers={"age_ok": True}, eligibility_step="class")
            return eligibility_class(lang)
        if bid == "age_no" or t in (_norm(AGE_NO), _norm(AGE_NO_EN)):
            set_fields(wa_id, eligibility_answers={"age_ok": False}, eligibility_step="done")
            clear_flow(wa_id, keep_language=True)
            reason = (
                "age is outside the allowed window."
                if lang == "en"
                else "उम्र निर्धारित सीमा में नहीं है।"
            )
            return eligibility_fail_result(reason, lang)
        if bid == "age_unsure" or t in (_norm(AGE_UNSURE), _norm(AGE_UNSURE_EN)):
            set_fields(wa_id, eligibility_step="age_typed")
            return eligibility_age_typed_prompt(lang)
        return eligibility_age(lang)

    if step == "age_typed":
        years = parse_age_years(text)
        if years is None:
            return eligibility_age_typed_prompt(lang)
        if age_in_window(years):
            set_fields(wa_id, eligibility_answers={"age_ok": True}, eligibility_step="class")
            return eligibility_class(lang)
        set_fields(wa_id, eligibility_answers={"age_ok": False}, eligibility_step="done")
        clear_flow(wa_id, keep_language=True)
        reason = (
            "age is outside the allowed window."
            if lang == "en"
            else "उम्र निर्धारित सीमा में नहीं है।"
        )
        return eligibility_fail_result(reason, lang)

    if step == "class":
        # Feedback 4.0: Yes → Class 1 PASS path; No → follow-up Class 2&3 vs <1
        if bid == "class_yes" or _yes(t, bid, "class_yes") or t == _norm(CLASS_1) or bid == "class_1":
            set_fields(wa_id, eligibility_answers={"class_ok": True}, eligibility_step="income")
            return eligibility_income(lang)
        if bid == "class_no" or _no(t, bid, "class_no"):
            set_fields(wa_id, eligibility_step="class_followup")
            return eligibility_class_followup(lang)
        # Legacy 3-way buttons still accepted
        if bid == "class_2_3" or t == _norm(CLASS_2_3) or "class 2" in t:
            set_fields(wa_id, eligibility_answers={"class_ok": True}, eligibility_step="income")
            return eligibility_income(lang)
        if bid == "class_lt1" or t == _norm(CLASS_LT1) or "less than" in t:
            set_fields(wa_id, eligibility_answers={"class_ok": False}, eligibility_step="done")
            clear_flow(wa_id, keep_language=True)
            reason = (
                "class must be Class 1 or Class 2 & 3."
                if lang == "en"
                else "कक्षा Class 1 या Class 2 & 3 होनी चाहिए।"
            )
            return eligibility_fail_result(reason, lang)
        return eligibility_class(lang)

    if step == "class_followup":
        if bid == "class_2_3" or t == _norm(CLASS_2_3) or "class 2" in t:
            set_fields(wa_id, eligibility_answers={"class_ok": True}, eligibility_step="income")
            return eligibility_income(lang)
        if bid == "class_lt1" or t == _norm(CLASS_LT1) or "less than" in t:
            set_fields(wa_id, eligibility_answers={"class_ok": False}, eligibility_step="done")
            clear_flow(wa_id, keep_language=True)
            reason = (
                "class must be Class 1 or Class 2 & 3."
                if lang == "en"
                else "कक्षा Class 1 या Class 2 & 3 होनी चाहिए।"
            )
            return eligibility_fail_result(reason, lang)
        return eligibility_class_followup(lang)

    if step == "income":
        if (
            bid == "income_ews"
            or t in (_norm(INCOME_EWS), _norm(INCOME_EWS_FULL), _norm(INCOME_EWS_EN))
            or "कमजोर" in text
            or "weaker" in t
            or "ews" in t
        ):
            set_fields(wa_id, eligibility_answers={"income_ok": True}, eligibility_step="done")
            clear_flow(wa_id, keep_language=True)
            return eligibility_pass_result(lang)
        if (
            bid == "income_dg"
            or t in (_norm(INCOME_DG), _norm(INCOME_DG_FULL), _norm(INCOME_DG_EN))
            or "वंचित" in text
            or "disadvantaged" in t
        ):
            set_fields(wa_id, eligibility_answers={"income_ok": True}, eligibility_step="done")
            clear_flow(wa_id, keep_language=True)
            return eligibility_pass_result(lang)
        if bid == "income_no" or t in (_norm(INCOME_NO), _norm(INCOME_NO_EN)) or "इनमें से नहीं" in text:
            set_fields(wa_id, eligibility_answers={"income_ok": False}, eligibility_step="done")
            clear_flow(wa_id, keep_language=True)
            reason = (
                "income/category condition not met."
                if lang == "en"
                else "आय/वर्ग शर्त पूरी नहीं होती।"
            )
            return eligibility_fail_result(reason, lang)
        return eligibility_income(lang)

    return None


def _handle_apply(wa_id: str | None, text: str, bid: str | None) -> dict[str, Any] | None:
    lang = _lang(wa_id)
    t = _norm(text)

    if bid == "apply_website" or t in (_norm(APPLY_WEBSITE), _norm(APPLY_WEBSITE_EN), _norm(APPLY_PORTAL)):
        return apply_website(lang)
    if bid == "apply_how" or t in (
        _norm(APPLY_HOW),
        _norm(APPLY_HOW_EN),
        _norm(APPLY_STEPS),
        "how to apply",
        "आवेदन कैसे करे",
    ):
        set_fields(wa_id, apply_step=1)
        return apply_how_all_steps(lang)
    if bid == "apply_youtube" or t in (_norm(APPLY_YOUTUBE), _norm(APPLY_YOUTUBE_EN), "youtube"):
        return apply_youtube(lang)
    if bid == "apply_problem" or t == _norm(APPLY_PROBLEM):
        set_fields(wa_id, flow="grievance", grievance_waiting=False, last_topic="grievance")
        return grievance_menu(lang)
    # Legacy next-step taps → show all steps once
    if bid == "apply_next" or t == _norm(APPLY_NEXT) or t in ("आगे", "हो गया"):
        return apply_how_all_steps(lang)
    if bid == "apply_steps" or t == _norm(APPLY_STEPS):
        return apply_how_all_steps(lang)
    if bid == "apply_portal" or t == _norm(APPLY_PORTAL):
        return apply_website(lang)

    return apply_start(lang)


def _handle_schools(wa_id: str | None, text: str, bid: str | None) -> dict[str, Any] | None:
    lang = _lang(wa_id)
    t = _norm(text)
    if (
        bid == "school_list"
        or t in (_norm(SCHOOL_LIST), _norm(SCHOOL_LIST_EN), _norm("open school list"))
    ):
        set_fields(wa_id, schools_step=1)
        return schools_list(lang)
    if bid == "school_dist" or t in (_norm(SCHOOL_DIST), _norm(SCHOOL_DIST_EN)) or "दूरी" in text or "distance" in t:
        set_fields(wa_id, schools_step=2)
        return schools_distance(lang)
    return schools_start(lang)


def _handle_docs(wa_id: str | None, text: str, bid: str | None) -> dict[str, Any] | None:
    """Docs always resolve to the single list (Feedback 4.0)."""
    lang = _lang(wa_id)
    t = _norm(text)
    if bid in ("docs_short", "docs_full", "docs_aadhaar", "docs_list") or t in (
        _norm(DOCS_SHORT),
        _norm(DOCS_LIST),
        _norm(DOCS_LIST_EN),
        _norm(DOCS_FULL),
        _norm(DOCS_FULL_BTN),
        _norm(DOCS_AADHAAR),
    ) or "लिस्ट" in text or "list" in t or "आधार" in text or "छोटी" in text or "पूरी लिस्ट" in text:
        return docs_list(lang)
    return docs_start(lang)


def _handle_grievance(wa_id: str | None, text: str, bid: str | None) -> dict[str, Any] | None:
    sess = get_session(wa_id)
    lang = sess.get("language")
    if sess.get("grievance_waiting"):
        label = sess.get("grievance_category") or ("Typed question" if lang == "en" else "स्वयं लिखा")
        clear_flow(wa_id, keep_language=True)
        return grievance_ticket(label, language=lang)

    gid = match_grievance(text, bid)
    if not gid and bid and bid.startswith("gr_"):
        gid = bid
    if gid == "gr_free":
        label = "Typed question" if lang == "en" else "स्वयं लिखा"
        set_fields(wa_id, grievance_waiting=True, grievance_category=label)
        return grievance_ask_free(lang)
    if gid:
        label = grievance_label_for_id(gid, lang)
        clear_flow(wa_id, keep_language=True)
        return grievance_ticket(label, language=lang)
    return grievance_menu(lang)


def _wrap_status_or_text(user_text: str, route: dict[str, Any], raw: str, language: str | None = None) -> dict[str, Any]:
    app_id = route.get("application_id")
    is_status = route.get("intent") == "STATUS" or route.get("domain") == "Status"
    if app_id:
        status = lookup_status(str(app_id))
        if status:
            return status_card_with_buttons(format_status_card(status), language)
        return status_card_with_buttons(raw, language)
    if is_status and not app_id:
        return {"text": raw}
    return {"text": raw}


def _llm_fallback(user_text: str, wa_id: str | None = None) -> dict[str, Any]:
    lang = _lang(wa_id)
    # Free-text eligibility before LLM
    free = try_free_text_eligibility(user_text, lang)
    if free:
        return free

    route = route_intent(user_text)
    print(f"Router result: {route}", flush=True)
    raw = generate_reply(user_text, route, language=lang)
    if not isinstance(raw, str):
        return _as_dict(raw)

    app_id = route.get("application_id")
    is_status = route.get("intent") == "STATUS" or route.get("domain") == "Status"
    if app_id or (is_status and "आवेदक का नाम" in raw):
        return _wrap_status_or_text(user_text, route, raw, lang)

    if raw.strip() == FALLBACK_HI.strip() or _looks_like_menu(raw):
        if is_grievance_like(user_text):
            clear_flow(wa_id, keep_language=True)
            label = "Typed question" if lang == "en" else "स्वयं लिखा"
            return grievance_ticket(label, language=lang)
        demo = try_demo_answer(user_text, lang)
        if demo:
            return demo
        return short_help_reply(lang)

    return {"text": raw}


def _handle_active_flow(
    wa_id: str | None,
    effective_text: str,
    bid: str | None,
    text: str,
) -> dict[str, Any] | None:
    sess = get_session(wa_id)
    flow = sess.get("flow")
    lang = sess.get("language")

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
        return status_ask_id(lang)

    if flow == "others":
        mid = match_menu(effective_text, bid)
        if mid:
            return None
        free = try_free_text_eligibility(effective_text, lang)
        if free:
            return free
        if is_grievance_like(effective_text):
            clear_flow(wa_id, keep_language=True)
            label = "Typed question" if lang == "en" else "स्वयं लिखा"
            return grievance_ticket(label, language=lang)
        demo = try_demo_answer(effective_text, lang)
        if demo:
            return demo
        if len(effective_text.split()) >= 4:
            return _llm_fallback(text, wa_id)
        return topic_chooser(lang)

    return None


def handle_message(
    user_text: str,
    wa_id: str | None = None,
    button_id: str | None = None,
) -> dict[str, Any]:
    """Return {text, buttons?, list_sections?, list_button_label?} or {replies: [...]}."""
    text = (user_text or "").strip()
    bid = (button_id or "").strip() or None

    if not text and not bid:
        return _as_dict(
            "नमस्कार। कृपया अपना प्रश्न लिखें। स्थिति, जानकारी, या शिकायत।"
        )

    effective_text = text
    if bid and not text:
        effective_text = bid

    sess = get_session(wa_id)
    lowered = _norm(effective_text)
    lang = sess.get("language")

    # GYAN application id -> status card + follow-up buttons
    gyan = GYAN_ID_RE.search(text or "")
    if gyan:
        set_fields(wa_id, awaiting_status_id=False, flow=None, last_topic="status")
        route = route_intent(text)
        raw = generate_reply(text, route, language=lang)
        return _wrap_status_or_text(text, route, raw if isinstance(raw, str) else str(raw), lang)

    # Language selection / switch — always return main_menu(new_lang)
    new_lang = match_language(effective_text, bid)
    if new_lang:
        set_fields(wa_id, language=new_lang, flow="main")
        return main_menu(new_lang)

    # Cold greeting / restart
    if lowered in _GREETINGS or bid in ("menu_main",):
        if bid == "menu_main" or lowered in {"menu", "मेनू", "start"}:
            clear_flow(wa_id, keep_language=True)
            set_fields(wa_id, flow="main")
            return main_menu(_lang(wa_id))
        if not sess.get("language"):
            set_fields(wa_id, flow="language")
            return language_prompt()
        clear_flow(wa_id, keep_language=True)
        set_fields(wa_id, flow="main")
        return main_menu(_lang(wa_id))

    # Explicit menu_* / elig_retry button ids always start that flow
    if bid and (bid.startswith("menu_") or bid == "elig_retry"):
        return _start_flow(wa_id, bid, text or effective_text)

    flow_snapshot = sess.get("flow")
    awaiting = bool(sess.get("awaiting_status_id"))

    # ACTIVE FLOW handlers BEFORE global match_menu
    if (
        flow_snapshot
        in (
            "language",
            "eligibility",
            "apply",
            "schools",
            "docs",
            "grievance",
            "status",
            "others",
        )
        or awaiting
    ):
        out = _handle_active_flow(wa_id, effective_text, bid, text)
        if out is not None:
            return out

    # Free-text eligibility (enough facts) before menu/LLM
    free = try_free_text_eligibility(effective_text, _lang(wa_id))
    if free:
        clear_flow(wa_id, keep_language=True)
        return free

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
        return _start_flow(wa_id, menu_id, text or effective_text)

    if GENERAL_INFO_RE.search(text or effective_text):
        set_fields(wa_id, flow="others", last_topic="others")
        return topic_chooser(_lang(wa_id))

    demo = try_demo_answer(effective_text, _lang(wa_id))
    if demo:
        return demo

    if is_grievance_like(effective_text) and len(effective_text.split()) >= 3:
        clear_flow(wa_id, keep_language=True)
        label = "Typed question" if _lang(wa_id) == "en" else "स्वयं लिखा"
        return grievance_ticket(label, language=_lang(wa_id))

    if flow_snapshot == "main":
        return main_menu(_lang(wa_id))

    if not get_session(wa_id).get("language"):
        set_fields(wa_id, flow="language")
        return language_prompt()

    return _llm_fallback(text, wa_id)
