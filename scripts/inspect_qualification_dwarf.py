#!/usr/bin/env python3
"""Export source-owned concrete function identities using the pinned DWARF reader.

This packages facts, not scores. dSYM use here does not add DecBench metric support.
"""
import argparse,collections,hashlib,json,sys,shlex
from pathlib import Path
from elftools.elf.elffile import ELFFile
import lief
from decbench.utils.binfmt import _build_dwarfinfo, die_attr_owner, die_str_attr
from decbench.utils.native_code import die_ranges
from decbench.metrics.type_match import _parse_function_die

def decode(value):return value.decode('utf-8','replace') if isinstance(value,bytes) else str(value)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('status',type=Path);ap.add_argument('--stage',type=Path,required=True);ap.add_argument('--sources',type=Path,required=True);a=ap.parse_args();s=json.loads(a.status.read_text());binary=a.stage/s['binary'];source=(a.sources/s['project']).resolve();rows=[];f=None
 try:
  if s['platform']=='macos':
   db=binary.with_name(binary.name+'.dSYM')/'Contents/Resources/DWARF'/binary.name;b=lief.parse(str(db));sections={'.'+x.name[2:]:bytes(x.content) for x in b.sections if x.segment_name=='__DWARF'}
   if '.debug_str_offs' in sections:sections['.debug_str_offsets']=sections.pop('.debug_str_offs')
   dw=_build_dwarfinfo(sections,True,8,'AArch64')
  else:
   f=binary.open('rb');elf=ELFFile(f);dw=elf.get_dwarf_info()
  image=lief.parse(str(binary));executable=[]
  for section in image.sections:
   if (s['platform']=='macos' and section.name=='__text') or (s['platform']=='linux' and int(section.flags)&4):executable.append((section.virtual_address,section.virtual_address+len(section.content)))
  assert executable,'No file-backed executable sections'
  producer=set();owned_cus=0;all_concrete=0;rejected_unmapped=0;compile_sources={}
  if s['platform']=='macos':
   for command in json.loads((a.status.parent/'compile_commands.json').read_text()):
    original=Path(command['file']).resolve();args=command.get('arguments') or shlex.split(command['command']);output=args[args.index('-o')+1] if '-o' in args else command.get('output');aliases=[original]
    if output:
     object_file=Path(command['directory'])/output;stem=object_file.with_suffix('');aliases.extend([stem,Path(str(stem)+'.ii')])
    for alias in aliases:
     alias=alias.resolve();prior=compile_sources.get(alias)
     assert prior is None or prior==original,'Conflicting compile-command TU identity';compile_sources[alias]=original
  for cu in dw.iter_CUs():
   top=cu.get_top_DIE();name=decode(top.attributes['DW_AT_name'].value);comp=decode(top.attributes.get('DW_AT_comp_dir').value) if top.attributes.get('DW_AT_comp_dir') else '';producer.add(decode(top.attributes['DW_AT_producer'].value))
   if s['platform']=='macos':
    tu=(Path(comp)/name).resolve() if not Path(name).is_absolute() else Path(name).resolve();tu=compile_sources.get(tu,tu);owned=tu.is_relative_to(source) and 'third_party' not in tu.relative_to(source).parts and 'deps' not in tu.relative_to(source).parts
   else:
    # Existing raw build pipeline clones each project to a temp src root.
    # This is CU ownership only; function declaration paths remain raw evidence.
    tu=Path(name) if Path(name).is_absolute() else Path(comp)/name;owned='/src/' in tu.as_posix() and 'third_party' not in tu.parts and 'deps' not in tu.parts
   if not owned:continue
   owned_cus+=1
   for die in cu.iter_DIEs():
    if die.tag!='DW_TAG_subprogram':continue
    ranges=die_ranges(die,dw)
    if not ranges:continue
    if not all(any(begin>=lo and end<=hi for lo,hi in executable) for begin,end in ranges):rejected_unmapped+=1;continue
    all_concrete+=1
    if s['platform']=='macos':
     attr,owner=die_attr_owner(die,'DW_AT_decl_file',follow_abstract_origin=True)
     if attr is None:continue
     lp=dw.line_program_for_CU(owner.cu);version=lp.header['version'];file_index=int(attr.value)-(0 if version>=5 else 1);files=lp['file_entry']
     if not 0<=file_index<len(files):continue
     entry=files[file_index];decl=Path(decode(entry.name));directory_index=int(entry.dir_index)-(0 if version>=5 else 1)
     if not decl.is_absolute() and 0<=directory_index<len(lp['include_directory']):decl=Path(decode(lp['include_directory'][directory_index]))/decl
     if not decl.is_absolute():decl=Path(comp)/decl
     decl=decl.resolve()
     if not decl.is_relative_to(source) or {'third_party','deps'} & set(decl.relative_to(source).parts):continue
    fname,variables=_parse_function_die(die,dw)
    if not fname:continue
    low=min(begin for begin,end in ranges);link=die_str_attr(die,'DW_AT_linkage_name',follow_abstract_origin=True) or die_str_attr(die,'DW_AT_MIPS_linkage_name',follow_abstract_origin=True)
    rows.append({'binary_sha256':s['binary_sha256'],'address':low,'ranges':ranges,'name':fname,'linkage_name':link if link else None,'source_tu':str(tu),'die_offset':die.offset,'variables':variables})
  assert rows,'No source-owned named concrete function records'
  counts=collections.Counter(x['name'] for x in rows)
  for row in rows:row['storage_key']=row['name'] if counts[row['name']]==1 else row['name']+'@0x'+format(row['address'],'x')
  result={'schema':'decbench-cpp-dwarf-evidence-v2','platform':s['platform'],'project':s['project'],'source_owned_cus':owned_cus,'concrete_records_before_name_resolution':all_concrete,'named_records':len(rows),'unique_entry_addresses':len({x['address'] for x in rows}),'rejected_unmapped_range_records':rejected_unmapped,'producer':sorted(producer),'ownership_method':'exact-native-source-root' if s['platform']=='macos' else 'raw-build-temp-src-layout; header-defined functions may include dependencies','source_level_and_abi_type_policy':'raw DWARF variable spellings/storage retained; no higher-level correctness scoring policy','functions':rows}
  (a.status.parent/'dwarf-functions.json').write_text(json.dumps(result,indent=2));s.pop('dwarf_evidence_error',None);s['source_owned_function_records']=len(rows);s['source_owned_cus']=owned_cus;s['unique_source_entry_addresses']=len({x['address'] for x in rows});s['rejected_unmapped_range_records']=rejected_unmapped;s['debug_producers']=sorted(producer);s['remaining_gates']=[x for x in s['remaining_gates'] if 'function index' not in x and 'function identity extraction' not in x]
 except Exception as e:s['dwarf_evidence_error']=str(e)
 finally:
  if f:f.close()
 a.status.write_text(json.dumps(s,indent=2));print(json.dumps({'status':str(a.status),'named_records':len(rows),'error':s.get('dwarf_evidence_error')}),flush=True)
if __name__=='__main__':main()
