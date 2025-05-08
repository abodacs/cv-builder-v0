import pytest

from app.core.state import CVState
from app.services.workflow import generate_prompt, process_input


@pytest.fixture
def empty_state() -> CVState:
    """Fixture providing an empty CV state."""
    return CVState()


@pytest.fixture
def en_state() -> CVState:
    """Fixture providing an English language CVState."""
    return CVState(language="en")


class TestProcessInput:
    """Test cases for input processing."""

    async def test_process_input_empty(self, empty_state: CVState) -> None:
        """Test processing empty input state."""
        result = await process_input(empty_state)
        assert result["user_input"] is None, "Empty input should return None"
        assert result["chatbot_response"] is None, "Empty input should have no response"

    async def test_process_input_invalid(self, empty_state: CVState) -> None:
        """Test processing invalid input."""
        with pytest.raises(ValueError, match="Invalid state"):
            await process_input(None)  # type: ignore


class TestPromptGeneration:
    """Test cases for prompt generation."""

    @pytest.mark.parametrize(
        ("section", "field", "expected_text", "language"),
        [
            ("personal_info", "name", "What is your full name?", "en"),
            ("personal_info", "email", "email", "en"),
            ("education", None, "education", "en"),
            ("skills", None, "مهارات", "ar"),
        ],
    )
    def test_generate_prompts(
        self, section: str, field: str, expected_text: str, language: str
    ) -> None:
        """Test generating prompts for different sections and languages."""
        state = CVState(language=language, current_section=section, current_field=field)
        result = generate_prompt(state)
        assert expected_text.lower() in result["chatbot_response"].lower()
        assert isinstance(result["chatbot_response"], str)

    def test_generate_prompt_invalid_section(self) -> None:
        """Test generating prompt for invalid section."""
        with pytest.raises(
            ValueError, match="Invalid section: invalid. Expected one of:.*"
        ):
            CVState(current_section="invalid")
