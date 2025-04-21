import pytest
from app.services.workflow import process_input, generate_prompt
from app.core.state import CVState

@pytest.fixture
def empty_state():
    """Fixture providing an empty CVState."""
    return CVState()

@pytest.fixture
def en_state():
    """Fixture providing an English language CVState."""
    return CVState(language="en")

class TestProcessInput:
    """Test cases for input processing."""

    def test_process_input_empty(self, empty_state):
        """Test processing empty input state."""
        result = process_input(empty_state)
        assert result["user_input"] is None, "Empty input should return None"
        assert result["chatbot_response"] is None, "Empty input should have no response"

    def test_process_input_invalid(self, empty_state):
        """Test processing invalid input."""
        with pytest.raises(ValueError):
            process_input(None)

class TestPromptGeneration:
    """Test cases for prompt generation."""

    @pytest.mark.parametrize("section,field,expected_text,language", [
        ("personal_info", "name", "What is your full name?", "en"),
        ("personal_info", "email", "email", "en"),
        ("education", None, "education", "en"),
        ("skills", None, "مهارات", "ar"),
    ])
    def test_generate_prompts(self, section, field, expected_text, language):
        """Test generating prompts for different sections and languages."""
        state = CVState(
            language=language,
            current_section=section,
            current_field=field
        )
        result = generate_prompt(state)
        assert expected_text in result["chatbot_response"].lower()
        assert isinstance(result["chatbot_response"], str)

    def test_generate_prompt_invalid_section(self):
        """Test generating prompt for invalid section."""
        state = CVState(current_section="invalid")
        with pytest.raises(ValueError):
            generate_prompt(state)
