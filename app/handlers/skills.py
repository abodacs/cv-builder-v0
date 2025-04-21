from typing import Any

from app.core.constants import KEYWORDS


def handle_skills(
    user_input: str | None, current_list: list[str], language: str
) -> dict[str, Any]:
    input_strip = (user_input or "").strip()
    input_lower = input_strip.lower()
    done_keyword = KEYWORDS[language]["done"].lower()

    if input_lower == done_keyword:
        return {"current_section": "finalize", "current_field": None}
    elif not input_strip:
        return {
            "current_section": "skills",
            "chatbot_response": "Please provide a skill or type 'done'.",
        }

    updated_list = list(current_list)
    updated_list.append(input_strip)

    return {"skills": updated_list, "current_section": "skills", "current_field": None}
