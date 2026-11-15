"""Export heuristic code observations to SARIF 2.1.0 for review tooling."""
from __future__ import annotations
import argparse
import json
from pathlib import Path


def export_sarif(report:dict, source_name:str)->dict:
    findings=[]
    for issue in report.get('issues',[]):
        findings.append({'ruleId':issue['rule'],'level':'error' if issue.get('severity')=='error' else 'warning',
                         'message':{'text':issue['message']},
                         'locations':[{'physicalLocation':{
                            'artifactLocation':{'uri':source_name},
                            'region':{'startLine':max(1,int(issue.get('line',1)))}}}]})
    rules=[{'id':v} for v in sorted({x['ruleId'] for x in findings})]
    return {'version':'2.1.0','$schema':'https://json.schemastore.org/sarif-2.1.0.json',
            'runs':[{'tool':{'driver':{'name':'PraxorynForgeHeuristics','rules':rules}},'results':findings}]}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source_report',type=Path)
    p.add_argument('--source',required=True);p.add_argument('--out',type=Path,required=True)
    args=p.parse_args();result=json.loads(args.source_report.read_text())
    args.out.write_text(json.dumps(export_sarif(result,args.source),indent=2)+'\n')
