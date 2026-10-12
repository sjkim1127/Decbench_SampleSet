#!/usr/bin/env python3
"""Seal only present artifacts; candidates, verified payloads and scores are separate."""
import argparse,collections,hashlib,json,shutil
from pathlib import Path

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for data in iter(lambda:f.read(1048576),b''):h.update(data)
 return h.hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--plan',type=Path,required=True);a=ap.parse_args();r=a.root.resolve();base=r/'staged/qualification-v2';plan=json.loads(a.plan.read_text());records=[]
 for platform in ['linux','windows','macos']:
  for status in sorted((base/platform).rglob('status.json')):
   s=json.loads(status.read_text());binary=base/s['binary'];stripped=base/s['stripped'];assert binary.is_file() and stripped.is_file();assert sha(binary)==s['binary_sha256'] and sha(stripped)==s['stripped_sha256'];assert s['code_sections_equal'];assert not s.get('dwarf_evidence_error')
   assert s.get('source_owned_function_records') or s.get('project_owned_function_count'),'No project function evidence: '+str(status)
   cell=next(c for c in plan['cells'] if c['platform']==s['platform'] and c['project']==s['project']);assert cell['source_revision']==s.get('source_revision',cell['source_revision'])
   source=base/'sources'/s['project']/'original.tar.gz';assert source.is_file(),'Missing pinned original sources: '+str(source)
   arch='x86_64' if platform=='windows' else 'arm64';dest=base/'inputs'/platform/arch/s['optimization']/s['project']/binary.name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(stripped,dest);assert sha(dest)==s['stripped_sha256'];s['input']=str(dest.relative_to(base));s['original_source_sha256']=sha(source);s['packaging_checks_passed']=True;s['qualified']=False;s['scoring_ready']=False;status.write_text(json.dumps(s,indent=2));records.append(s)
 coverage=collections.Counter(x['platform'] for x in records);present={(x['platform'],x['project'],x['optimization']) for x in records};missing=[{'cell':c['id'],'mode':mode} for c in plan['cells'] for mode in c['optimization_modes'] if (c['platform'],c['project'],mode) not in present]
 manifest={'schema':'decbench-cpp-qualification-package-v2','status':'staging-preview-not-complete-qualification','target_project_platform_cells':15,'target_linked_images':45,'present_project_platform_cells':len({(x['platform'],x['project']) for x in records}),'present_linked_images':len(records),'present_platform_images':dict(coverage),'qualified_images':0,'scoring_ready_images':0,'raw_corpus':plan['raw_corpus'],'legacy_qualification_parent':plan['qualification_parent'],'records':records,'missing':missing,'files':[]}
 for p in sorted(base.rglob('*')):
  if p.is_file() and p.name not in ['manifest.json','manifest.sha256']:manifest['files'].append({'path':str(p.relative_to(base)),'sha256':sha(p),'size':p.stat().st_size})
 p=base/'manifest.json';p.write_text(json.dumps(manifest,indent=2));(base/'manifest.sha256').write_text(sha(p)+'  manifest.json\n');print(json.dumps({k:v for k,v in manifest.items() if k not in ['records','files']},indent=2))
if __name__=='__main__':main()
