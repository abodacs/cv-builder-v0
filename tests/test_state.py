import pytest
from app.core.state import CVState

@pytest.fixture
def default_state():
    """Fixture providing a default CVState instance."""
    return CVState()

@pytest.fixture
def populated_state():
    """Fixture providing a CVState instance with sample data."""
    return CVState(
        personal_info={"name": "John", "email": "john@example.com"},
        education=[{"details": "BSc"}],
        skills=["Python", "Testing"]
    )

class TestCVState:
    """Test cases for CV state management."""

    def test_state_initialization(self, default_state):
        """Test default state initialization."""
        assert default_state.language == "ar", "Default language should be Arabic"
        assert default_state.current_section == "personal_info", "Should start with personal info"
        assert not default_state.is_complete, "New state should not be complete"
        assert all(isinstance(attr, list) for attr in [
            default_state.education,
            default_state.work_experience,
            default_state.skills
        ]), "List attributes should be empty lists"

    def test_state_serialization(self, populated_state):
        """Test state serialization and deserialization."""
        serialized = populated_state.model_dump_json()
        deserialized = CVState.model_validate_json(serialized)
        
        assert deserialized.dict() == populated_state.dict(), "Serialization should preserve all data"

    def test_state_validation(self):
        """Test state validation rules."""
        with pytest.raises(ValueError):
            CVState(language="invalid")
        
        with pytest.raises(ValueError):
            CVState(current_section="invalid_section")

    def test_state_completion(self, populated_state):
        """Test state completion logic."""
        populated_state.is_complete = True
        assert populated_state.is_complete, "Should allow marking state as complete"
        
        serialized = populated_state.model_dump_json()
        deserialized = CVState.model_validate_json(serialized)
        assert deserialized.is_complete, "Completion status should persist after serialization"
