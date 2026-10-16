#!/usr/bin/env python3
"""Decode one explicitly selected Ethereum event from supplied log bytes offline."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

CODEC = Path(__file__).resolve().parents[1] / 'abi-workbench' / 'abi_workbench.py'
spec = importlib.util.spec_from_file_location('line4_event_codec', CODEC)
abi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(abi)
NOTICE = ('Supplied bytes and ABI only: no receipt, emitter identity, chain inclusion, '
          'finality or token movement is verified. Indexed compound values remain hashes.')
ZTO = '0xd782bdea4ef02a0bd391eb9089470c8080f0a68e'
TRANSFER = {'type': 'event', 'name': 'Transfer', 'anonymous': False, 'inputs': [
    {'name': 'from', 'type': 'address', 'indexed': True},
    {'name': 'to', 'type': 'address', 'indexed': True},
    {'name': 'value', 'type': 'uint256', 'indexed': False}]}


def read_json(path):
    source = Path(path).resolve()
    if not source.is_relative_to(Path.cwd().resolve()):
        raise ValueError('input path must stay inside the current workspace')
    with source.open('rb') as stream:
        raw = stream.read(abi.MAX_ABI_BYTES + 1)
    if len(raw) > abi.MAX_ABI_BYTES:
        raise ValueError('JSON input exceeds the 1 MiB limit')
    try:
        return json.loads(raw.decode('utf-8-sig'), object_pairs_hook=abi.unique_object)
    except RecursionError as exc:
        raise ValueError('JSON nesting is too deep') from exc


def event_schema(entry):
    abi.validate_abi([entry])
    if entry['type'] != 'event':
        raise ValueError('selected entry must be an event')
    if type(entry.get('anonymous', False)) is not bool:
        raise ValueError('anonymous must be a boolean')
    params = entry.get('inputs', [])
    # Reuse the codec's type, depth, parameter and signature limits.
    signature = abi.input_signature(entry)
    if len(signature) > abi.MAX_FUNCTION_REFERENCE:
        raise ValueError('event signature exceeds the 8192-character limit')
    for p in params:
        if type(p.get('indexed')) is not bool:
            raise ValueError('every event input requires a boolean indexed field')
    n = sum(p['indexed'] for p in params)
    anonymous = entry.get('anonymous', False)
    if n > (4 if anonymous else 3):
        raise ValueError('event requires more than four EVM topics')
    return signature, anonymous


def select_event(entries, reference):
    abi.validate_abi(entries)
    if not isinstance(reference, str) or len(reference) > abi.MAX_FUNCTION_REFERENCE:
        raise ValueError('event reference exceeds the 8192-character limit')
    name = reference.split('(', 1)[0]
    candidates = [e for e in entries if e['type'] == 'event' and e['name'] == name]
    if '(' in reference:
        _, reference = abi.function_reference(reference)
        candidates = [e for e in candidates if event_schema(e)[0] == reference]
    if len(candidates) != 1:
        raise ValueError('event selection must match exactly one entry; use a full signature for overloads')
    event_schema(candidates[0])
    return candidates[0]


def parse_log(log):
    if not isinstance(log, dict):
        raise ValueError('log must be an object containing topics and data')
    topics = log.get('topics')
    if not isinstance(topics, list) or len(topics) > 4:
        raise ValueError('topics must be an array of at most four 32-byte hex strings')
    parsed = []
    for topic in topics:
        if not isinstance(topic, str) or len(topic) != 66:
            raise ValueError('each topic must be a 32-byte 0x hex string')
        parsed.append(abi.parse_data(topic))
    if not isinstance(log.get('data'), str):
        raise ValueError('data must be an even-length 0x hex string')
    data = abi.parse_data(log['data'])
    abi.check_budget(len(data) + 32 * len(parsed), 'log')
    return parsed, data


def decode_log(entry, log):
    signature, anonymous = event_schema(entry)
    topics, data = parse_log(log)
    params = entry.get('inputs', [])
    if len(topics) != sum(p['indexed'] for p in params) + (not anonymous):
        raise ValueError('topic count does not match selected event')
    if not anonymous:
        expected = abi.keccak256(signature.encode('ascii'))
        if topics[0] != expected:
            raise ValueError('topic0 does not match selected event signature')
    ordinary = [p for p in params if not p['indexed']]
    decoded = iter(abi.decode_tuple(ordinary, data, strict=True))
    ti = 0 if anonymous else 1
    arguments = []
    for i, p in enumerate(params):
        t = abi.canonical(p)
        arg = {'position': i, 'name': p.get('name') or f'arg{i}',
               'type': t, 'indexed': p['indexed']}
        if not p['indexed']:
            arg.update(encoding='abi', value=next(decoded)['value'])
        else:
            topic = topics[ti]
            ti += 1
            # All arrays and tuples are hashed, even static ones of one word.
            if p['type'] == 'tuple' or '[' in t or t in ('string', 'bytes'):
                arg.update(encoding='indexed_hash', hash='0x' + topic.hex(),
                           recoverable=False)
            else:
                arg.update(encoding='topic_word', value=abi.decode_scalar(t, topic))
        arguments.append(arg)
    return {'status': 'decoded', 'signature': signature, 'anonymous': anonymous,
            'arguments': arguments, 'notice': NOTICE}


def demo():
    # Independently constructed fixture using ZTO/IMD as addresses, not holders.
    imd = 'd34a99bc0f67ae1bbd63c660e6d0b0dd03e263b7'
    log = {'topics': [
        '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef',
        '0x' + '00'*12 + ZTO[2:], '0x' + '00'*12 + imd],
        'data': '0x' + (10**18).to_bytes(32, 'big').hex()}
    result = decode_log(TRANSFER, log)
    result['fixture'] = 'Constructed offline Transfer bytes; not an observed transfer or balance'
    result['token_context'] = ZTO
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--demo', action='store_true')
    parser.add_argument('--abi', help='workspace-contained ABI JSON array')
    parser.add_argument('--event', help='event name or canonical full signature')
    parser.add_argument('--log', help='workspace-contained JSON with topics and data')
    args = parser.parse_args()
    try:
        if args.demo:
            if any((args.abi, args.event, args.log)):
                raise ValueError('--demo cannot be combined with other arguments')
            result = demo()
        else:
            if not all((args.abi, args.event, args.log)):
                raise ValueError('provide --abi, --event and --log, or --demo')
            result = decode_log(select_event(read_json(args.abi), args.event), read_json(args.log))
    except (ValueError, OSError, RecursionError) as exc:
        print(f'error: {exc}', file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
