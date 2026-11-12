from pathlib import Path
from flask import current_app
from . import keyword_service


def _normalize_doc_ids(doc_ids):
    if doc_ids is None:
        return None
    if isinstance(doc_ids, str):
        return [doc_ids]
    values = []
    for item in doc_ids:
        if item is None:
            continue
        value = str(item).strip()
        if value:
            values.append(value)
    return list(dict.fromkeys(values))


def collection():
    import chromadb
    client=chromadb.PersistentClient(path=str(Path(current_app.config['DATA_DIR'])/'chroma'))
    model=current_app.config['EMBED_MODEL'].replace('/','_').replace(':','_').replace('-','_')
    return client.get_or_create_collection(name='ika_'+model,metadata={'hnsw:space':'cosine'})

def remove_document(doc_id):
    col=collection(); col.delete(where={'document_id':doc_id})
    keyword_service.remove_document(doc_id)

def store(doc,items,vectors):
    col=collection()
    if len(items) != len(vectors):
        raise ValueError('Embedding count does not match the document chunk count')
    new_ids = [x['id'] for x in items]
    existing = col.get(where={'document_id': doc.id}, include=[])
    old_ids = existing.get('ids', [])
    col.upsert(ids=new_ids,documents=[x['text'] for x in items],embeddings=vectors,metadatas=[{'document_id':doc.id,'title':doc.original_filename,'page':x['page'],'chunk_index':x['index'],'embedding_model':current_app.config['EMBED_MODEL'],'index_version':1} for x in items])
    new_id_set = set(new_ids)
    obsolete_ids = [chunk_id for chunk_id in old_ids if chunk_id not in new_id_set]
    if obsolete_ids:
        col.delete(ids=obsolete_ids)
    keyword_service.replace_document(doc.id, items, doc.original_filename)

def search(vector,doc_ids=None,n=3,query=None):
    normalized_ids = _normalize_doc_ids(doc_ids)
    if normalized_ids == [] or n <= 0:
        return []
    col=collection()
    count = col.count()
    indexed = keyword_service.indexed_count()
    if indexed != count:
        keyword_service.rebuild_from_collection(col)
    candidate_count = max(n, n * 4)
    semantic = []
    if count:
        params={'query_embeddings':[vector],'n_results':min(candidate_count,count),'include':['documents','metadatas','distances']}
        if normalized_ids:
            params['where']={'document_id':{'$in':normalized_ids}} if len(normalized_ids)>1 else {'document_id':normalized_ids[0]}
        result=col.query(**params)
        semantic = [dict(id=i,text=t,metadata=m,distance=d,retrieval_method='semantic') for i,t,m,d in zip(result['ids'][0],result['documents'][0],result['metadatas'][0],result['distances'][0])]
    lexical = keyword_service.search(query, normalized_ids, limit=candidate_count) if query else []
    fused = {}
    for rank, match in enumerate(semantic, 1):
        entry = fused.setdefault(match['id'], {**match, 'hybrid_score': 0.0, 'retrieval_methods': []})
        entry['hybrid_score'] += 1.0 / (60 + rank)
        entry['retrieval_methods'].append('semantic')
    for rank, match in enumerate(lexical, 1):
        entry = fused.setdefault(match['id'], {**match, 'hybrid_score': 0.0, 'retrieval_methods': []})
        entry['hybrid_score'] += 1.0 / (60 + rank)
        entry['retrieval_methods'].append('keyword')
        entry['lexical_score'] = match['lexical_score']
    return sorted(fused.values(), key=lambda item: (-item['hybrid_score'], str(item.get('id', ''))))[:n]
