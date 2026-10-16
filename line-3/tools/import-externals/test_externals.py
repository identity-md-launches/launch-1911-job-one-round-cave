"""Behavior tests; project fixture bytes are parsed, never imported."""
import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('externals', Path(__file__).with_name('externals.py'))
E = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(E)
M = E.load_budget().load_mapper()


def mapped(sources):
    return M.inspect(Path('.'), source_bytes={p: s.encode() for p, s in sources.items()})


def groups(result):
    return {g['name']: g for g in result['externals']}


class ExternalTests(unittest.TestCase):
    def test_grouping_and_exact_sites_keep_alias_duplicates(self):
        report = mapped({'a.py': 'import urllib.request as r, urllib.error\n'
                         'from urllib.parse import urlparse as parse, quote\n'
                         'import json; import json\n'})
        result = E.inventory(report)
        self.assertEqual([g['name'] for g in result['externals']], ['json', 'urllib'])
        self.assertEqual(result['summary']['external_site_count'], 6)
        self.assertEqual([s['target'] for s in groups(result)['urllib']['sites']],
                         ['urllib.error', 'urllib.request', 'urllib.parse import quote',
                          'urllib.parse import urlparse'])
        self.assertEqual([s['line'] for s in groups(result)['json']['sites']], [3, 3])
        self.assertTrue(all(not g['routes'] for g in result['externals']))

    def test_shortest_lexicographic_route_and_direct_site(self):
        report = mapped({'main.py': 'import z, a, longer\nif __name__ == "__main__": pass\n',
                         'a.py': 'import remote\n', 'z.py': 'import remote\n',
                         'longer.py': 'import a\n'})
        group = groups(E.inventory(report))['remote']
        self.assertEqual(group['routes'][0]['import_path'], ['main', 'a'])
        self.assertEqual(group['routes'][0]['sites'], [
            {'module': 'a', 'path': 'a.py', 'line': 1, 'target': 'remote'}])
        direct = groups(E.inventory(report, ['a']))['remote']['routes'][0]
        self.assertEqual(direct['distance'], 0)
        self.assertEqual(direct['import_path'], ['a'])

    def test_local_shadow_namespace_relative_and_unresolved_are_not_external(self):
        report = mapped({'json.py': '', 'main.py': 'import json, ns.child, ns.missing\n'
                         'from ns import child\nfrom . import missing\n', 'ns/child.py': ''})
        result = E.inventory(report)
        self.assertEqual(result['externals'], [])
        self.assertEqual({i['type'] for i in result['issues']},
                         {'unresolved_local', 'unresolved_relative'})

    def test_selection_dedup_unknown_and_unreachable(self):
        report = mapped({'main.py': 'import a\nif __name__ == "__main__": pass\n',
                         'a.py': 'import remote\n', 'other.py': 'import hidden\n'})
        result = E.inventory(report, ['other', 'main', 'other'])
        self.assertEqual(result['selection']['starts'], ['main', 'other'])
        self.assertEqual(groups(result)['remote']['routes'][0]['start'], 'main')
        self.assertEqual(groups(E.inventory(report))['hidden']['routes'], [])
        self.assertEqual(E.inventory(report, [])['selection']['starts'], [])
        with self.assertRaisesRegex(ValueError, 'unknown local module'):
            E.inventory(report, ['absent'])

    def test_conditional_function_and_star_imports_remain_syntactic(self):
        report = mapped({'a.py': 'if False:\n import remote\n'
                         'def f():\n from library.sub import *\n'
                         'if __name__ == "__main__": pass\n'})
        result = E.inventory(report)
        self.assertEqual(set(groups(result)), {'remote', 'library'})
        self.assertEqual(groups(result)['library']['sites'][0]['target'], 'library.sub import *')
        self.assertEqual(groups(result)['remote']['routes'][0]['distance'], 0)

    def test_warnings_preserved_and_no_input_mutation(self):
        report = mapped({'a.py': 'import a\n__import__("hidden")\n',
                         'broken.py': 'this is ! not Python\n',
                         'pkg.py': '', 'pkg/__init__.py': ''})
        before = copy.deepcopy(report)
        result = E.inventory(report)
        self.assertEqual(result['issues'], report['issues'])
        self.assertEqual(result['cycles'], [['a']])
        self.assertEqual(result['dynamic_imports'], [{'module': 'a', 'path': 'a.py', 'line': 2}])
        self.assertEqual(report, before)
        self.assertEqual(result['externals'], [])
        self.assertIn('Warnings: 2 issues, 1 cycles, 1 dynamic calls', E.format_text(result))

    def test_cycle_and_deep_paths_use_iterative_traversal(self):
        sources = {f'n{i:04}.py': f'import n{i+1:04}\n' for i in range(1200)}
        sources['n1200.py'] = 'import n0000\nimport remote\n'
        result = E.inventory(mapped(sources), ['n0000'])
        route = groups(result)['remote']['routes'][0]
        self.assertEqual(route['distance'], 1200)
        self.assertEqual(len(route['import_path']), 1201)

    def test_real_cli_snapshot_refusals_and_execution_trap(self):
        Path('test/scratch').mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir='test/scratch') as directory:
            root = Path(directory)
            source = b'import json\nraise RuntimeError("must not execute")\n'
            (root / 'main.py').write_bytes(source)
            def run(*args):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    code = E.main([str(root), '--json', *args])
                return code, json.loads(output.getvalue())
            code, result = run('--strict')
            self.assertEqual(code, 0)
            self.assertEqual(result['inventory']['bytes'], len(source))
            self.assertEqual(result['summary']['external_root_count'], 1)
            self.assertEqual(result['status'], 'complete')
            code, result = run('--max-file-bytes', '1')
            self.assertEqual(code, 2)
            self.assertEqual(set(result), {'status', 'error'})
            self.assertEqual(result['error']['type'], 'budget_exceeded')
            code, result = run('--from', 'absent')
            self.assertEqual(code, 2)
            self.assertEqual(result['status'], 'refused')
            (root / 'main.py').write_text('import main\n__import__("hidden")\n')
            code, result = run('--strict')
            self.assertEqual(code, 1)
            self.assertEqual(result['status'], 'complete')

    def test_empty_tree_and_permuted_input(self):
        self.assertEqual(E.inventory(mapped({}))['externals'], [])
        report = mapped({'b.py': 'import external\n', 'a.py': 'import b\n'})
        result = E.inventory(report, ['a'])
        report['modules'].reverse()
        report['edges'].reverse()
        self.assertEqual(E.inventory(report, ['a']), result)


if __name__ == '__main__':
    unittest.main()
