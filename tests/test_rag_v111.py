"""Regression tests for IKA v1.1.1. Run with: python -m pytest -v"""
from app.services.rag_service import INSUFFICIENT, normalize_response, rank_matches


def sample(page=1):
    return {
        'id': f'doc:{page}:0', 'distance': 0.3 + page / 100,
        'text': 'Motor rating: 7.5 kW',
        'metadata': {'document_id': 'doc', 'title': 'manual.pdf', 'page': page},
    }


def test_correct_answer_and_source():
    answer, sources = normalize_response('Motor rating: 7.5 kW [SOURCE 1]', [sample()])
    assert answer == 'Motor rating: 7.5 kW [SOURCE 1]'
    assert [s['page'] for s in sources] == [1]


def test_abstention_has_no_sources():
    assert normalize_response('Insufficient evidence. [SOURCE 1]', [sample()]) == (INSUFFICIENT, [])


def test_placeholder_not_shown():
    answer, sources = normalize_response('Motor rating: 7.5 kW [SOURCE 1]\nSOURCE N.', [sample()])
    assert 'SOURCE N' not in answer
    assert len(sources) == 1


def test_invalid_source_number_rejected():
    assert normalize_response('Motor rating: 7.5 kW [SOURCE 9]', [sample()]) == (INSUFFICIENT, [])


def test_uncited_answer_rejected():
    assert normalize_response('Motor rating: 7.5 kW', [sample()]) == (INSUFFICIENT, [])


def test_answer_key_penalized():
    primary = sample(1)
    answer_key = sample(4)
    answer_key['distance'] = 0.2
    answer_key['text'] = 'Questions with expected evidence: motor rating 7.5 kW'
    assert rank_matches([answer_key, primary])[0]['id'] == primary['id']


def test_does_not_abstain_on_normal_sentence_containing_not_specified():
    answer, sources = normalize_response(
        'Warranty is not specified, but the motor rating is 7.5 kW [SOURCE 1]', [sample()]
    )
    assert answer.startswith('Warranty is not specified')
    assert len(sources) == 1
