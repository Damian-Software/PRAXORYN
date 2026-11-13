"""Policy gate for static analysis and test reports, not an executor of repository code."""
from __future__ import annotations
import json
from pathlib import Path

REQUIRED = ('unit', 'lint', 'security')


def evaluate(report: dict) -> dict:
    results = report.get('checks')
    if not isinstance(results, dict):
        return {'decision': 'BLOCK', 'reasons': ['missing_checks']}
    reasons = []
    for item in REQUIRED:
        value = results.get(item)
        if not isinstance(value, dict) or value.get('status') != 'pass':
            reasons.append(f'{item}_not_passed')
    # An AI suggestion is not a passing test or a security clearance.
    if report.get('ai_assessment') == 'approve' and reasons:
        reasons.append('ai_cannot_override_required_checks')
    return {'decision': 'PASS' if not reasons else 'BLOCK', 'reasons': reasons}


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('report', type=Path)
    args = parser.parse_args()
    result = evaluate(json.loads(args.report.read_text(encoding='utf-8')))
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['decision'] == 'PASS' else 1)


if __name__ == '__main__':
    main()
