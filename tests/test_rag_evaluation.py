"""Offline golden checks for grounded answers, citations, and abstention."""
import pytest

from app.services import rag_service


def match(chunk_id, page, text):
    return {
        'id': chunk_id,
        'text': text,
        'distance': 0.2,
        'metadata': {
            'document_id': 'synthetic-manual',
            'title': 'IKA_Synthetic_Industrial_Pump_Manual.pdf',
            'page': page,
        },
    }


CASES = [
    {
        'question': 'What is the nominal flow rate?',
        'passage': match('pump:1:0', 1, 'Nominal flow is 40 cubic metres per hour (40 m3/h).'),
        'generation': 'The nominal flow rate is 40 m3/h. [SOURCE 1]',
        'expected_answer': '40 m3/h',
        'expected_page': 1,
    },
    {
        'question': 'How often is the vibration trend reviewed?',
        'passage': match('pump:2:0', 2, 'Every 30 days, review the fictional bearing vibration trend.'),
        'generation': 'The vibration trend is reviewed every 30 days. [SOURCE 1]',
        'expected_answer': 'every 30 days',
        'expected_page': 2,
    },
    {
        'question': 'What is the pump warranty period?',
        'passage': match('pump:4:0', 4, 'The warranty period is not specified.'),
        'generation': 'Insufficient evidence.',
        'expected_answer': rag_service.INSUFFICIENT,
        'expected_page': None,
    },
]


@pytest.mark.parametrize('case', CASES, ids=['specification', 'maintenance', 'unsupported'])
def test_golden_rag_cases(monkeypatch, case):
    monkeypatch.setattr(rag_service, 'embed', lambda questions: [[0.1, 0.2]])
    monkeypatch.setattr(
        rag_service, 'search',
        lambda vector, document_ids, n, query: [case['passage']],
    )
    monkeypatch.setattr(rag_service, 'generate', lambda prompt: case['generation'])

    result = rag_service.answer(case['question'])

    assert case['expected_answer'].lower() in result['answer'].lower()
    if case['expected_page'] is None:
        assert result['sources'] == []
    else:
        assert result['sources'][0]['page'] == case['expected_page']
        assert result['sources'][0]['source_number'] == 1
        assert '[SOURCE 1]' in result['answer']
