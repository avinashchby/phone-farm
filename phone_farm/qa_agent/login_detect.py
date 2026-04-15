"""Heuristic login screen detection and field extraction."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET

_LOGIN_TEXTS = re.compile(r"\b(sign in|log in|login|register|sign up|continue with)\b", re.IGNORECASE)
_EMAIL_IDS = re.compile(r"(email|username|user|phone)", re.IGNORECASE)


def detect_login_screen(xml: str) -> bool:
    """Return True if the screen appears to be a login/auth screen.

    Heuristics: password field, login-text buttons, OAuth buttons.
    """
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return False

    for node in root.iter():
        input_type = node.get("inputType", "")
        text = node.get("text", "")
        content_desc = node.get("content-desc", "")
        if "textPassword" in input_type:
            return True
        if _LOGIN_TEXTS.search(text) or _LOGIN_TEXTS.search(content_desc):
            return True
    return False


def extract_login_fields(xml: str) -> dict:
    """Extract login form field resource-ids from screen XML.

    Returns {"email_field": str|None, "password_field": str|None, "submit_button": str|None}.
    """
    result: dict = {"email_field": None, "password_field": None, "submit_button": None}
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return result

    for node in root.iter():
        rid = node.get("resource-id", "")
        input_type = node.get("inputType", "")
        text = node.get("text", "")
        tag = node.tag  # Android XML: tag is the widget class e.g. "android.widget.Button"

        if "textPassword" in input_type and not result["password_field"]:
            result["password_field"] = rid

        if _EMAIL_IDS.search(rid) and "EditText" in tag and not result["email_field"]:
            result["email_field"] = rid

        if "Button" in tag and _LOGIN_TEXTS.search(text) and not result["submit_button"]:
            result["submit_button"] = rid

    return result
