from app.services import rag_service as rag


def match(page, text, distance=0.2):
    return {'id': f'chunk-{page}', 'text': text, 'distance': distance,
            'metadata': {'document_id': 'demo', 'title': 'manual.pdf', 'page': page}}


def test_primary_spec_ranks_above_answer_key():
    answer_key = match(4, 'Questions with expected evidence. Motor rating 7.5 kW', 0.10)
    spec = match(1, 'Motor rating: 7.5 kW', 0.20)
    assert rag.rank_matches([answer_key, spec])[0]['id'] == spec['id']


def test_valid_citation_mapping():
    response, sources = rag.normalize_response('Motor rating 7.5 kW [SOURCE 1].', [match(1, 'Motor rating: 7.5 kW')])
    assert '[SOURCE 1]' in response
    assert sources[0]['page'] == 1


def test_hallucinated_citation_removed():
    response, sources = rag.normalize_response('7.5 kW [SOURCE 99]', [match(1, 'Motor rating: 7.5 kW')])
    assert response == rag.INSUFFICIENT
    assert sources == []


def test_abstention_has_no_sources():
    response, sources = rag.normalize_response('Insufficient evidence. [SOURCE 1]', [match(1, 'Nominal flow 40 m3/h')])
    assert response == rag.INSUFFICIENT
    assert sources == []


def test_answer_with_mocked_retrieval(monkeypatch):
    monkeypatch.setattr(rag, 'embed', lambda questions: [[0.1, 0.2]])
    monkeypatch.setattr(rag, 'search', lambda vector, ids, n: [match(1, 'Motor rating: 7.5 kW')])
    monkeypatch.setattr(rag, 'generate', lambda prompt: 'The motor rating is 7.5 kW [SOURCE 1].')
    result = rag.answer('What is the motor rating?')
    assert result['sources'][0]['page'] == 1
    assert result['retrieval_diagnostics'][0]['chunk_id'] == 'chunk-1'
