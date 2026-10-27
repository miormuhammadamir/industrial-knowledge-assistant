import requests
from flask import current_app

def request_api(path,payload=None,timeout=90):
    url=current_app.config['OLLAMA_URL'].rstrip('/')+'/api/'+path
    try:
        response=requests.post(url,json=payload,timeout=timeout) if payload is not None else requests.get(url,timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc: raise RuntimeError('Ollama unavailable or model missing. Check Ollama and installed models.') from exc

def embed(texts):
    if not texts:return []
    result=request_api('embed',{'model':current_app.config['EMBED_MODEL'],'input':texts})
    return result['embeddings']

def generate(prompt):
    for model in [current_app.config['OLLAMA_MODEL'],current_app.config['OLLAMA_FALLBACK']]:
        try:
            return request_api('generate',{'model':model,'prompt':prompt,'stream':False,'options':{'num_ctx':2048,'num_predict':300},'keep_alive':'0s'},timeout=120)['response']
        except RuntimeError: continue
    raise RuntimeError('No usable Ollama generation model available')
