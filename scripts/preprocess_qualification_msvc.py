#!/usr/bin/env python3
"""Replay native MSVC compile commands into /P source evidence on Windows."""
import argparse,ctypes,json,subprocess
from ctypes import wintypes
from pathlib import Path

def argv(command):
 fn=ctypes.windll.shell32.CommandLineToArgvW;fn.argtypes=[wintypes.LPCWSTR,ctypes.POINTER(ctypes.c_int)];fn.restype=ctypes.POINTER(wintypes.LPWSTR);n=ctypes.c_int();p=fn(command,ctypes.byref(n));assert p
 try:return [p[i] for i in range(n.value)]
 finally:
  free=ctypes.windll.kernel32.LocalFree;free.argtypes=[ctypes.c_void_p];free.restype=ctypes.c_void_p;free(ctypes.cast(p,ctypes.c_void_p))
def main():
 ap=argparse.ArgumentParser();ap.add_argument('commands',type=Path);ap.add_argument('output',type=Path);a=ap.parse_args();a.output.mkdir(parents=True,exist_ok=True);records=[]
 for i,c in enumerate(json.loads(a.commands.read_text())):
  if not Path(c['file']).suffix.lower() in ['.cpp','.cc','.cxx','.c++']:continue
  raw=c.get('arguments') or argv(c['command']);args=[raw[0]]
  for arg in raw[1:]:
   if arg.lower() in ['/c','-c','/fs','/showincludes'] or arg.lower().startswith(('/fo','/fd','/mp')):continue
   args.append(arg)
  output=(a.output/(str(i).zfill(5)+'.ii')).resolve();args+=['/P','/Fi'+str(output)];subprocess.run(args,cwd=c['directory'],check=True);assert output.exists() and output.stat().st_size>0;records.append({'source':c['file'],'directory':c['directory'],'original_command':c['command'],'preprocess_argv':args,'preprocessed':output.name})
 assert records,'No C++ preprocessing evidence';(a.output/'source-map.json').write_text(json.dumps(records,indent=2))
if __name__=='__main__':main()
