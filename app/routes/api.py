import hashlib,uuid
from pathlib import Path
from flask import Blueprint,current_app,request,jsonify
from sqlalchemy import func
from ..extensions import db
from ..models import Document,Conversation,Message,MessageSource,IndexingJob
from ..services.pdf_service import validate_pdf
from ..services.rag_service import answer
from ..services.ollama_service import request_api
from ..services.vector_service import remove_document
api=Blueprint('api',__name__)
from ..security import require_role, current_user
from .auth import audit

def error(message,code=400):return jsonify(error={'code':'request_error','message':message}),code
def doc_json(d):return dict(id=d.id,filename=d.original_filename,status=d.status,pages=d.page_count,chunks=d.chunk_count,error=d.error_message,created_at=d.created_at.isoformat())
@api.get('/dashboard/stats')
def stats():
    counts={s:Document.query.filter_by(status=s).count() for s in ['pending','processing','indexed','failed']}
    return jsonify(documents=Document.query.count(),statuses=counts,chunks=db.session.query(func.sum(Document.chunk_count)).scalar() or 0,conversations=Conversation.query.count(),questions=Message.query.filter_by(role='user').count())
@api.route('/documents',methods=['GET','POST'])
def documents():
    if request.method=='POST' and current_user().role=='viewer':return error('Editor role required',403)
    if request.method=='GET':
        query=Document.query.order_by(Document.created_at.desc())
        if request.args.get('status'):query=query.filter_by(status=request.args['status'])
        if request.args.get('search'):query=query.filter(Document.original_filename.ilike('%'+request.args['search'][:100]+'%'))
        return jsonify(documents=[doc_json(d) for d in query.limit(200)])
    file=request.files.get('file')
    if not file or not file.filename or not file.filename.lower().endswith('.pdf'):return error('Upload a PDF file')
    data=file.read(current_app.config['MAX_CONTENT_LENGTH']+1)
    if len(data)>current_app.config['MAX_CONTENT_LENGTH']:return error('File too large',413)
    digest=hashlib.sha256(data).hexdigest()
    existing=Document.query.filter_by(file_hash=digest).first()
    if existing:return jsonify(error={'code':'duplicate','message':'PDF already uploaded'},document=doc_json(existing)),409
    doc_id=str(uuid.uuid4());stored=doc_id+'.pdf';path=Path(current_app.config['DATA_DIR'])/'uploads'/stored
    path.write_bytes(data)
    try:validate_pdf(path)
    except Exception as exc:path.unlink(missing_ok=True);return error(str(exc))
    doc=Document(id=doc_id,original_filename=Path(file.filename.replace('\\','/')).name[:255],stored_filename=stored,file_hash=digest,file_size=len(data))
    db.session.add(doc);audit('document.upload','document',doc.id,doc.original_filename);db.session.commit()
    job=current_app.extensions['indexer'].enqueue(doc.id)
    return jsonify(document=doc_json(doc),job_id=job.id),202
@api.route('/documents/<doc_id>',methods=['GET','DELETE'])
def document(doc_id):
    if request.method=='DELETE' and current_user().role=='viewer':return error('Editor role required',403)
    doc=db.session.get(Document,doc_id)
    if not doc:return error('Document not found',404)
    if request.method=='GET':return jsonify(document=doc_json(doc))
    if doc.status=='processing':return error('Cannot delete while indexing',409)
    try:remove_document(doc.id)
    except Exception:return error('Vector database unavailable; deletion cancelled',503)
    (Path(current_app.config['DATA_DIR'])/'uploads'/doc.stored_filename).unlink(missing_ok=True)
    IndexingJob.query.filter_by(document_id=doc.id).delete()
    audit('document.delete','document',doc.id,doc.original_filename);db.session.delete(doc);db.session.commit()
    return '',204
@api.post('/documents/<doc_id>/reindex')
@require_role('editor')
def reindex(doc_id):
    doc=db.session.get(Document,doc_id)
    if not doc:return error('Document not found',404)
    if doc.status in ('processing','pending'):return error('Already processing',409)
    doc.status='pending';audit('document.reindex','document',doc.id);db.session.commit()
    job=current_app.extensions['indexer'].enqueue(doc.id)
    return jsonify(job_id=job.id),202
