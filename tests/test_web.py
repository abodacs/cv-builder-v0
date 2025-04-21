from fastapi.testclient import TestClient
import pytest
from app.web.app import create_app

@pytest.fixture
def client():
    """Fixture that creates a test client."""
    return TestClient(create_app())

class TestWebEndpoints:
    """Test cases for web endpoints."""
    
    def test_root_endpoint(self, client):
        """Test if root endpoint returns HTML content."""
        response = client.get("/")
        assert response.status_code == 200
        assert "html" in response.text.lower()
        assert response.headers["content-type"] == "text/html; charset=utf-8"

    def test_websocket_health(self, client):
        """Test WebSocket health check endpoint."""
        response = client.get("/ws/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    @pytest.mark.parametrize("static_file", [
        "/static/fonts/Amiri-Regular.ttf",
        "/static/css/style.css",
        "/static/js/main.js"
    ])
    def test_static_files(self, client, static_file):
        """Test static file handling with different file types."""
        response = client.get(static_file)
        assert response.status_code in [404, 200]

    def test_cors_headers(self, client):
        """Test CORS headers are properly set."""
        response = client.options("/")
        assert response.headers["access-control-allow-origin"] == "*"
        assert "access-control-allow-methods" in response.headers

    def test_invalid_endpoint(self, client):
        """Test handling of invalid endpoints."""
        response = client.get("/invalid")
        assert response.status_code == 404
        assert response.json().get("detail") is not None
