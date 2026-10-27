import queue,threading,uuid
from datetime import datetime,timezone
from pathlib import Path
from .pdf_service import extract_pages
from .chunking_service import chunks
from .ollama_service import embed
from .vector_service import store,remove_document
from ..extensions import db
from ..models import Document,IndexingJob
class Indexer:
    def __init__(self,app): self.app=app;self.jobs=queue.Queue(maxsize=100);self.worker=None
    def start(self):
        if self.worker and self.worker.is_alive():return
        self.worker=threading.Thread(target=self.loop,daemon=True,name='ika-indexer');self.worker.start()
        with self.app.app_context():
            for job in IndexingJob.query.filter(IndexingJob.status.in_(['pending','processing'])).all():
                job.status='pending';self.jobs.put(job.id)
            db.session.commit()
    def enqueue(self,document_id):
        active=IndexingJob.query.filter_by(document_id=document_id).filter(IndexingJob.status.in_(['pending','processing'])).first()
        if active:return active
        job=IndexingJob(id=str(uuid.uuid4()),document_id=document_id)
        db.session.add(job);db.session.commit()
        if self.worker:self.jobs.put_nowait(job.id)
        return job
    def loop(self):
        while True:
            job_id=self.jobs.get()
            try:
                with self.app.app_context():self.process(job_id)
            finally:self.jobs.task_done()
    def process(self,job_id):
        job=db.session.get(IndexingJob,job_id)
        if not job:return
        doc=db.session.get(Document,job.document_id)
        if not doc:return
        try:
            job.status='processing';job.started_at=datetime.now(timezone.utc);doc.status='processing';db.session.commit()
            pages=extract_pages(Path(self.app.config['DATA_DIR'])/'uploads'/doc.stored_filename)
            items=[{'id':f'{doc.id}:{p}:{i}','page':p,'index':i,'text':t} for p,i,t in chunks(pages)]
            if not items:raise ValueError('No text chunks available')
            vectors=[]
            for start in range(0,len(items),4):
                vectors.extend(embed([x['text'] for x in items[start:start+4]]))
                job.progress=min(90,int((start+4)*90/len(items)));db.session.commit()
            remove_document(doc.id);store(doc,items,vectors)
            doc.page_count=len(pages);doc.chunk_count=len(items);doc.status='indexed';doc.error_message=None;job.status='completed';job.progress=100
        except Exception as exc:
            doc.status='failed';doc.error_message=str(exc)[:400];job.status='failed';job.error_message=doc.error_message
        job.completed_at=datetime.now(timezone.utc);db.session.commit()