@api.get('/indexing/jobs/<job_id>')
def job(job_id):
    j=db.session.get(IndexingJob,job_id)
    if not j:return error('Job not found',404)
    return jsonify(id=j.id,document_id=j.document_id,status=j.status,progress=j.progress,error=j.error_message)
@api.route('/conversations',methods=['GET'])
def conversations():
    q=Conversation.query
    term=request.args.get('search','').strip()[:100]
    if term:q=q.filter(Conversation.title.ilike('%'+term+'%'))
    return jsonify(conversations=[{'id':c.id,'title':c.title,'updated_at':c.updated_at.isoformat()} for c in q.order_by(Conversation.updated_at.desc()).limit(100)])

@api.patch('/conversations/<cid>')
def rename_conversation(cid):
    c=db.session.get(Conversation,cid)
    if not c:return error('Conversation not found',404)
    body=request.get_json(silent=True)
    title=body.get('title') if isinstance(body,dict) else None
    if not isinstance(title,str) or not 1<=len(title.strip())<=180:return error('Title must contain 1-180 characters')
    c.title=title.strip()
    c.updated_at=__import__('datetime').datetime.now(__import__('datetime').timezone.utc)
    db.session.commit()
    return jsonify(id=c.id,title=c.title,updated_at=c.updated_at.isoformat())
@api.route('/conversations/<cid>',methods=['GET','DELETE'])
def conversation(cid):
    c=db.session.get(Conversation,cid)
    if not c:return error('Conversation not found',404)
    if request.method=='DELETE':db.session.delete(c);db.session.commit();return '',204
    return jsonify(id=c.id,title=c.title,messages=[{'role':m.role,'content':m.content,'sources':[{'document_id':s.document_id,'page':s.page_number,'chunk_id':s.chunk_id,'excerpt':s.source_excerpt} for s in m.sources]} for m in sorted(c.messages,key=lambda m:m.created_at)])
@api.post('/chat')
def chat():
    body=request.get_json(silent=True) or {};question=body.get('question');ids=body.get('document_ids')
    if not isinstance(question,str) or not 1<=len(question.strip())<=2000:return error('Question must contain 1-2000 characters')
    if ids is not None and (not isinstance(ids,list) or len(ids)>100 or any(not isinstance(x,str) for x in ids)):return error('Invalid document filters')
    cid=body.get('conversation_id');c=db.session.get(Conversation,cid) if cid else None
    if cid and not c:return error('Conversation not found',404)
    try:result=answer(question.strip(),ids)
    except Exception as exc:current_app.logger.warning('RAG failure: %s',exc);return error('AI service unavailable. Check Ollama and ChromaDB.',503)
    if not c:c=Conversation(id=str(uuid.uuid4()),title=question[:70]);db.session.add(c)
    user=Message(id=str(uuid.uuid4()),conversation_id=c.id,role='user',content=question)
    assistant=Message(id=str(uuid.uuid4()),conversation_id=c.id,role='assistant',content=result['answer'])
    db.session.add_all([user,assistant]);db.session.flush()
    for s in result['sources']:db.session.add(MessageSource(message_id=assistant.id,document_id=s['document_id'],page_number=s['page'],chunk_id=s['chunk_id'],source_excerpt=s['excerpt']))
    db.session.commit();return jsonify(conversation_id=c.id,**result)
@api.get('/models')
def models():
    try:return jsonify(available=True,models=request_api('tags').get('models',[]),active=current_app.config['OLLAMA_MODEL'])
    except RuntimeError:return jsonify(available=False,models=[],active=current_app.config['OLLAMA_MODEL'])
@api.get('/system/health')
def health():
    try:request_api('tags');ollama='online'
    except RuntimeError:ollama='offline'
    try:
        from ..services.vector_service import collection
        collection().count();vector='online'
    except Exception:vector='unavailable'
    return jsonify(application='online',ollama=ollama,vector_database=vector)

@api.get('/documents/<doc_id>/jobs')
def document_jobs(doc_id):
    doc=db.session.get(Document,doc_id)
    if not doc:return error('Document not found',404)
    jobs=IndexingJob.query.filter_by(document_id=doc_id).order_by(IndexingJob.started_at.desc()).limit(10).all()
    return jsonify(jobs=[{'id':j.id,'status':j.status,'progress':j.progress,
                          'error':('Indexing failed. Check server logs.' if j.error_message else None)} for j in jobs])
