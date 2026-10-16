"""Cross-line checks: incomplete framing, review windows and exact CSV semantics."""
import contextlib
import csv
import io
import json
from pathlib import Path
import tempfile
import unittest

import framing_review as tool

LIVE = 'line-1/tools/framing-lens/observed-live.json'


class FramingHandoffTests(unittest.TestCase):
    def setUp(self):
        Path('test/scratch').mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir='test/scratch')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def save(self, name, text):
        path = self.root / name
        path.write_text(text)
        return path

    def source(self, change=None):
        source = json.loads(Path(LIVE).read_text())
        probe = source.get('probe', source)
        if change:
            change(probe)
        return self.save('source.json', json.dumps(source))

    def baseline(self):
        text, judgment = tool.snapshot(LIVE)
        self.assertEqual(judgment['outcome'], 'consistent')
        return self.save('baseline.csv', text)

    def test_real_retained_capture_has_exact_length_and_digest(self):
        text, judgment = tool.snapshot(LIVE)
        row = next(csv.DictReader(io.StringIO(text)))
        self.assertEqual(row['declared_bytes'], row['body_bytes'])
        self.assertEqual(row['outcome'], 'consistent')
        self.assertEqual(row['capture_complete'], 'true')
        self.assertEqual(len(row['report_sha256']), 64)
        self.assertEqual(judgment['source_ok'], True)
        path = self.save('equal.csv', text)
        self.assertTrue(tool.compare(path, path)['comparison']['equal'])

    def test_missing_header_capture_stays_unknown_not_absent(self):
        source = self.source(lambda p: p['hops'][-1].pop('framing_headers'))
        text, judgment = tool.snapshot(source)
        self.assertEqual(judgment['outcome'], 'unknown')
        row = next(csv.DictReader(io.StringIO(text)))
        self.assertEqual(row['declared_bytes'], '')
        self.assertEqual(row['capture_complete'], '')
        self.assertIn('missing_headers', row['findings'])

    def test_empty_page_does_not_hide_change(self):
        baseline = self.baseline()
        source = self.source(lambda p: p['hops'][-1].pop('framing_headers'))
        after = self.save('after.csv', tool.snapshot(source)[0])
        report = tool.compare(baseline, after, offset=999, limit=1)
        self.assertEqual(report['entries'], [])
        self.assertFalse(report['comparison']['equal'])
        self.assertEqual(report['comparison']['summary']['changed'], 1)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = tool.main(['compare', str(baseline), str(after), '--offset', '999'])
        self.assertEqual(code, 1)

    def test_filter_does_not_hide_ambiguity_and_group_stays_whole(self):
        baseline = self.baseline()
        rows = list(csv.DictReader(io.StringIO(baseline.read_text())))
        out = io.StringIO(newline='')
        writer = csv.DictWriter(out, fieldnames=tool.COLUMNS, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows * 3)
        after = self.save('duplicate.csv', out.getvalue())
        hidden = tool.compare(baseline, after, kinds=['changed'])
        self.assertEqual(hidden['entries'], [])
        self.assertFalse(hidden['comparison']['complete'])
        visible = tool.compare(baseline, after, limit=1)
        self.assertEqual(len(visible['entries'][0]['detail']['after']), 3)
        self.assertEqual(visible['window']['returned'], 1)

    def test_redirect_unknown_hop_is_retained_with_terminal(self):
        def prepend(p):
            p['hops'].insert(0, {'url': p['url'], 'status': 302,
                                'framing_headers': [['content-length', '0']]})
        text, judgment = tool.snapshot(self.source(prepend))
        rows = list(csv.DictReader(io.StringIO(text)))
        self.assertEqual([r['hop'] for r in rows], ['0', '1'])
        self.assertEqual([r['outcome'] for r in rows], ['unknown', 'consistent'])
        self.assertEqual([r['overall_outcome'] for r in rows], ['unknown', 'unknown'])
        self.assertEqual(rows[0]['body_bytes'], '')

    def test_pages_reassemble_all_hops_without_changing_summary(self):
        baseline = self.baseline()
        source = self.source(lambda p: p['hops'].insert(0,
            {'url': p['url'], 'status': 302, 'framing_headers': []}))
        after = self.save('after.csv', tool.snapshot(source)[0])
        whole = tool.compare(baseline, after)
        first = tool.compare(baseline, after, limit=1)
        second = tool.compare(baseline, after, offset=first['window']['next_offset'], limit=1)
        self.assertEqual(first['entries'] + second['entries'], whole['entries'])
        self.assertEqual(first['comparison'], second['comparison'])

    def test_invalid_inputs_refuse_without_success_output(self):
        baseline = self.baseline()
        invalid = self.save('bad.csv', 'url,hop\nhttps://example.org/,0\n')
        for args in [ ['compare', str(baseline), str(invalid)],
                      ['compare', str(baseline), str(baseline), '--match-key', 'null'],
                      ['compare', str(baseline), str(baseline), '--limit', '0'],
                      ['snapshot', str(self.save('bad.json', '{"x":1,"x":2}'))]]:
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                self.assertEqual(tool.main(args), 2)
            self.assertEqual(out.getvalue(), '')
            self.assertIn('error', json.loads(err.getvalue()))

    def test_watchdog_without_http_evidence_does_not_invent_identity(self):
        path = self.save('watchdog.json', '{"schema":"deadline-sentry/v1","ok":false}')
        with self.assertRaises(ValueError):
            tool.snapshot(path)


if __name__ == '__main__':
    unittest.main()
