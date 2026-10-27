import os
from pathlib import Path
from flask import Flask, jsonify
from dotenv import load_dotenv
from .extensions import db
from .services.indexing_service import Indexer

def create_app(test_config=None):
    load_dotenv()
    app=Flask(__name__,instance_relative_config=True)
    base=Path(app.instance_path).parent
    app.config.update(SECRET_KEY=os.getenv('SECRET_KEY','local-dev-only'),SQLALCHEMY_DATABASE_URI='sqlite:///'+str(base/'data'/'ika.sqlite3'),SQLALCHEMY_TRACK_MODIFICATIONS=False,MAX_CONTENT_LENGTH=int(os.getenv('MAX_UPLOAD_MB','25'))*1024*1024,DATA_DIR=str(base/'data'),OLLAMA_URL=os.getenv('OLLAMA_URL','http://127.0.0.1:11434'),OLLAMA_MODEL=os.getenv('OLLAMA_MODEL','llama3.2:3b'),OLLAMA_FALLBACK=os.getenv('OLLAMA_FALLBACK','llama3.2:1b'),EMBED_MODEL=os.getenv('EMBED_MODEL','nomic-embed-text'),TESTING=False)
    if test_config: app.config.update(test_config)
    Path(app.config['DATA_DIR'],'uploads').mkdir(parents=True,exist_ok=True)
    db.init_app(app)
    from . import models
    with app.app_context(): db.create_all()
    from .routes.api import api
    from .routes.pages import pages
    app.register_blueprint(api,url_prefix='/api');app.register_blueprint(pages)
    app.extensions['indexer']=Indexer(app)
    if not app.config['TESTING']: app.extensions['indexer'].start()
    @app.errorhandler(413)
    def too_large(e): return jsonify(error={'code':'too_large','message':'Upload exceeds size limit'}),413
    return app
