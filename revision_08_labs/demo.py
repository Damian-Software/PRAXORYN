"""Print a synthetic, non-networked walkthrough."""
from policy_broker import Principal, Resource, Broker, DecisionLog
from rag_acl import Document, search
from workflow_lease import Job


def run() -> None:
    person = Principal('user-001', 'tenant-a', frozenset({'reader', 'mail-drafter'}),
                       frozenset({'engineering'}))
    own = Resource('policies', 'tenant-a', 'internal', frozenset({'engineering'}))
    other = Resource('policies', 'tenant-b', 'internal', frozenset({'engineering'}))
    docs = [Document('doc-a', 'policies', own, 1, True, 'Retention policy', 'Approved retention rules.'),
            Document('doc-b', 'policies', other, 1, True, 'Secret roadmap', 'Hidden budget value.')]
    log = DecisionLog()
    broker = Broker(log)
    permission, _ = broker.authorize(person, 'knowledge.search',
        {'query': 'retention', 'collection_id': 'policies', 'max_results': 3}, resource=own)
    rejected, _ = broker.authorize(person, 'shell.exec', {'command': 'whoami'})
    draft, _ = broker.authorize(person, 'mail.draft',
        {'recipient': 'reviewer@example.test', 'subject': 'Review', 'body': 'Draft only.'})
    job = Job()
    lease = job.acquire(now=100)
    success = job.complete(lease, 'artifact:demo-001', now=110)
    print({'search_allowed': permission, 'unknown_tool_allowed': rejected,
           'draft_allowed': draft, 'results': len(search(person, 'policies', 'retention', docs)),
           'workflow_completed': success, 'audit_events': len(log.events)})


if __name__ == '__main__':
    run()
