from typing import ClassVar

from pydantic import BaseModel, Field, field_validator


class CVState(BaseModel):
    """State model for CV builder conversation."""

    language: str = "ar"  # Default to Arabic
    personal_info: dict[str, str] = Field(
        default_factory=dict, description="User's personal information"
    )
    education: list[dict] = Field(default_factory=list)
    work_experience: list[dict] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    validation_errors: dict[str, str] = Field(default_factory=dict)
    current_section: str = "personal_info"
    current_field: str | None = None
    user_input: str | None = None
    chatbot_response: str | None = None
    cv_output: str | None = None
    is_complete: bool = False

    @property
    def is_valid(self) -> bool:
        return len(self.validation_errors) == 0

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str) -> str:
        valid_languages = ["en", "ar"]
        if v not in valid_languages:
            raise ValueError(
                f"Invalid language: {v}. Must be one of: {', '.join(valid_languages)}"
            )
        return v

    @field_validator("current_section")
    @classmethod
    def validate_section(cls, v: str) -> str:
        valid_sections = [
            "personal_info",
            "education",
            "work_experience",
            "skills",
            "finalize",
            "review",
        ]
        if v not in valid_sections:
            raise ValueError(
                f"Invalid section: {v}. Expected one of: {', '.join(valid_sections)}"
            )
        return v

    class Config:
        """Pydantic model configuration."""

        json_encoders: ClassVar[dict] = {
            # Add any custom JSON encoders if needed
        }
