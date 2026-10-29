
import uuid

from app.extensions import db
from app.models import Conversation, Message


def test_conversation_rename_search_and_delete(admin_client):
    client = admin_client
    cid = str(uuid.uuid4())

    # Create a test conversation and message.
    with client.application.app_context():
        db.session.add(
            Conversation(
                id=cid,
                title="Old title",
            )
        )

        db.session.add(
            Message(
                id=str(uuid.uuid4()),
                conversation_id=cid,
                role="user",
                content="hello",
            )
        )

        db.session.commit()

    # Test conversation renaming.
    response = client.patch(
        f"/api/conversations/{cid}",
        json={"title": "Pump diagnostics"},
    )

    assert response.status_code == 200
    assert response.json["title"] == "Pump diagnostics"

    # Test conversation searching.
    response = client.get(
        "/api/conversations?search=Pump"
    )

    assert response.status_code == 200
    assert any(
        conversation["id"] == cid
        for conversation in response.json["conversations"]
    )

    # Test invalid conversation title.
    response = client.patch(
        f"/api/conversations/{cid}",
        json={"title": "  "},
    )

    assert response.status_code == 400

    # Delete the conversation ONCE.
    response = client.delete(
        f"/api/conversations/{cid}",
        json={},
    )

    print("DELETE status:", response.status_code)
    print(
        "DELETE response:",
        response.get_data(as_text=True),
    )

    assert response.status_code == 204

    # Verify the conversation no longer exists.
    response = client.get(
        f"/api/conversations/{cid}"
    )

    assert response.status_code == 404

    # Verify related messages were deleted.
    with client.application.app_context():
        assert (
            Message.query.filter_by(
                conversation_id=cid
            ).count()
            == 0
        )
