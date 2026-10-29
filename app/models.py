from datetime import datetime,timezone
from .extensions import db

def now(): return datetime.now(timezone.utc)
class Document(db.Model):
    id=db.Column(db.String(36),primary_key=True)
    original_filename=db.Column(db.String(255),nullable=False)
    stored_filename=db.Column(db.String(100),nullable=False,unique=True)
    file_hash=db.Column(db.String(64),nullable=False,unique=True,index=True)
    file_size=db.Column(db.Integer,nullable=False)
    page_count=db.Column(db.Integer,default=0)
    chunk_count=db.Column(db.Integer,default=0)
    status=db.Column(db.String(24),default='pending',index=True)
    error_message=db.Column(db.Text)
    created_at=db.Column(db.DateTime(timezone=True),default=now)
    updated_at=db.Column(db.DateTime(timezone=True),default=now,onupdate=now)
class Conversation(db.Model):
    id=db.Column(db.String(36),primary_key=True)
    title=db.Column(db.String(180),nullable=False)
    created_at=db.Column(db.DateTime(timezone=True),default=now)
    updated_at=db.Column(db.DateTime(timezone=True),default=now,onupdate=now)
    messages=db.relationship('Message',cascade='all,delete-orphan',backref='conversation')
class Message(db.Model):
    id=db.Column(db.String(36),primary_key=True)
    conversation_id=db.Column(db.String(36),db.ForeignKey('conversation.id'),nullable=False,index=True)
    role=db.Column(db.String(20),nullable=False)
    content=db.Column(db.Text,nullable=False)
    created_at=db.Column(db.DateTime(timezone=True),default=now)
    sources=db.relationship('MessageSource',cascade='all,delete-orphan')
class MessageSource(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    message_id=db.Column(db.String(36),db.ForeignKey('message.id'),nullable=False)
    document_id=db.Column(db.String(36),nullable=False)
    page_number=db.Column(db.Integer,nullable=False)
    chunk_id=db.Column(db.String(150),nullable=False)
    source_excerpt=db.Column(db.Text,nullable=False)
class IndexingJob(db.Model):
    id=db.Column(db.String(36),primary_key=True)
    document_id=db.Column(db.String(36),db.ForeignKey('document.id'),nullable=False,index=True)
    status=db.Column(db.String(24),default='pending')
    progress=db.Column(db.Integer,default=0)
    started_at=db.Column(db.DateTime(timezone=True))
    completed_at=db.Column(db.DateTime(timezone=True))
    error_message=db.Column(db.Text)


class User(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    username=db.Column(db.String(40),unique=True,nullable=False,index=True)
    display_name=db.Column(db.String(120),nullable=False)
    password_hash=db.Column(db.String(255),nullable=False)
    role=db.Column(db.String(12),nullable=False,default='viewer')
    is_active=db.Column(db.Boolean,nullable=False,default=True)
    created_at=db.Column(db.DateTime(timezone=True),default=now,nullable=False)

class AuditEvent(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    actor_id=db.Column(db.Integer,db.ForeignKey('user.id'),nullable=True)
    action=db.Column(db.String(80),nullable=False)
    entity_type=db.Column(db.String(40),nullable=False)
    entity_id=db.Column(db.String(80))
    details=db.Column(db.String(500))
    created_at=db.Column(db.DateTime(timezone=True),default=now,nullable=False)
