from app.services.chunking_service import chunks
from app import create_app

def test_chunks_preserve_pages():
    result=list(chunks([(3,'one two three four five')],size=3,overlap=1))
    assert [x[0] for x in result]==[3,3]
    assert 'three' in result[0][2]
    assert 'three' in result[1][2]


def test_chunks_repeat_section_heading_and_preserve_line_context():
    text = '1. Pump specifications\nMotor rating is 7.5 kW.\nNominal speed is 1450 rpm.'
    result = list(chunks([(2, text)], size=12, overlap=3))

    assert len(result) > 1
    assert all(item[0] == 2 for item in result)
    assert all(item[2].startswith('1. Pump specifications') for item in result)


def test_app_starts_without_ollama(tmp_path):
    app = create_app({
        "TESTING": True,
        "DATA_DIR": str(tmp_path),
        "SQLALCHEMY_DATABASE_URI": (
            "sqlite:///" + str(tmp_path / "test.db")
        ),
    })

    client = app.test_client()

    # Public application page should load.
    assert client.get("/").status_code == 200

    # Protected dashboard must reject anonymous access.
    response = client.get("/api/dashboard/stats")

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "unauthorized"


def test_authenticated_dashboard(admin_client):
    response = admin_client.get("/api/dashboard/stats")

    assert response.status_code == 200

    data = response.get_json()

    assert data["documents"] == 0
    assert data["conversations"] == 0


def test_create_admin_cli_bootstraps_first_account(app):
    result = app.test_cli_runner().invoke(
        args=["create-admin"],
        input="ikaadmin\nIKA Administrator\nVerySecurePassword123!\nVerySecurePassword123!\n",
    )

    assert result.exit_code == 0, result.output
    assert "Administrator 'ikaadmin' created." in result.output

    from app.models import User
    from werkzeug.security import check_password_hash

    with app.app_context():
        admin = User.query.filter_by(username="ikaadmin").one()
        assert admin.role == "admin"
        assert check_password_hash(admin.password_hash, "VerySecurePassword123!")


def test_create_admin_cli_refuses_second_bootstrap(admin_client):
    result = admin_client.application.test_cli_runner().invoke(
        args=["create-admin"],
        input="",
    )

    assert result.exit_code != 0
    assert "An administrator already exists." in result.output


def test_generated_secret_is_random_and_persistent(tmp_path):
    config = {
        "TESTING": True,
        "SECRET_KEY": "change-this-local-secret",
        "DATA_DIR": str(tmp_path / "data"),
        "SQLALCHEMY_DATABASE_URI": (
            "sqlite:///" + str(tmp_path / "test.db")
        ),
    }

    first = create_app(config)
    second = create_app(config)

    assert first.secret_key != "change-this-local-secret"
    assert first.secret_key == second.secret_key
    assert len(first.secret_key) >= 32
