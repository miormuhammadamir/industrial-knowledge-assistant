import os
import re
import secrets
from pathlib import Path
import click
from flask import Flask, jsonify
from dotenv import load_dotenv
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash
from .extensions import db
from .services.indexing_service import Indexer


def _resolve_secret_key(data_dir, configured):
    placeholders = {'', 'local-dev-only', 'change-this-local-secret'}
    if configured and configured not in placeholders:
        return configured

    secret_path = Path(data_dir) / '.secret_key'
    secret_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        value = secrets.token_urlsafe(48)
        with secret_path.open('x', encoding='utf-8') as secret_file:
            secret_file.write(value)
        return value
    except FileExistsError:
        value = secret_path.read_text(encoding='utf-8').strip()
        if len(value) < 32:
            raise RuntimeError('The local secret key file is invalid; remove it and restart the app.')
        return value


def create_app(test_config=None):
    load_dotenv()
    app=Flask(__name__,instance_relative_config=True)
    base=Path(app.instance_path).parent
    app.config.update(SECRET_KEY=os.getenv('SECRET_KEY'),SQLALCHEMY_DATABASE_URI='sqlite:///'+str(base/'data'/'ika.sqlite3'),SQLALCHEMY_TRACK_MODIFICATIONS=False,MAX_CONTENT_LENGTH=int(os.getenv('MAX_UPLOAD_MB','25'))*1024*1024,DATA_DIR=str(base/'data'),OLLAMA_URL=os.getenv('OLLAMA_URL','http://127.0.0.1:11434'),OLLAMA_MODEL=os.getenv('OLLAMA_MODEL','llama3.2:3b'),OLLAMA_FALLBACK=os.getenv('OLLAMA_FALLBACK','llama3.2:1b'),EMBED_MODEL=os.getenv('EMBED_MODEL','nomic-embed-text'),TESTING=False)
    if test_config: app.config.update(test_config)
    Path(app.config['DATA_DIR']).mkdir(parents=True,exist_ok=True)
    app.config['SECRET_KEY'] = _resolve_secret_key(
        app.config['DATA_DIR'], app.config.get('SECRET_KEY')
    )
    Path(app.config['DATA_DIR'],'uploads').mkdir(parents=True,exist_ok=True)
    db.init_app(app)
    from . import models
    with app.app_context(): db.create_all()

    @app.cli.command('create-admin')
    def create_admin():
        """Create the first administrator account for a fresh installation."""
        from .models import User

        if User.query.filter_by(role='admin').first():
            raise click.ClickException('An administrator already exists.')

        username = click.prompt('Username').strip().lower()
        if not re.fullmatch(r'[a-zA-Z0-9_.-]{3,40}', username):
            raise click.ClickException(
                'Username must be 3-40 letters, digits, dots, underscores or dashes.'
            )
        if User.query.filter(db.func.lower(User.username) == username).first():
            raise click.ClickException('Username already exists.')

        display_name = click.prompt('Display name').strip()
        if not 1 <= len(display_name) <= 120:
            raise click.ClickException('Display name must contain 1-120 characters.')

        password = click.prompt(
            'Password', hide_input=True, confirmation_prompt=True
        )
        if not 12 <= len(password) <= 128:
            raise click.ClickException('Password must contain 12-128 characters.')

        db.session.add(User(
            username=username,
            display_name=display_name,
            password_hash=generate_password_hash(password),
            role='admin',
        ))
        try:
            db.session.commit()
        except IntegrityError as exc:
            db.session.rollback()
            raise click.ClickException('Could not create administrator; username may already exist.') from exc
        click.echo(f"Administrator '{username}' created.")

    from .routes.api import api
    from .routes.pages import pages
    app.register_blueprint(api,url_prefix='/api');app.register_blueprint(pages)
    from .routes.auth import auth
    from .security import csrf_guard
    app.register_blueprint(auth,url_prefix='/api')
    @app.before_request
    def protect_api():
        from flask import request, jsonify
        from .security import current_user
        if not request.path.startswith('/api/'):
            return None
        if request.method not in ('GET','HEAD','OPTIONS'):
            rejection=csrf_guard()
            if rejection:return rejection
        if request.path in ('/api/auth/session','/api/auth/login'):
            return None
        if current_user() is None:
            return jsonify(error={'code':'unauthorized','message':'Please sign in.'}),401
        return None
    app.config.update(SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_SECURE=os.getenv('IKA_HTTPS','0')=='1')

    app.extensions['indexer']=Indexer(app)
    if not app.config['TESTING']: app.extensions['indexer'].start()
    @app.errorhandler(413)
    def too_large(e): return jsonify(error={'code':'too_large','message':'Upload exceeds size limit'}),413
    return app
