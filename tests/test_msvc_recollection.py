import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / 'scripts/collect_msvc_recollection.py'
spec = importlib.util.spec_from_file_location('recollection', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class CommandEvidenceTests(unittest.TestCase):
    def test_batch_sources_are_separated_without_reordering_options(self):
        argv = ['cl.exe', '/c', '/DVALUE=1', 'one.cpp', '/O2', 'two.cpp', '/Ipath']
        self.assertEqual(module.single_source_argv(argv, r'D:\src\one.cpp'),
                         ['cl.exe', '/c', '/DVALUE=1', '/O2', '/Ipath', r'D:\src\one.cpp'])

    def test_forced_language_and_output_flags_are_not_mistaken_for_sources(self):
        self.assertFalse(module.is_source('/TP'))
        self.assertFalse(module.is_source('/Fooutput.cpp.obj'))
        self.assertTrue(module.is_source(r'D:\source\FILE.CPP'))

    def test_tlog_keys_preserve_all_source_members_and_effective_command(self):
        rows = module.tlog_records('^D:\\src\\A.CPP|D:\\src\\B.CPP\n/c /O2 /DVALUE=1\n')
        self.assertEqual(rows, [([r'D:\src\A.CPP', r'D:\src\B.CPP'], '/c /O2 /DVALUE=1')])

    def test_malformed_tlog_record_is_not_silently_skipped(self):
        with self.assertRaises(ValueError):
            module.tlog_records('^D:\\src\\A.CPP\n^D:\\src\\B.CPP\n')
        with self.assertRaises(ValueError):
            module.tlog_records('^D:\\src\\A.CPP\n')

    def test_c_batch_members_are_not_replayed_as_additional_cpp_inputs(self):
        self.assertEqual(module.single_source_argv(['cl.exe', '/c', 'a.cpp', 'b.c'], 'a.cpp'),
                         ['cl.exe', '/c', 'a.cpp'])

    def test_source_root_matching_has_a_path_boundary(self):
        self.assertTrue(module.within(r'd:\source\src\a.cpp', r'D:\SOURCE'))
        self.assertFalse(module.within(r'D:\source-other\a.cpp', r'D:\source'))
        self.assertFalse(module.within(r'E:\source\a.cpp', r'D:\source'))

    def test_each_tracking_log_uses_its_proven_project_directory(self):
        root = module.project_directory(r'D:\src\main.vcxproj|D:\src')
        sub = module.project_directory(r'D:\src\3rdparty\wx.vcxproj|D:\src\3rdparty')
        self.assertEqual(root[1], r'D:\src')
        self.assertEqual(sub[1], r'D:\src\3rdparty')
        self.assertNotEqual(root[1], sub[1])

    def test_missing_or_inconsistent_project_directory_is_rejected(self):
        for text in ['', r'D:\src\main.vcxproj', r'main.vcxproj|D:\src',
                     r'D:\src\3rdparty\wx.vcxproj|D:\src',
                     r'D:\src\main.vcxproj|D:\src|other']:
            with self.subTest(text=text), self.assertRaises(ValueError):
                module.project_directory(text)


if __name__ == '__main__':
    unittest.main()
