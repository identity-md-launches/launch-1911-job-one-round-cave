#!/usr/bin/env python3
"""Project saved HTTP framing evidence into CSV and page exact differences."""
import argparse
import csv
import io
import json
import sys

import framing_lens
import payload_contract
import reconcile
import review_slice

COLUMNS = ('url', 'hop', 'overall_outcome', 'source_ok', 'status', 'outcome',
           'mode', 'capture_complete', 'declared_bytes', 'body_bytes',
           'findings', 'report_sha256')
NOTICE = ('Saved, unauthenticated GET evidence only. A framing match does not '
          'establish payload validity or current endpoint health. Windows limit '
          'entries, not bytes; ambiguous groups stay whole. Use immutable inputs '
          'and identical options while paging. No network or writes are performed.')


def snapshot(path):
    source, digest = framing_lens.load_report(path)
    judgment = framing_lens.analyze(source)
    url, probe = payload_contract.source_url(source)
    if not judgment['hops']:
        raise ValueError('no attributable HTTP hops; no CSV snapshot was produced')
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=COLUMNS, lineterminator='\n')
    writer.writeheader()
    for index, item in enumerate(judgment['hops']):
        raw = probe['hops'][index]
        writer.writerow({'url': url, 'hop': str(index),
                         'overall_outcome': judgment['outcome'],
                         'source_ok': str(judgment['source_ok']).lower(),
                         'status': str(item['status']), 'outcome': item['outcome'],
                         'mode': item['mode'],
                         'capture_complete': (str(item['capture_complete']).lower()
                                              if 'capture_complete' in item else ''),
                         'declared_bytes': item.get('declared_bytes', ''),
                         'body_bytes': raw.get('body_bytes', ''),
                         'findings': json.dumps(item['findings'], sort_keys=True,
                                                separators=(',', ':')),
                         'report_sha256': digest})
    return stream.getvalue(), judgment


def compare(before, after, kinds=review_slice.KINDS, match_key=None, offset=0, limit=50):
    for path in (before, after):
        header, groups, count = reconcile.load_table(path, ['url', 'hop'])
        if header != list(COLUMNS) or count == 0:
            raise ValueError('need nonempty framing CSV snapshots with the exact header')
        for key in groups:
            # Validate identifiers without pretending to authenticate supplied values.
            payload_contract.source_url({'url': key[0]})
            if key[1] not in {str(i) for i in range(11)}:
                raise ValueError('hop must be a canonical index from 0 through 10')
    result = reconcile.reconcile(before, after, ['url', 'hop'])
    return dict(review_slice.select(result, kinds, match_key, offset, limit),
                handoff='http-framing-review/v1', scope=NOTICE)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    commands = parser.add_subparsers(dest='command', required=True)
    snap = commands.add_parser('snapshot')
    snap.add_argument('report')
    diff = commands.add_parser('compare')
    diff.add_argument('before')
    diff.add_argument('after')
    diff.add_argument('--kind', choices=review_slice.KINDS, action='append')
    diff.add_argument('--match-key', help='exact JSON object with string url and hop')
    diff.add_argument('--offset', type=int, default=0)
    diff.add_argument('--limit', type=int, default=50)
    args = parser.parse_args(argv)
    try:
        if args.command == 'snapshot':
            output, judgment = snapshot(args.report)
            code = 0 if judgment['outcome'] == 'consistent' else 1
        else:
            match = json.loads(args.match_key) if args.match_key is not None else None
            if args.match_key is not None and match is None:
                raise ValueError('match-key must be an object')
            result = compare(args.before, args.after, args.kind or review_slice.KINDS,
                             match, args.offset, args.limit)
            output = json.dumps(result, indent=2, ensure_ascii=True) + '\n'
            code = 0 if result['comparison']['equal'] else 1
    except (OSError, ValueError, TypeError, KeyError, IndexError, OverflowError, RecursionError) as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=True), file=sys.stderr)
        return 2
    sys.stdout.write(output)
    return code


if __name__ == '__main__':
    raise SystemExit(main())
