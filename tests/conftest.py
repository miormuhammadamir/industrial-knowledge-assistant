
import pytest

from app import create_app
from app.extensions import db


@pytest.fixture
def app(tmp_path):
    """Create an isolated Flask application for each test."""

    data_dir = tmp_path / "data"
    database_path = tmp_path / "test.sqlite3"

    test_app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": (
                f"sqlite:///{database_path.as_posix()}"
            ),
            "DATA_DIR": str(data_dir),
            "SECRET_KEY": "test-only-secret-key",
        }
    )

    yield test_app

    with test_app.app_context():
        db.session.remove()
        db.engine.dispose()


@pytest.fixture
def client(app):
    """Provide a Flask test client."""
    return app.test_client()


from werkzeug.security import generate_password_hash
from app.models import User


@pytest.fixture
def admin_client(client):
    """Provide an authenticated administrator for API tests."""

    with client.application.app_context():
        admin = User(
            username="testadmin",
            display_name="Test Administrator",
            password_hash=generate_password_hash(
                "TestAdminPassword123!"
            ),
            role="admin",
            is_active=True,
        )

        db.session.add(admin)
        db.session.commit()

    # Obtain the CSRF token before submitting login.
    session_response = client.get("/api/auth/session")

    assert session_response.status_code == 200

    csrf_token = session_response.get_json()["csrf_token"]

    response = client.post(
        "/api/auth/login",
        json={
            "username": "testadmin",
            "password": "TestAdminPassword123!",
        },
        headers={
            "X-CSRF-Token": csrf_token,
        },
    )

    assert response.status_code == 200, response.get_json()

    new_csrf_token = response.get_json()["csrf_token"]

    client.environ_base["HTTP_X_CSRF_TOKEN"] = new_csrf_token

    return client
  
