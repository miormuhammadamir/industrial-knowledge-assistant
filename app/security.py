"""Session authentication and role-based access controls."""
from functools import wraps
from flask import session, jsonify, g, request
from .extensions import db
from .models import User

ROLE_LEVEL = {'viewer': 1, 'editor': 2, 'admin': 3}

def current_user():
    if not hasattr(g, 'ika_user'):
        uid = session.get('user_id')
        g.ika_user = db.session.get(User, uid) if uid else None
        if g.ika_user is not None and not g.ika_user.is_active:
            session.clear()
            g.ika_user = None
    return g.ika_user

def require_role(min_role='viewer'):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = current_user()
            if not user:
                return jsonify(error={'code':'unauthorized','message':'Please sign in.'}), 401
            if ROLE_LEVEL.get(user.role, 0) < ROLE_LEVEL[min_role]:
                return jsonify(error={'code':'forbidden','message':'Insufficient permissions.'}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator

def csrf_guard():
    """Require same-origin request plus a session-bound CSRF token for mutations."""
    if request.method in ('GET', 'HEAD', 'OPTIONS'):
        return None
    # Login is also CSRF protected by requiring a JSON request and custom header.
    if not request.is_json and not request.path.endswith('/documents') and '/documents/' not in request.path:
        return jsonify(error={'code':'bad_request','message':'JSON request required.'}), 400
    expected = session.get('csrf_token')
    supplied = request.headers.get('X-CSRF-Token')
    if not expected or not supplied or supplied != expected:
        return jsonify(error={'code':'csrf','message':'Invalid CSRF token.'}), 403
    return None
