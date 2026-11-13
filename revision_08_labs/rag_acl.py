"""Toy lexical retrieval: enforce tenant/ACL BEFORE scoring or returning data."""
from __future__ import annotations
from dataclasses import dataclass
import re
from policy_broker import Principal, Resource, can_read


@dataclass(frozen=True)
class Document:
    document_id: str
    collection_id: str
    resource: Resource
    revision: int
    active: bool
    title: str
    body: str


def terms(text: str) -> set[str]:
    return set(re.findall(r'\w+', text.casefold(), flags=re.UNICODE))


def search(principal: Principal, collection_id: str, query: str,
           documents: list[Document], limit: int = 5) -> list[dict[str, object]]:
    if not isinstance(query, str) or len(query) > 300 or not query.strip():
        raise ValueError('Invalid query')
    if type(limit) is not int or not 1 <= limit <= 10:
        raise ValueError('Invalid limit')
    q = terms(query)
    results: list[tuple[int, Document]] = []
    for doc in documents:
        if not doc.active or doc.collection_id != collection_id:
            continue
        if not can_read(principal, doc.resource):
            continue
        score = len(q & terms(doc.title + ' ' + doc.body))
        if score:
            results.append((score, doc))
    results.sort(key=lambda item: (-item[0], item[1].document_id))
    return [{'document_id': doc.document_id, 'title': doc.title,
             'revision': doc.revision, 'excerpt': doc.body[:160]}
            for _, doc in results[:limit]]
