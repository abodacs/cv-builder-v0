from pydantic import BaseModel, Field
from typing import Dict, List, Optional

class CVState(BaseModel):
    """State model for CV builder conversation."""
    language: str = "ar"  # Default to Arabic
    personal_info: Dict[str, str] = Field(default_factory=dict)
    education: List[Dict] = Field(default_factory=list)
    work_experience: List[Dict] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    current_section: str = "personal_info"
    current_field: Optional[str] = None
    user_input: Optional[str] = None
    chatbot_response: Optional[str] = None
    cv_output: Optional[str] = None
    is_complete: bool = False

    class Config:
        """Pydantic model configuration."""
        json_encoders = {
            # Add any custom JSON encoders if needed
        }
