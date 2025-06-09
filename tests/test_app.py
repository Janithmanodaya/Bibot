import pytest
from app import create_app

@pytest.fixture
def app():
    app = create_app()
    app.config.update({
        "TESTING": True,
    })
    # TODO: Add any specific test configurations here, e.g., test database
    yield app

@pytest.fixture
def client(app):
    return app.test_client()

def test_index_page(client):
    """Test that the index page loads correctly."""
    response = client.get('/')
    assert response.status_code == 200
    assert b"Welcome to the Automated Trading Bot" in response.data
