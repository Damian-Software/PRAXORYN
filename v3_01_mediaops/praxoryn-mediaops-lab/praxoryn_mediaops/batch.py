"""Conservative sequential batch execution for synthetic or approved briefs."""
from pathlib import Path
from .pipeline import publish


def run_batch(source_dir: Path, output_dir: Path, max_jobs: int = 10) -> dict:
    if not (1 <= max_jobs <= 50):
        raise ValueError('max_jobs out of range')
    briefs=sorted(source_dir.glob('*.json'))
    if len(briefs) > max_jobs:
        raise ValueError('batch exceeds allowed size')
    succeeded=[]
    failed=[]
    for brief in briefs:
        try:
            path=publish(brief,output_dir,live=False)
        except (ValueError,FileExistsError,RuntimeError) as exc:
            failed.append({'brief':brief.name,'error':type(exc).__name__})
        else:
            succeeded.append(path.name)
    return {'successful':succeeded,'failed':failed}
