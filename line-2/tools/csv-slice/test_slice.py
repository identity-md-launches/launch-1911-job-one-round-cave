"""Behavioral tests. Run from the repository root with unittest discovery."""
import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('csv_slice', Path(__file__).with_name('slice.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SliceTests(unittest.TestCase):
    def setUp(self):
        scratch = Path('test/scratch')
        scratch.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.temp.cleanup)
        self.before = Path(self.temp.name) / 'before.csv'
        self.after = Path(self.temp.name) / 'after.csv'
        self.before.write_text('id,value\na,old\nb,gone\nd,first\nd,second\nz,same\n', encoding='utf-8')
        self.after.write_text('id,value\na,new\nc,added\nd,first\nz,same\n', encoding='utf-8')
        self.result = module.engine.reconcile(self.before, self.after, ['id'])

    def test_pages_reconstruct_every_difference_once(self):
        report = module.select(self.result, limit=1)
        entries = list(report['entries'])
        while report['window']['next_offset'] is not None:
            report = module.select(self.result, limit=1, offset=report['window']['next_offset'])
            entries.extend(report['entries'])
        self.assertEqual(entries, module.select(self.result)['entries'])
        self.assertEqual([e['kind'] for e in entries], list(module.KINDS))

    def test_duplicate_group_remains_whole(self):
        report = module.select(self.result, kinds=['ambiguous'], limit=1)
        group = report['entries'][0]['detail']
        self.assertEqual([r['record'] for r in group['before']], [4, 5])
        self.assertEqual(len(group['after']), 1)
        self.assertFalse(report['comparison']['complete'])

    def test_missing_key_still_globally_different(self):
        report = module.select(self.result, match_key={'id': 'absent'})
        self.assertEqual(report['entries'], [])
        self.assertFalse(report['comparison']['equal'])
        self.assertEqual(report['comparison']['summary']['changed'], 1)

    def test_filters_literal_key(self):
        report = module.select(self.result, match_key={'id': 'a'})
        self.assertEqual([e['kind'] for e in report['entries']], ['changed'])
        self.assertEqual(report['entries'][0]['detail']['fields']['value']['after'], 'new')

    def test_composite_keys_not_concatenated(self):
        self.before.write_text('a,b,v\nx,y|z,1\nx|y,z,1\n', encoding='utf-8')
        self.after.write_text('a,b,v\nx,y|z,2\nx|y,z,3\n', encoding='utf-8')
        result = module.engine.reconcile(self.before, self.after, ['a', 'b'])
        report = module.select(result, match_key={'b': 'y|z', 'a': 'x'})
        self.assertEqual(len(report['entries']), 1)
        self.assertEqual(report['entries'][0]['detail']['fields']['v']['after'], '2')

    def test_schema_survives_empty_window(self):
        self.after.write_text('id,value,extra\na,old,x\n', encoding='utf-8')
        report = module.select(module.engine.reconcile(self.before, self.after, ['id']), offset=999)
        self.assertEqual(report['comparison']['schema']['added_columns'], ['extra'])
        self.assertEqual(report['entries'], [])
        self.assertIsNone(report['window']['next_offset'])

    def test_bounds(self):
        for kwargs in ({'limit': 0}, {'limit': 1001}, {'limit': True}, {'offset': -1}, {'offset': False}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                module.select(self.result, **kwargs)

    def test_invalid_key_and_kind(self):
        for key in ({}, {'id': 1}, {'other': 'a'}, ['a']):
            with self.subTest(key=key), self.assertRaises(ValueError):
                module.select(self.result, match_key=key)
        for kinds in ([], ['unchanged']):
            with self.assertRaises(ValueError):
                module.select(self.result, kinds=kinds)

    def test_selection_does_not_mutate_comparison(self):
        old = copy.deepcopy(self.result)
        module.select(self.result, kinds=['removed', 'removed'], limit=1)
        self.assertEqual(self.result, old)

    def cli(self, *extra):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            status = module.main([str(self.before), str(self.after), '--key', 'id', *extra])
        return status, out.getvalue(), err.getvalue()

    def test_cli_empty_selection_exit_one(self):
        status, out, err = self.cli('--match-key', '{"id":"missing"}')
        self.assertEqual(status, 1)
        self.assertEqual(json.loads(out)['entries'], [])
        self.assertEqual(err, '')

    def test_cli_invalid_json_and_null(self):
        for raw in ('{', 'null', '[]'):
            status, out, err = self.cli('--match-key', raw)
            self.assertEqual(status, 2)
            self.assertEqual(out, '')
            self.assertIn('error', json.loads(err))

    def test_equal_exit_zero(self):
        self.after.write_bytes(self.before.read_bytes())
        # Unique table: duplicates deliberately remain incomplete even on self-comparison.
        self.before.write_text('id,value\na,old\n', encoding='utf-8')
        self.after.write_bytes(self.before.read_bytes())
        status, out, err = self.cli()
        self.assertEqual(status, 0)
        self.assertTrue(json.loads(out)['comparison']['equal'])


if __name__ == '__main__':
    unittest.main()
