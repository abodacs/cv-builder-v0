from typing import Any

from app.core.constants import KEYWORDS


def handle_education(
    user_input: str | None, current_list: list[dict], language: str
) -> dict[str, Any]:
    return handle_list_section(
        (user_input or "").strip(), current_list, "education", "skills", language
    )


def handle_list_section(
    user_input: str, current_list: list, list_key: str, next_section: str, language: str
) -> dict[str, Any]:
    input_strip = user_input.strip()
    input_lower = input_strip.lower()
    done_keyword = KEYWORDS[language]["done"].lower()

    if input_lower == done_keyword:
        return {"current_section": next_section, "current_field": None}
    elif not input_strip:
        return {
            "current_section": list_key,
            "chatbot_response": "Please provide details or type 'done'.",
        }

    updated_list = list(current_list)
    updated_list.append({"details": input_strip})

    return {list_key: updated_list, "current_section": list_key, "current_field": None}
