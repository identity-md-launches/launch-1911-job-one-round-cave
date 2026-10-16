#!/usr/bin/env python3
"""Inventory explicit external imports without importing the inspected project."""
import argparse
from collections import deque
import importlib.util
import json
from pathlib import Path
import sys

SCOPE = ('External means not resolved to a module or namespace in this scanned '
         'import root. Names include standard-library and third-party imports; '
         'they are not distribution names or installation requirements. Routes '
         'follow explicit local edges only and do not establish execution. '
         'Conditions, function bodies, dynamic targets, implicit package startup '
         'and installed packages are not simulated. Absence of a route does not '
         'prove an import unused. Review issues, cycles, dynamic calls and skips.')


def load_budget():
    path = Path(__file__).resolve().parents[1] / 'import-budget' / 'budget.py'
    spec = importlib.util.spec_from_file_location('line3_externals_budget', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def inventory(report, starts=None):
    records = {m['module']: m for m in report['modules']}
    selected = sorted(set(report['summary']['entrypoints'] if starts is None else starts))
    for name in selected:
        if name not in records:
            raise ValueError('unknown local module: ' + name)
    graph = {name: set() for name in records}
    for edge in report['edges']:
        graph[edge['from']].add(edge['to'])
    groups = {}
    for name in sorted(records):
        record = records[name]
        for item in record['imports']:
            if item['kind'] != 'external':
                continue
            # Mapper's target retains explicit spelling, including from-import names.
            anchor = item['target'].split(' import ', 1)[0]
            root = anchor.split('.', 1)[0]
            group = groups.setdefault(root, {'name': root, 'sites': [], 'routes': []})
            group['sites'].append({'module': name, 'path': record['path'],
                                   'line': item['line'], 'target': item['target']})
    for group in groups.values():
        group['sites'].sort(key=lambda s: (s['module'], s['line'], s['target']))
    # One BFS per selected entry point, shared across all external names.
    for start in selected:
        parents, pending = {start: None}, deque([start])
        while pending:
            node = pending.popleft()
            for child in sorted(graph[node]):
                if child not in parents:
                    parents[child] = node
                    pending.append(child)
        for group in groups.values():
            owners = {site['module'] for site in group['sites']}
            candidates = []
            for owner in sorted(owners & parents.keys()):
                path, node = [], owner
                while node is not None:
                    path.append(node)
                    node = parents[node]
                candidates.append(list(reversed(path)))
            if candidates:
                path = min(candidates, key=lambda p: (len(p), p))
                group['routes'].append({'start': start, 'import_path': path,
                                        'distance': len(path) - 1,
                                        'sites': [s for s in group['sites'] if s['module'] == path[-1]]})
    dynamic = [{'module': m['module'], 'path': m['path'], 'line': line}
               for m in sorted(records.values(), key=lambda m: m['module'])
               for line in m['dynamic_import_lines']]
    return {'externals': [groups[name] for name in sorted(groups)],
            'selection': {'mode': 'detected_entrypoints' if starts is None else 'explicit_modules',
                          'starts': selected},
            'summary': dict(report['summary'], external_root_count=len(groups),
                            external_site_count=sum(len(g['sites']) for g in groups.values())),
            'issues': report['issues'], 'cycles': report['cycles'],
            'dynamic_imports': dynamic, 'scope': SCOPE}


def format_text(result):
    lines = [f"External names: {result['summary']['external_root_count']}; "
             f"sites: {result['summary']['external_site_count']}",
             'Route starts: ' + (', '.join(result['selection']['starts']) or '(none)')]
    for group in result['externals']:
        lines.append(group['name'])
        for site in group['sites']:
            lines.append(f"  {site['path']}:{site['line']}: {site['target']}")
        for route in group['routes']:
            lines.append('  route: ' + ' -> '.join(route['import_path']))
        if not group['routes']:
            lines.append('  no route from the selected starts in this static graph')
    lines.append(f"Warnings: {len(result['issues'])} issues, {len(result['cycles'])} cycles, "
                 f"{len(result['dynamic_imports'])} dynamic calls")
    lines.append(SCOPE)
    return '\n'.join(lines)


def main(argv=None):
    budget = load_budget()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('--from', dest='starts', action='append', metavar='MODULE',
                        help='replace detected entry points; repeat for multiple starts')
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--strict', action='store_true', help='exit 1 for scan issues, cycles or dynamic calls')
    for name, value in budget.DEFAULTS.items():
        parser.add_argument('--max-' + name.replace('_', '-'), dest=name, type=int, default=value)
    args = parser.parse_args(argv)
    try:
        scan = budget.scan(args.root, {name: getattr(args, name) for name in budget.DEFAULTS})
        result = dict(inventory(scan['map'], args.starts), status='complete',
                      inventory=scan['inventory'], limits=scan['limits'], collection_scope=scan['scope'])
    except (OSError, ValueError, RuntimeError, RecursionError) as exc:
        error = exc.evidence if isinstance(exc, budget.BudgetExceeded) else {
            'type': 'scan_error', 'detail': str(exc)}
        print(json.dumps({'status': 'refused', 'error': error}, indent=2) if args.json
              else 'import-externals: ' + str(exc), file=sys.stdout if args.json else sys.stderr)
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False) if args.json else format_text(result))
    return int(bool(args.strict and (result['issues'] or result['cycles'] or result['dynamic_imports'])))


if __name__ == '__main__':
    sys.exit(main())
