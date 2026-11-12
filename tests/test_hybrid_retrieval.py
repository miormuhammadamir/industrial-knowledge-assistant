import pytest

from app.services import keyword_service, vector_service


def test_keyword_search_retrieves_exact_equipment_terms(app):
    with app.app_context():
        keyword_service.replace_document(
            'pump-doc',
            [
                {
                    'id': 'pump:1:0',
                    'page': 1,
                    'text': 'Asterion PX-40 motor rating is 7.5 kW.',
                },
                {
                    'id': 'other:2:0',
                    'page': 2,
                    'text': 'General maintenance interval is 30 days.',
                },
            ],
            'pump-manual.pdf',
        )

        results = keyword_service.search('PX-40 motor rating', limit=5)

    assert results[0]['id'] == 'pump:1:0'
    assert results[0]['metadata']['page'] == 1


def test_hybrid_search_merges_keyword_candidates_with_vector_results(app, monkeypatch):
    records = [
        {
            'id': 'semantic:1',
            'text': 'General details about pump maintenance.',
            'metadata': {'document_id': 'doc-1', 'title': 'manual.pdf', 'page': 1},
            'distance': 0.1,
        },
        {
            'id': 'keyword:2',
            'text': 'Asterion PX-40 motor rating is 7.5 kW.',
            'metadata': {'document_id': 'doc-1', 'title': 'manual.pdf', 'page': 2},
            'distance': 0.4,
        },
    ]

    class FakeCollection:
        def count(self):
            return len(records)

        def get(self, include):
            return {
                'ids': [record['id'] for record in records],
                'documents': [record['text'] for record in records],
                'metadatas': [record['metadata'] for record in records],
            }

        def query(self, **params):
            record = records[0]
            return {
                'ids': [[record['id']]],
                'documents': [[record['text']]],
                'metadatas': [[record['metadata']]],
                'distances': [[record['distance']]],
            }

    monkeypatch.setattr(vector_service, 'collection', FakeCollection)
    with app.app_context():
        results = vector_service.search(
            [0.1, 0.2], n=2, query='Asterion PX-40 motor rating'
        )

    by_id = {result['id']: result for result in results}
    assert set(by_id) == {'semantic:1', 'keyword:2'}
    assert by_id['keyword:2']['retrieval_methods'] == ['keyword']
    assert by_id['semantic:1']['retrieval_methods'][0] == 'semantic'


def test_explicit_empty_document_filter_returns_no_results(app, monkeypatch):
    class UnexpectedCollection:
        def count(self):
            raise AssertionError('Empty filter should short-circuit before querying')

    monkeypatch.setattr(vector_service, 'collection', UnexpectedCollection)
    with app.app_context():
        assert vector_service.search([0.1], doc_ids=[], query='motor') == []


def test_store_validates_vectors_before_replacing_existing_chunks(app, monkeypatch):
    class UnexpectedCollection:
        def get(self, **kwargs):
            raise AssertionError('Invalid vectors must fail before reading or writing Chroma')

    monkeypatch.setattr(vector_service, 'collection', UnexpectedCollection)
    document = type('Document', (), {'id': 'doc-1', 'original_filename': 'manual.pdf'})()

    with app.app_context():
        with pytest.raises(ValueError, match='Embedding count'):
            vector_service.store(
                document,
                [{'id': 'doc-1:1:0', 'page': 1, 'index': 0, 'text': 'Motor rating.'}],
                [],
            )


def test_store_writes_new_chunks_before_deleting_obsolete_ids(app, monkeypatch):
    events = []

    class FakeCollection:
        def get(self, **kwargs):
            return {'ids': ['doc-1:1:0', 'doc-1:2:0']}

        def upsert(self, **kwargs):
            events.append('upsert')

        def delete(self, **kwargs):
            events.append(('delete', kwargs['ids']))

    monkeypatch.setattr(vector_service, 'collection', FakeCollection)
    monkeypatch.setattr(
        vector_service.keyword_service, 'replace_document',
        lambda document_id, items, title: events.append('keyword-index'),
    )
    document = type('Document', (), {'id': 'doc-1', 'original_filename': 'manual.pdf'})()
    items = [{'id': 'doc-1:1:0', 'page': 1, 'index': 0, 'text': 'Motor rating.'}]

    with app.app_context():
        vector_service.store(document, items, [[0.1, 0.2]])

    assert events == ['upsert', ('delete', ['doc-1:2:0']), 'keyword-index']
