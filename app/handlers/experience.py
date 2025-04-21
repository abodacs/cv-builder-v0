from typing import List, Dict, Any
from .education import handle_list_section

def handle_experience(user_input: str, current_list: List[Dict], language: str) -> Dict[str, Any]:
    return handle_list_section(user_input, current_list, "work_experience", "finalize", language)
