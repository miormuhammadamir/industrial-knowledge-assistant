
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
