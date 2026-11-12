"""Persistent SQLite FTS5 index used to complement vector retrieval."""
import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from flask import current_app


_TERM = re.compile(r'[\w-]+', re.UNICODE)


@contextmanager
def _connection():
    connection = _connect()
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def _connect():
    path = Path(current_app.config['DATA_DIR']) / 'keyword.sqlite3'
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=30)
    connection.execute('PRAGMA busy_timeout = 30000')
    connection.execute(
        'CREATE VIRTUAL TABLE IF NOT EXISTS chunks USING fts5('
        'chunk_id UNINDEXED, document_id UNINDEXED, title UNINDEXED, '
        'page UNINDEXED, content)'
    )
    return connection


def replace_document(document_id, items, title):
    rows = [
        (item['id'], document_id, title, str(item['page']), item['text'])
        for item in items
    ]
    with _connection() as connection:
        connection.execute('DELETE FROM chunks WHERE document_id = ?', (document_id,))
        connection.executemany(
            'INSERT INTO chunks(chunk_id, document_id, title, page, content) '
            'VALUES (?, ?, ?, ?, ?)',
            rows,
        )


def remove_document(document_id):
    with _connection() as connection:
        connection.execute('DELETE FROM chunks WHERE document_id = ?', (document_id,))


def rebuild_from_collection(col):
    result = col.get(include=['documents', 'metadatas'])
    rows = []
    for chunk_id, text, metadata in zip(
        result['ids'], result['documents'], result['metadatas']
    ):
        if not metadata or not metadata.get('document_id') or text is None:
            continue
        rows.append((
            chunk_id,
            metadata['document_id'],
            metadata.get('title', ''),
            str(metadata.get('page', '')),
            text,
        ))
    with _connection() as connection:
        connection.execute('DELETE FROM chunks')
        connection.executemany(
            'INSERT INTO chunks(chunk_id, document_id, title, page, content) '
            'VALUES (?, ?, ?, ?, ?)',
            rows,
        )


def search(query, document_ids=None, limit=20):
    terms = list(dict.fromkeys(_TERM.findall(query or '')))
    if not terms:
        return []
    match_query = ' OR '.join(f'"{term}"' for term in terms)
    conditions = ['chunks MATCH ?']
    parameters = [match_query]
    if document_ids is not None:
        normalized_ids = list(dict.fromkeys(document_ids))
        if not normalized_ids:
            return []
        conditions.append('document_id IN (' + ','.join('?' for _ in normalized_ids) + ')')
        parameters.extend(normalized_ids)
    parameters.append(max(1, int(limit)))
    sql = (
        'SELECT chunk_id, document_id, title, page, content, bm25(chunks) '
        'FROM chunks WHERE ' + ' AND '.join(conditions) +
        ' ORDER BY bm25(chunks) LIMIT ?'
    )
    with _connection() as connection:
        rows = connection.execute(sql, parameters).fetchall()
    return [{
        'id': row[0],
        'text': row[4],
        'metadata': {
            'document_id': row[1],
            'title': row[2],
            'page': int(row[3]) if str(row[3]).isdigit() else row[3],
        },
        'distance': None,
        'lexical_score': row[5],
        'retrieval_method': 'keyword',
    } for row in rows]


def indexed_count():
    with _connection() as connection:
        return connection.execute('SELECT count(*) FROM chunks').fetchone()[0]
