#!/usr/bin/env python3
"""Explain framing evidence in a saved Endpoint Sentry GET report, offline."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import stat
import sys

SCHEMA = 'framing-lens/v1'
MAX_REPORT = 1048576


def strict_json(raw):
    def pairs(items):
        result = {}
        for k, v in items:
            if k in result:
                raise ValueError('duplicate JSON key')
            result[k] = v
        return result
    def constant(_):
        raise ValueError('non-JSON number')
    def number(s):
        value = float(s)
        if not math.isfinite(value):
            raise ValueError('non-finite number')
        return value
    return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
                      parse_constant=constant, parse_float=number)


def load_report(name):
    path = Path(name).resolve()
    if not path.is_relative_to(Path.cwd().resolve()):
        raise ValueError('input must stay inside current workspace')
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_REPORT:
        raise ValueError('input must be a regular file of at most 1 MiB')
    with path.open('rb') as stream:
        raw = stream.read(MAX_REPORT + 1)
    if len(raw) > MAX_REPORT:
        raise ValueError('input exceeds 1 MiB')
    return strict_json(raw), hashlib.sha256(raw).hexdigest()


def analyze(source):
    if not isinstance(source, dict):
        raise ValueError('report must be an object')
    wrapped = source.get('schema') == 'deadline-sentry/v1'
    prefix = '/probe' if wrapped else ''
    if wrapped and type(source.get('ok')) is not bool:
        raise ValueError('invalid watchdog health')
    probe = source.get('probe') if wrapped else source
    result = {'schema': SCHEMA, 'outcome': 'unknown', 'hops': [],
              'limits': ['Saved GET evidence is unauthenticated and historical.',
                         'HTTP library parsing is not a raw wire audit; chunk terminators and trailers are not retained.',
                         'Matching length does not prove payload correctness or endpoint health.',
                         'No network, retries, body reads or repairs are performed.']}
    if wrapped and probe is None:
        if source['ok']:
            raise ValueError('successful watchdog lacks worker report')
        result['reason'] = 'watchdog supplied no HTTP evidence'
        return result
    if not isinstance(probe, dict) or probe.get('schema') != 'endpoint-sentry/v1':
        raise ValueError('expected Endpoint Sentry or Deadline Sentry report')
    if type(probe.get('ok')) is not bool or (wrapped and source['ok'] != probe['ok']):
        raise ValueError('invalid or contradictory source health')
    result['source_ok'] = probe['ok']
    error = probe.get('error')
    if error is not None and (not isinstance(error, dict) or not isinstance(error.get('kind'), str)
                              or probe['ok']):
        raise ValueError('invalid source error')
    hops = probe.get('hops')
    if not isinstance(hops, list) or len(hops) > 11 or any(not isinstance(h, dict) for h in hops):
        raise ValueError('invalid hop list')
    final_url = probe.get('final_url')
    if final_url is not None and (not isinstance(final_url, str) or not final_url or len(final_url) > 4096
                                 or not hops or hops[-1].get('url') != final_url):
        raise ValueError('invalid terminal URL')
    if probe['ok'] and not final_url:
        raise ValueError('successful source lacks terminal response')
    for index, hop in enumerate(hops):
        if not isinstance(hop, dict) or type(hop.get('status')) is not int or not 100 <= hop['status'] <= 599:
            raise ValueError('invalid hop')
        size = hop.get('body_bytes')
        if size is not None and (type(size) is not int or not 0 <= size <= 16777217):
            raise ValueError('invalid body byte count')
        if 'body_truncated' in hop and type(hop['body_truncated']) is not bool:
            raise ValueError('invalid truncation flag')
        item = {'evidence': prefix + '/hops/' + str(index), 'status': hop['status'],
                'outcome': 'unknown', 'mode': 'unknown', 'findings': []}
        result['hops'].append(item)
        def finding(code, state, detail):
            item['findings'].append({'code': code, 'state': state, 'detail': detail})
        headers = hop.get('framing_headers')
        if headers is None:
            finding('missing_headers', 'unknown', 'Capture predates framing header evidence; absence cannot be inferred.')
            continue
        if not isinstance(headers, list) or len(headers) > 100:
            raise ValueError('invalid framing header array')
        fields = {'content-length': [], 'transfer-encoding': []}
        for pair in headers:
            if (not isinstance(pair, list) or len(pair) != 2 or not isinstance(pair[0], str)
                    or pair[0] not in fields or not isinstance(pair[1], str) or len(pair[1]) > 65536):
                raise ValueError('invalid framing header field')
            fields[pair[0]].append(pair[1])
        lengths = fields['content-length']
        transfers = fields['transfer-encoding']
        declared = None
        if lengths:
            values = [s.strip(' \t') for value in lengths for s in value.split(',')]
            if any(not re.fullmatch(r'[0-9]{1,1024}', s) for s in values):
                finding('invalid_length', 'issue', 'Content-Length is not a bounded nonnegative ASCII decimal list.')
            elif len({int(s) for s in values}) != 1:
                finding('conflicting_lengths', 'issue', 'Content-Length values disagree.')
            else:
                declared = int(values[0])
                item['declared_bytes'] = declared
                if len(values) > 1:
                    finding('repeated_length', 'info', 'Identical repeated lengths can be normalized by a recipient; producer may reject them.')
        if lengths and transfers:
            finding('competing_framing', 'issue', 'Transfer-Encoding and Content-Length coexist; do not compare length as authoritative framing.')
        no_body = hop['status'] < 200 or hop['status'] in (204, 304)
        # Sentry performs GET only. A 304 length describes a selected representation,
        # whereas 1xx and 204 prohibit both of these framing fields.
        if no_body:
            item['mode'] = 'no-body'
            if hop['status'] != 304 and (lengths or transfers):
                finding('forbidden_framing', 'issue', 'This status prohibits Content-Length and Transfer-Encoding.')
            if size is not None and size != 0:
                finding('unexpected_body', 'issue', 'This status has no message body but capture reports body bytes.')
            if hop['status'] == 304 and lengths:
                finding('representation_length', 'info', '304 Content-Length is representation metadata, not received body size.')
        elif transfers:
            if len(transfers) == 1 and transfers[0].strip(' \t').lower() == 'chunked':
                item['mode'] = 'chunked'
                finding('chunked', 'info', 'Body byte count excludes chunk framing removed by the HTTP library.')
            else:
                item['mode'] = 'unsupported-transfer'
                finding('unsupported_transfer', 'unknown', 'Only a single bare chunked coding is interpreted; other lists or parameters are outside this lens.')
        elif declared is not None:
            item['mode'] = 'content-length'
        elif not lengths:
            item['mode'] = 'connection-close'
            finding('close_delimited', 'unknown', 'No independent declared length: closure alone cannot distinguish intended end from a silent early close.')
        digest = hop.get('body_sha256')
        if digest is not None and (not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest)):
            raise ValueError('invalid body digest')
        terminal = index == len(hops) - 1 and final_url is not None
        # A JSON/status check failure can follow a complete body capture.
        complete = (terminal and size is not None and digest is not None and not hop.get('body_truncated', False)
                    and (error is None or error['kind'] in ('json', 'json_pointer')))
        item['capture_complete'] = complete
        if not complete:
            finding('incomplete_capture', 'unknown', 'No complete terminal body evidence; redirect bodies and partial reads are not length mismatches.')
        elif item['mode'] == 'content-length':
            finding('length_match' if size == declared else 'length_mismatch',
                    'consistent' if size == declared else 'issue',
                    'Captured bytes equal declared length.' if size == declared else 'Complete captured bytes differ from declared length.')
        states = {f['state'] for f in item['findings']}
        item['outcome'] = ('issue' if 'issue' in states else 'unknown' if 'unknown' in states
                           else 'consistent' if complete else 'unknown')
    outcomes = [h['outcome'] for h in result['hops']]
    result['outcome'] = ('issue' if 'issue' in outcomes else 'unknown' if not outcomes or 'unknown' in outcomes
                         else 'consistent')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('report', help='saved JSON report inside current workspace')
    args = parser.parse_args(argv)
    try:
        source, digest = load_report(args.report)
        result = analyze(source)
        result['source_sha256'] = digest
    except (OSError, ValueError, UnicodeError, OverflowError, RecursionError):
        print(json.dumps({'schema': SCHEMA, 'error': 'Invalid report or workspace input path.'}))
        return 2
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0 if result['outcome'] == 'consistent' else 1


if __name__ == '__main__':
    sys.exit(main())
