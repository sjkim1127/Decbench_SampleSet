"""Collect actual MSVC invocation evidence for newly built Detours/WinSparkle.

This never associates rebuilt source evidence with an older binary identity.
"""
import argparse
import ctypes
from ctypes import wintypes
import hashlib
import json
import ntpath
from pathlib import Path, PureWindowsPath
import subprocess


def windows_argv(command):
    split = ctypes.windll.shell32.CommandLineToArgvW
    split.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_int)]
    split.restype = ctypes.POINTER(wintypes.LPWSTR)
    count = ctypes.c_int()
    pointer = split(command, ctypes.byref(count))
    if not pointer:
        raise ValueError('Cannot decode Windows compiler command')
    try:
        return [pointer[i] for i in range(count.value)]
    finally:
        free = ctypes.windll.kernel32.LocalFree
        free.argtypes = [ctypes.c_void_p]
        free.restype = ctypes.c_void_p
        free(ctypes.cast(pointer, ctypes.c_void_p))


def is_source(argument):
    return not argument.startswith(('/', '-')) and PureWindowsPath(argument).suffix.lower() in {'.cpp', '.cc', '.cxx', '.c++'}


def single_source_argv(arguments, source):
    """Separate a compiler batch without reordering its effective options."""
    return [argument for argument in arguments if not is_source(argument)
            and not (not argument.startswith(('/', '-'))
                     and PureWindowsPath(argument).suffix.lower() == '.c')] + [source]


def within(source, root):
    try:
        return ntpath.commonpath([ntpath.normcase(source), ntpath.normcase(root)]) == ntpath.normcase(root)
    except ValueError:
        return False


def tlog_records(text):
    lines = text.splitlines()
    records = []
    for index, line in enumerate(lines):
        if line.startswith('^'):
            if index + 1 >= len(lines):
                raise ValueError('Missing CL command in tracking log')
            sources = [source for source in line[1:].split('|') if is_source(source)]
            if sources:
                command = lines[index + 1].strip()
                if not command or command.startswith('^'):
                    raise ValueError('Missing CL command in tracking log')
                records.append((sources, command))
    return records


def project_directory(text):
    """Require the project identity emitted beside this compiler tracking log."""
    fields = text.strip().split('|')
    if len(fields) != 2:
        raise ValueError('Missing or malformed MSBuild project directory evidence')
    project, directory = fields
    if (not ntpath.isabs(project) or not ntpath.isabs(directory)
            or ntpath.normcase(ntpath.normpath(ntpath.dirname(project)))
            != ntpath.normcase(ntpath.normpath(directory))):
        raise ValueError('Inconsistent MSBuild project directory evidence')
    return project, directory


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--project', choices=['detours', 'winsparkle'], required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--compiler', required=True)
    args = parser.parse_args()
    source_root, evidence = args.source.resolve(), args.evidence.resolve()
    records = []
    if args.project == 'winsparkle':
        logs = sorted(source_root.rglob('CL.command.1.tlog'))
        if not logs:
            raise ValueError('Actual MSBuild CL tracking log is missing')
        (evidence/'tracking').mkdir(exist_ok=True)
        for index, path in enumerate(logs):
            raw = path.read_bytes()
            (evidence/'tracking'/f'{index:04d}.tlog').write_bytes(raw)
            marker = path.parent/'decbench-project.txt'
            marker_raw = marker.read_bytes()
            project, directory = project_directory(marker_raw.decode('utf-8-sig'))
            if not within(project, str(source_root)) or not Path(project).is_file():
                raise ValueError('Compiler tracking project is outside the source checkout')
            (evidence/'tracking'/f'{index:04d}-project.txt').write_bytes(marker_raw)
            for sources, command in tlog_records(raw.decode('utf-16')):
                argv = windows_argv(command)
                if argv and ntpath.basename(argv[0]).lower() in {'cl', 'cl.exe'}:
                    argv = argv[1:]
                for source in sources:
                    if within(source, str(source_root)):
                        records.append({'directory': directory, 'file': source,
                            'arguments': [args.compiler] + single_source_argv(argv, source),
                            'evidence': {'kind': 'msbuild-cl-tlog', 'path': str(path),
                                         'sha256': hashlib.sha256(raw).hexdigest(), 'batch_command': command,
                                         'project': project,
                                         'project_marker_sha256': hashlib.sha256(marker_raw).hexdigest()}})
    else:
        text = (evidence/'build.log').read_text(encoding='utf-8-sig', errors='strict')
        for line in text.splitlines():
            command = line.strip()
            if command.lower().startswith('cl '):
                argv = windows_argv(command)[1:]
                directory = source_root/'src'
            elif command.lower().startswith(args.compiler.lower()+' '):
                argv = windows_argv(command[len(args.compiler):].strip())
                directory = source_root
            else:
                continue
            for source in [value for value in argv if is_source(value)]:
                full = ntpath.normpath(ntpath.join(str(directory), source))
                if within(full, str(source_root)):
                    records.append({'directory': str(directory), 'file': full,
                        'arguments': [args.compiler] + single_source_argv(argv, full),
                        'evidence': {'kind': 'executed-build-log-command', 'batch_command': command}})
    if not records:
        raise ValueError('No actual project C++ compiler invocations collected')
    selected = {}
    for row in records:
        if not Path(row['file']).is_file():
            raise ValueError('Recorded source is not available: '+row['file'])
        row['source_sha256'] = hashlib.sha256(Path(row['file']).read_bytes()).hexdigest()
        row['command'] = subprocess.list2cmdline(row['arguments'])
        signature = (ntpath.normcase(row['file']), tuple(row['arguments']))
        selected[signature] = row
    records = list(selected.values())
    (evidence/'compile_commands.json').write_text(json.dumps(records, indent=2))
    replay = [{**row, 'arguments': row['arguments'] + ['/Y-']} for row in records]
    replay_path = evidence/'preprocess_commands.json'
    replay_path.write_text(json.dumps(replay, indent=2))
    subprocess.run(['python', 'scripts/preprocess_qualification_msvc.py', str(replay_path),
                    str(evidence/'preprocessed')], check=True)
    mappings = json.loads((evidence/'preprocessed/source-map.json').read_text())
    if len(mappings) != len(records):
        raise ValueError('Preprocessed TU coverage differs from actual invocation set')
    with (evidence/'recollection.json').open('w') as out:
        json.dump({'schema': 'cpp-native-recollection-v1', 'project': args.project,
                   'compile_invocations': len(records), 'preprocessed_tus': len(mappings),
                   'pch_policy': 'textual replay with /Y-; original PCH arguments retained separately',
                   'original_binary_identity_reuse': False, 'qualified': False, 'scoring_ready': False,
                   'remaining': ['original/new identity comparison', 'native/source ownership qualification',
                                 'preprocessing-to-original compilation equivalence']}, out, indent=2)
    print(json.dumps({'project': args.project, 'preprocessed_tus': len(mappings)}))


if __name__ == '__main__':
    main()
