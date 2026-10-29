from app.services.chunking_service import chunks
from app import create_app

def test_chunks_preserve_pages():
    result=list(chunks([(3,'one two three four five')],size=3,overlap=1))
    assert [x[0] for x in result]==[3,3]
    assert result[1][2]=='three four five'


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
