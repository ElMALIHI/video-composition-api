"""
Tests for the /compose endpoint with new format.
"""

from fastapi.testclient import TestClient

from main import app

# Create a TestClient instance
client = TestClient(app)

# Example composition request data
composition_data = {
    "scenes": {
        "Scene 1": {
            "source": "https://i.ibb.co/Xxjt47yJ/generate.jpg",
            "media_type": "image/video",
            "duration": 3.0,
            "transition": "fade"
        },
        "Scene 2": {
            "source": "https://i.ibb.co/1GPcCXCB/generate.jpg",
            "media_type": "image/video",
            "duration": 5.0,
            "transition": "slide_left"
        }
    },
    "output_format": "mp4",
    "quality": "1080p",
    "fps": 30,
    "priority": "normal",
    "composition_settings": {
        "background_color": "black",
        "crossfade_audio": True
    },
    "webhook_url": None,
    "metadata": {}
}


def test_compose_with_new_format():
    """Test /compose endpoint with new format."""
    headers = {"Authorization": "Bearer dev-key-123", "Content-Type": "application/json"}
    response = client.post("/compose", json=composition_data, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "job" in data
    assert data["job"]["title"] == "Composition: Scene 1, Scene 2"
    assert data["job"]["status"] == "pending"
