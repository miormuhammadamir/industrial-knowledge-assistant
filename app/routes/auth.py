"""Authentication, user profile, admin users, and audit API."""
import secrets
from datetime import datetime, timezone
from flask import Blueprint, jsonify, request, session, current_app
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy import func
from ..extensions import db
from ..models import User, AuditEvent
from ..security import current_user, require_role

auth = Blueprint('auth', __name__)

def public_user(user):
    return {'id':user.id, 'username':user.username, 'display_name':user.display_name,
            'role':user.role, 'active':user.is_active, 'created_at':user.created_at.isoformat()}

def audit(action, entity_type, entity_id=None, details=None):
    user = current_user()
    db.session.add(AuditEvent(actor_id=user.id if user else None, action=action,
        entity_type=entity_type, entity_id=str(entity_id) if entity_id else None,
        details=(details or '')[:500]))

def err(message, status=400):
    return jsonify(error={'message':message}), status

@auth.get('/auth/session')
def get_session():
    token = session.get('csrf_token')
    if not token:
        token = secrets.token_urlsafe(32)
        session['csrf_token'] = token
    user = current_user()
    return jsonify(user=public_user(user) if user else None, csrf_token=token)

@auth.post('/auth/login')
def login():
    body=request.get_json(silent=True) or {}
    username=str(body.get('username','')).strip().lower()
    password=body.get('password','')
    if not username or not isinstance(password,str): return err('Invalid credentials',401)
    user=User.query.filter(func.lower(User.username)==username).first()
    if not user or not user.is_active or not check_password_hash(user.password_hash,password):
        return err('Invalid credentials',401)
    session.clear()
    session['user_id']=user.id
    session['csrf_token']=secrets.token_urlsafe(32)
    audit('login','user',user.id)
    db.session.commit()
    return jsonify(user=public_user(user),csrf_token=session['csrf_token'])

@auth.post('/auth/logout')
@require_role()
def logout():
    audit('logout','user',current_user().id)
    db.session.commit()
    session.clear()
    return '',204

@auth.get('/auth/me')
@require_role()
def me(): return jsonify(user=public_user(current_user()))

@auth.patch('/auth/me')
@require_role()
def edit_profile():
    body=request.get_json(silent=True) or {}
    user=current_user()
    name=body.get('display_name')
    if not isinstance(name,str) or not 1<=len(name.strip())<=120: return err('Display name must be 1-120 characters')
    user.display_name=name.strip()
    audit('profile.update','user',user.id)
    db.session.commit()
    return jsonify(user=public_user(user))

@auth.post('/auth/change-password')
@require_role()
def change_password():
    body=request.get_json(silent=True) or {}
    old,new=body.get('current_password'),body.get('new_password')
    user=current_user()
    if not isinstance(old,str) or not check_password_hash(user.password_hash,old): return err('Current password is incorrect',403)
    if not isinstance(new,str) or len(new)<12 or len(new)>128: return err('Password must be 12-128 characters')
    user.password_hash=generate_password_hash(new)
    audit('password.change','user',user.id)
    db.session.commit()
    return jsonify(ok=True)

@auth.get('/admin/users')
@require_role('admin')
def list_users(): return jsonify(users=[public_user(u) for u in User.query.order_by(User.username).all()])

@auth.post('/admin/users')
@require_role('admin')
def create_user():
    body=request.get_json(silent=True) or {}
    username=body.get('username'); password=body.get('password'); role=body.get('role','viewer'); name=body.get('display_name')
    if not isinstance(username,str) or not __import__('re').fullmatch(r'[A-Za-z0-9_.-]{3,40}',username): return err('Username must be 3-40 letters, digits, dots, underscores or dashes')
    if not isinstance(password,str) or not 12<=len(password)<=128: return err('Password must be 12-128 characters')
    if role not in ('viewer','editor','admin'): return err('Invalid role')
    if not isinstance(name,str) or not 1<=len(name.strip())<=120: return err('Display name required')
    if User.query.filter(func.lower(User.username)==username.lower()).first(): return err('Username already exists',409)
    user=User(username=username.lower(),display_name=name.strip(),password_hash=generate_password_hash(password),role=role)
    db.session.add(user);db.session.flush();audit('user.create','user',user.id)
    db.session.commit()
    return jsonify(user=public_user(user)),201

@auth.patch('/admin/users/<int:uid>')
@require_role('admin')
def update_user(uid):
    user=db.session.get(User,uid)
    if not user:return err('User not found',404)
    body=request.get_json(silent=True) or {}
    if 'role' in body:
        if body['role'] not in ('viewer','editor','admin'):return err('Invalid role')
        if user.id==current_user().id and body['role']!='admin':return err('Cannot demote yourself',409)
        user.role=body['role']
    if 'active' in body:
        if not isinstance(body['active'],bool):return err('Invalid active value')
        if user.id==current_user().id and not body['active']:return err('Cannot deactivate yourself',409)
        user.is_active=body['active']
    audit('user.update','user',uid)
    db.session.commit()
    return jsonify(user=public_user(user))

@auth.get('/admin/audit')
@require_role('admin')
def list_audit():
    events=AuditEvent.query.order_by(AuditEvent.id.desc()).limit(200).all()
    return jsonify(events=[{'id':e.id,'actor_id':e.actor_id,'action':e.action,
      'entity_type':e.entity_type,'entity_id':e.entity_id,'details':e.details,
      'created_at':e.created_at.isoformat()} for e in events])
