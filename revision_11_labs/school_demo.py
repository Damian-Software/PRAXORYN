"""Read-only access-filtering demo; no LLM required."""
import json
from pathlib import Path
from document_acl import filter_documents


def run_demo() -> list[str]:
    docs=json.loads((Path(__file__).parent/'fixtures/school_documents.json').read_text(encoding='utf-8'))
    teacher={'active':True,'tenant_id':'school-A','subject_id':'teacher-001',
             'roles':['teacher'],'educational_interest':True}
    return [doc['document_id'] for doc in filter_documents(teacher,docs)]


if __name__=='__main__':
    print(json.dumps({'allowed_document_ids':run_demo()},indent=2))
