import pytest
from app.core.state import CVState
from app.handlers.personal_info import handle_personal_info
from app.handlers.education import handle_education
from app.handlers.experience import handle_experience
from app.handlers.skills import handle_skills
from app.handlers.finalize import handle_finalize
from app.core.constants import PERSONAL_INFO_FIELDS

@pytest.fixture
def empty_state():
    """Fixture providing an empty CVState."""
    return CVState()

@pytest.fixture
def personal_info():
    """Fixture providing sample personal info."""
    return {"name": "John", "email": "john@example.com"}

class TestPersonalInfoHandler:
    """Test cases for personal information handler."""

    @pytest.mark.parametrize("field,value,next_field", [
        ("name", "John Doe", "email"),
        ("email", "john@example.com", "phone"),
        ("phone", "+1234567890", "address"),
    ])
    def test_handle_personal_info_fields(self, field, value, next_field):
        """Test handling of different personal info fields."""
        result = handle_personal_info(value, {}, field)
        assert result["personal_info"][field] == value, f"Should set {field} correctly"
        assert result["current_field"] == next_field, f"Should move to {next_field}"
        assert result["current_section"] == "personal_info"

    def test_handle_personal_info_last_field(self):
        """Test handling the last personal info field."""
        result = handle_personal_info("123 Main St", {"name": "John"}, "address")
        assert result["personal_info"]["address"] == "123 Main St"
        assert result["current_section"] == "education"
        assert result["current_field"] is None

class TestEducationHandler:
    """Test cases for education handler."""

    @pytest.mark.parametrize("language", ["ar", "en"])
    def test_handle_education_add_entry(self, language):
        """Test adding education entries in different languages."""
        education = "BSc Computer Science"
        result = handle_education(education, [], language)
        assert len(result["education"]) == 1
        assert result["education"][0]["details"] == education
        assert result["current_section"] == "education"

    def test_handle_education_done(self):
        """Test completing education section."""
        result = handle_education("done", [], "en")
        assert result["current_section"] == "skills"
        assert result["current_field"] is None

class TestExperienceHandler:
    """Test cases for work experience handler."""

    def test_handle_experience_add_entry(self):
        """Test adding work experience entries."""
        experience = "Software Engineer at Tech Corp"
        result = handle_experience(experience, [], "ar")
        assert len(result["work_experience"]) == 1
        assert result["work_experience"][0]["details"] == experience
        assert result["current_section"] == "work_experience"

    def test_handle_experience_invalid_input(self):
        """Test handling invalid experience input."""
        with pytest.raises(ValueError):
            handle_experience("", [], "ar")
