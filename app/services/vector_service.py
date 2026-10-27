from pathlib import Path
from flask import current_app

def collection():
    import chromadb
    client=chromadb.PersistentClient(path=str(Path(current_app.config['DATA_DIR'])/'chroma'))
    model=current_app.config['EMBED_MODEL'].replace('/','_').replace(':','_').replace('-','_')
    return client.get_or_create_collection(name='ika_'+model,metadata={'hnsw:space':'cosine'})

def remove_document(doc_id):
    col=collection(); col.delete(where={'document_id':doc_id})

def store(doc,items,vectors):
    col=collection()
    col.upsert(ids=[x['id'] for x in items],documents=[x['text'] for x in items],embeddings=vectors,metadatas=[{'document_id':doc.id,'title':doc.original_filename,'page':x['page'],'chunk_index':x['index'],'embedding_model':current_app.config['EMBED_MODEL'],'index_version':1} for x in items])

def search(vector,doc_ids=None,n=3):
    col=collection()
    if col.count()==0:return []
    params={'query_embeddings':[vector],'n_results':min(n,col.count()),'include':['documents','metadatas','distances']}
    if doc_ids:params['where']={'document_id':{'$in':doc_ids}} if len(doc_ids)>1 else {'document_id':doc_ids[0]}
    result=col.query(**params)
    return [dict(id=i,text=t,metadata=m,distance=d) for i,t,m,d in zip(result['ids'][0],result['documents'][0],result['metadatas'][0],result['distances'][0])]
