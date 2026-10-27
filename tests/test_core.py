from app.services.chunking_service import chunks
from app import create_app

def test_chunks_preserve_pages():
    result=list(chunks([(3,'one two three four five')],size=3,overlap=1))
    assert [x[0] for x in result]==[3,3]
    assert result[1][2]=='three four five'

def test_app_starts_without_ollama(tmp_path):
    app=create_app({'TESTING':True,'DATA_DIR':str(tmp_path),'SQLALCHEMY_DATABASE_URI':'sqlite:///'+str(tmp_path/'test.db')})
    client=app.test_client()
    assert client.get('/').status_code==200
    assert client.get('/api/dashboard/stats').json['documents']==0
    assert client.post('/api/chat',json={'question':''}).status_code==400
    assert client.post('/api/documents',data={}).status_code==400
