#!/usr/bin/env python3
"""Package exactly pinned tracked source trees and record gitlink dependencies."""
import argparse,json,subprocess
from pathlib import Path

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--plan',type=Path,required=True);a=ap.parse_args();r=a.root.resolve();p=json.loads(a.plan.read_text());seen=set()
 for c in p['cells']:
  name=c['project'];rev=c['source_revision'];repo=c['source_repository']
  if name in seen or not repo or not rev:continue
  seen.add(name);src=r/'sources'/name
  if not src.exists():
   for cmd in [['git','init','-q',str(src)],['git','-C',str(src),'remote','add','origin','https://github.com/'+repo+'.git'],['git','-C',str(src),'fetch','-q','--depth','1','origin',rev],['git','-C',str(src),'checkout','-q','FETCH_HEAD']]:subprocess.run(cmd,check=True)
  actual=subprocess.check_output(['git','-C',str(src),'rev-parse','HEAD'],text=True).strip();assert actual==rev
  out=r/'staged/qualification-v2/sources'/name;out.mkdir(parents=True,exist_ok=True);subprocess.run(['git','-C',str(src),'archive','--format=tar.gz','--output',str(out/'original.tar.gz'),'HEAD'],check=True)
  gitlinks=[]
  for line in subprocess.check_output(['git','-C',str(src),'ls-tree','-r','HEAD'],text=True).splitlines():
   meta,path=line.split('\t',1)
   if meta.startswith('160000 '):gitlinks.append({'path':path,'commit':meta.split()[2]})
  (out/'provenance.json').write_text(json.dumps({'repository':repo,'revision':rev,'tracked_source_tree':True,'gitlinks':gitlinks,'note':'git archive contains tracked main-tree files. Gitlink content requires separate dependency fetching; preprocessed TUs preserve compiled expansions.'},indent=2));print(name,rev,flush=True)
if __name__=='__main__':main()
