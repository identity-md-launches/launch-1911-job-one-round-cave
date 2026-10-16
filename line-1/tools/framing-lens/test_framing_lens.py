import copy
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import framing_lens as lens


def report(headers=None, size=2, status=200):
    hop = {'url': 'https://example.org/', 'status': status, 'body_bytes': size,
           'body_sha256': 'a' * 64}
    if headers is not None:
        hop['framing_headers'] = headers
    return {'schema': 'endpoint-sentry/v1', 'ok': True,
            'final_url': hop['url'], 'hops': [hop], 'checks': []}


def codes(result):
    return {f['code'] for f in result['hops'][0]['findings']}


class FramingTests(unittest.TestCase):
    def test_match_and_mismatch(self):
        r = report([['content-length', '2']])
        self.assertEqual(lens.analyze(r)['outcome'], 'consistent')
        r['hops'][0]['body_bytes'] = 1
        self.assertIn('length_mismatch', codes(lens.analyze(r)))
        self.assertEqual(lens.analyze(r)['outcome'], 'issue')

    def test_old_capture_does_not_infer_absence(self):
        self.assertIn('missing_headers', codes(lens.analyze(report())))
        self.assertEqual(lens.analyze(report())['outcome'], 'unknown')
        self.assertIn('close_delimited', codes(lens.analyze(report([]))))

    def test_repeated_and_conflicting_lengths(self):
        for headers in [[['content-length', '2'], ['content-length', '02']],
                        [['content-length', '2, 2']]]:
            r = lens.analyze(report(headers))
            self.assertEqual(r['outcome'], 'consistent')
            self.assertIn('repeated_length', codes(r))
        r = lens.analyze(report([['content-length', '2, 3']]))
        self.assertIn('conflicting_lengths', codes(r))
        self.assertEqual(r['outcome'], 'issue')

    def test_malformed_decimal(self):
        for value in ['-1', '+2', '', '2,', '٢', '2.0', '1e2', '9' * 1025]:
            with self.subTest(value=value[:20]):
                r = lens.analyze(report([['content-length', value]]))
                self.assertIn('invalid_length', codes(r))

    def test_transfer_coding_is_not_a_length(self):
        r = lens.analyze(report([['transfer-encoding', 'CHUNKED']]))
        self.assertEqual(r['outcome'], 'consistent')
        self.assertNotIn('length_match', codes(r))
        for value in ['gzip, chunked', 'chunked;foo=bar', '', 'chunked, chunked']:
            self.assertEqual(lens.analyze(report([['transfer-encoding', value]]))['outcome'], 'unknown')
        r = lens.analyze(report([['transfer-encoding', 'chunked'], ['content-length', '2']]))
        self.assertIn('competing_framing', codes(r))
        self.assertEqual(r['outcome'], 'issue')

    def test_partial_and_redirect_bytes_not_mismatches(self):
        r = report([['content-length', '20']], 2)
        for change in ['body_truncated', 'missing_final', 'timeout', 'missing_digest']:
            source = copy.deepcopy(r)
            source['ok'] = False
            if change == 'body_truncated':
                source['hops'][0]['body_truncated'] = True
            elif change == 'missing_final':
                del source['final_url']
            elif change == 'timeout':
                source['error'] = {'kind': 'timeout'}
            else:
                del source['hops'][0]['body_sha256']
            result = lens.analyze(source)
            self.assertEqual(result['outcome'], 'unknown')
            self.assertNotIn('length_mismatch', codes(result))

    def test_semantic_failure_does_not_invalidate_complete_bytes(self):
        r = report([['content-length', '2']])
        r.update(ok=False, error={'kind': 'json'})
        result = lens.analyze(r)
        self.assertEqual(result['outcome'], 'consistent')
        self.assertFalse(result['source_ok'])

    def test_304_representation_length_and_204_prohibition(self):
        r = lens.analyze(report([['content-length', '20000']], 0, 304))
        self.assertEqual(r['outcome'], 'consistent')
        self.assertIn('representation_length', codes(r))
        self.assertNotIn('length_mismatch', codes(r))
        r = lens.analyze(report([['content-length', '0']], 0, 204))
        self.assertIn('forbidden_framing', codes(r))
        r = lens.analyze(report([], 1, 204))
        self.assertIn('unexpected_body', codes(r))
        self.assertEqual(lens.analyze(report([], 0, 204))['outcome'], 'consistent')

    def test_watchdog_and_multiple_hops(self):
        r = report([['content-length', '2']])
        self.assertEqual(lens.analyze({'schema': 'deadline-sentry/v1', 'ok': True, 'probe': r})['outcome'], 'consistent')
        r['hops'].insert(0, {'status': 302, 'framing_headers': [['content-length', '50']]})
        result = lens.analyze(r)
        self.assertEqual(result['outcome'], 'unknown')
        self.assertEqual(result['hops'][1]['outcome'], 'consistent')
        self.assertEqual(lens.analyze({'schema': 'deadline-sentry/v1', 'ok': False})['outcome'], 'unknown')

    def test_invalid_shapes(self):
        for headers in ['2', [['set-cookie', 'private']], [[2, '2']], [['content-length', 2]]]:
            with self.assertRaises(ValueError):
                lens.analyze(report(headers))
        for size in [-1, True, 16777218]:
            with self.assertRaises(ValueError):
                lens.analyze(report([], size))
        r = report([]); r['ok'] = False
        with self.assertRaises(ValueError):
            lens.analyze({'schema': 'deadline-sentry/v1', 'ok': True, 'probe': r})

    def test_malformed_terminal_hop_is_rejected(self):
        r = report([])
        r['hops'] = [None]
        with self.assertRaises(ValueError):
            lens.analyze(r)
        r = report([])
        r['final_url'] = ''
        with self.assertRaises(ValueError):
            lens.analyze(r)

    def test_loader_and_cli(self):
        for raw in [b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1e999}']:
            with self.assertRaises(ValueError):
                lens.strict_json(raw)
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as folder:
            path = Path(folder) / 'report.json'
            path.write_text(json.dumps(report([['content-length', '2']])))
            with contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(lens.main([str(path)]), 0)
            self.assertEqual(len(json.loads(out.getvalue())['source_sha256']), 64)
            path.write_bytes(b'x' * (lens.MAX_REPORT + 1))
            with self.assertRaises(ValueError):
                lens.load_report(path)
        # Rejected before opening: no outside-workspace file is read.
        with self.assertRaises(ValueError):
            lens.load_report(Path.cwd().parent / 'outside-report.json')


if __name__ == '__main__':
    unittest.main()
