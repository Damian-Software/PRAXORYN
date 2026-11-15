"""Pre-retrieval ACL example: deny by default, not a full IAM service."""
import json
from pathlib import Path


def allowed(docs, groups):
    if not all(isinstance(x,str) for x in groups):raise ValueError('invalid groups')
    authorized=[]
    for doc in docs:
        declared=doc.get('allowed_groups',[])
        if any(group in declared for group in groups):
            authorized.append({'doc_id':doc['doc_id'],'revision':doc['revision']})
    return authorized


def main():
    docs=json.loads(Path('examples/school_docs.json').read_text())
    print('student:',allowed(docs,['students']))
    print('teacher:',allowed(docs,['teachers']))

if __name__=='__main__':main()
