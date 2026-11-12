import re

import tiktoken


_ENCODING = tiktoken.get_encoding('cl100k_base')
_HEADING = re.compile(r'^(?:\d+(?:\.\d+)*\.?\s+\S.*|[A-Z][A-Z0-9 /&()_-]{2,100})$')
_TITLE_JOINERS = {'and', 'or', 'of', 'the', 'for', 'to', 'in', 'on', 'by'}


def _is_heading(line):
    if _HEADING.fullmatch(line):
        return True
    words = line.split()
    return (
        1 < len(words) <= 8
        and not re.search(r'[.!?;:]$', line)
        and all(
            word[0].isupper() or word.casefold() in _TITLE_JOINERS
            for word in words if word[0].isalpha()
        )
    )


def _sections(text):
    heading = ''
    lines = []
    for raw_line in text.splitlines():
        line = ' '.join(raw_line.split())
        if not line:
            continue
        if _is_heading(line):
            if lines:
                yield heading, '\n'.join(lines)
            heading = line
            lines = []
        else:
            lines.append(line)
    if lines:
        yield heading, '\n'.join(lines)
    elif heading:
        yield heading, ''


def chunks(pages, size=500, overlap=75):
    if size <= 0 or not 0 <= overlap < size:
        raise ValueError('Invalid chunk settings')
    for page, text in pages:
        index = 0
        for heading, body in _sections(text):
            heading_tokens = _ENCODING.encode(heading)
            body_tokens = _ENCODING.encode(body)
            prefix = heading_tokens if heading_tokens else []
            body_size = max(1, size - len(prefix))
            body_step = max(1, body_size - min(overlap, body_size - 1))
            if not body_tokens:
                if prefix:
                    yield page, index, _ENCODING.decode(prefix)
                    index += 1
                continue
            for start in range(0, len(body_tokens), body_step):
                part = prefix + body_tokens[start:start + body_size]
                if part:
                    yield page, index, _ENCODING.decode(part)
                    index += 1
                if start + body_size >= len(body_tokens):
                    break
