#!/usr/bin/env python3
"""Reproduce the Gathering 33 framing/CSV handoff using saved public evidence."""
import json
from pathlib import Path
import subprocess
import sys


def main():
    script = 'shared/http-evidence/framing_review.py'
    results = []

    def run(label, args, expected, output=None):
        command = [sys.executable, '-B', script, *map(str, args)]
        p = subprocess.run(command, capture_output=True, text=True, timeout=15)
        results.append({'name': label, 'command': command, 'exit_code': p.returncode,
                        'expected_exit_code': expected, 'passed': p.returncode == expected,
                        'stdout_bytes': len(p.stdout.encode()), 'stderr': p.stderr})
        if p.returncode != expected:
            raise RuntimeError(label + ': unexpected exit')
        if output:
            Path(output).write_text(p.stdout)
        return p.stdout

    before = 'shared/http-evidence/observed-framing33.csv'
    after = 'shared/http-evidence/observed-framing-live33.csv'
    unknown = 'shared/http-evidence/observed-framing-unknown33.csv'
    run('Historical real framing snapshot',
        ['snapshot', 'line-1/tools/framing-lens/observed-live.json'], 0, before)
    run('Separate fresh public capture framing snapshot',
        ['snapshot', 'gathering/live-framing33-source.json'], 0, after)
    run('Older capture lacks framing evidence',
        ['snapshot', 'line-1/tools/endpoint-doctor/observed-live.json'], 1, unknown)
    run('Equal framing evidence', ['compare', before, before, '--limit', '1'], 0)
    page = json.loads(run('Historical-to-fresh exact evidence change',
        ['compare', before, after, '--limit', '1'], 1,
        'shared/http-evidence/observed-framing-review33.json'))
    assert page['comparison']['summary']['changed'] == 1
    assert set(page['entries'][0]['detail']['fields']) == {'report_sha256'}
    missing = json.loads(run('Unknown older framing stays visible',
        ['compare', unknown, after, '--limit', '1'], 1,
        'shared/http-evidence/observed-framing-unknown-review33.json'))
    assert missing['comparison']['summary']['changed'] == 1
    empty = json.loads(run('Empty window retains full difference verdict',
        ['compare', unknown, after, '--offset', '999'], 1))
    assert not empty['comparison']['equal'] and not empty['entries']
    report = {'round': 33, 'ok': all(r['passed'] for r in results), 'results': results}
    Path('gathering/shared-tool-checks33.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'ok': report['ok'], 'checks': len(results)}))


if __name__ == '__main__':
    main()
