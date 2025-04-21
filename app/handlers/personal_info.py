from typing import Dict, Any, Optional
from app.core.constants import PERSONAL_INFO_FIELDS

def handle_personal_info(user_input: str, current_personal_info: Dict[str, str], current_field: Optional[str]) -> Dict[str, Any]:
    updates: Dict[str, Any] = {}

    if not current_field:
        updates["current_field"] = PERSONAL_INFO_FIELDS[0]
        updates["current_section"] = "personal_info"
        return updates

    updated_personal_info = current_personal_info.copy()
    updated_personal_info[current_field] = user_input.strip()
    updates["personal_info"] = updated_personal_info

    try:
        current_index = PERSONAL_INFO_FIELDS.index(current_field)
        if current_index + 1 < len(PERSONAL_INFO_FIELDS):
            updates["current_field"] = PERSONAL_INFO_FIELDS[current_index + 1]
            updates["current_section"] = "personal_info"
        else:
            updates["current_section"] = "education"
            updates["current_field"] = None
    except ValueError:
        updates["current_section"] = "education"
        updates["current_field"] = None

    return updates
