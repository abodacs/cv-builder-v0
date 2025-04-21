from typing import Any

from .education import handle_list_section


def handle_experience(
    user_input: str | None, current_list: list[dict], language: str
) -> dict[str, Any]:
    return handle_list_section(
        (user_input or "").strip(),
        current_list,
        "work_experience",
        "finalize",
        language,
    )
