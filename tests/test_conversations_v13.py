import uuid
from app.extensions import db
from app.models import Conversation, Message

def test_conversation_rename_search_and_delete(client):
    cid=str(uuid.uuid4())
    with client.application.app_context():
        db.session.add(Conversation(id=cid,title='Old title'))
        db.session.add(Message(id=str(uuid.uuid4()),conversation_id=cid,role='user',content='hello'))
        db.session.commit()
    r=client.patch(f'/api/conversations/{cid}',json={'title':'Pump diagnostics'})
    assert r.status_code==200
    assert r.json['title']=='Pump diagnostics'
    r=client.get('/api/conversations?search=Pump')
    assert any(c['id']==cid for c in r.json['conversations'])
    assert client.patch(f'/api/conversations/{cid}',json={'title':'  '}).status_code==400
    assert client.delete(f'/api/conversations/{cid}').status_code==204
    assert client.get(f'/api/conversations/{cid}').status_code==404
    with client.application.app_context():
        assert Message.query.filter_by(conversation_id=cid).count()==0
