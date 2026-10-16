#!/usr/bin/env python3
"""Bounded review windows over a fresh exact keyed CSV comparison."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys


def load_engine():
    path = Path(__file__).resolve().parents[1] / 'csv-reconcile' / 'reconcile.py'
    spec = importlib.util.spec_from_file_location('csv_slice_engine', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


engine = load_engine()
KINDS = ('added', 'removed', 'changed', 'ambiguous')


def select(result, kinds=KINDS, match_key=None, offset=0, limit=50):
    """Keep global verdicts separate from the selected, possibly empty window."""
    if type(offset) is not int or offset < 0:
        raise ValueError('offset must be a nonnegative integer')
    if type(limit) is not int or not 1 <= limit <= 1000:
        raise ValueError('limit must be an integer from 1 to 1000')
    if not kinds or any(kind not in KINDS for kind in kinds):
        raise ValueError('select at least one known kind')
    if match_key is not None:
        if (not isinstance(match_key, dict) or set(match_key) != set(result['keys'])
                or any(not isinstance(v, str) for v in match_key.values())):
            raise ValueError('match-key must contain exactly all key columns with string values')
    selected = []
    counts = {}
    for kind in KINDS:
        rows = [row for row in result[kind] if kind in kinds and
                (match_key is None or row['key'] == match_key)]
        counts[kind] = len(rows)
        selected.extend({'kind': kind, 'detail': row} for row in rows)
    total = len(selected)
    entries = selected[offset:offset + limit]
    end = min(offset + len(entries), total)
    return {
        'format': 'csv-slice/v1',
        'comparison': {field: result[field] for field in
                       ('format', 'keys', 'ignored_columns', 'equal', 'complete', 'schema', 'summary')},
        'selection': {'kinds': [kind for kind in KINDS if kind in kinds],
                      'match_key': match_key, 'counts': counts, 'total_entries': total},
        'window': {'offset': offset, 'limit': limit, 'returned': len(entries),
                   'omitted_entries': total - len(entries),
                   'next_offset': end if entries and end < total else None},
        'entries': entries,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('before')
    parser.add_argument('after')
    parser.add_argument('--key', action='append', required=True)
    parser.add_argument('--ignore', action='append', default=[])
    parser.add_argument('--kind', action='append', choices=KINDS)
    parser.add_argument('--match-key', help='JSON object with every key column and literal string values')
    parser.add_argument('--offset', type=int, default=0)
    parser.add_argument('--limit', type=int, default=50)
    args = parser.parse_args(argv)
    try:
        match = json.loads(args.match_key) if args.match_key is not None else None
        if args.match_key is not None and match is None:
            raise ValueError('match-key must be an object, not null')
        result = engine.reconcile(args.before, args.after, args.key, args.ignore)
        report = select(result, args.kind or KINDS, match, args.offset, args.limit)
    except (ValueError, OSError) as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=True), file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True))
    # Empty selection never turns a globally different comparison into success.
    return 0 if result['equal'] else 1


if __name__ == '__main__':
    sys.exit(main())
