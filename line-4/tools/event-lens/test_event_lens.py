import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import event_lens as t


def word(n):
    return '0x' + n.to_bytes(32, 'big', signed=n < 0).hex()


def event(*params, anonymous=False):
    return {'type': 'event', 'name': 'E', 'anonymous': anonymous, 'inputs': list(params)}


def param(typ, indexed=False, **kw):
    return dict(type=typ, indexed=indexed, **kw)


def log_for(e, topics=(), data='0x'):
    prefix = [] if e.get('anonymous') else ['0x'+t.abi.keccak256(t.event_schema(e)[0].encode()).hex()]
    return {'topics': prefix + list(topics), 'data': data}


class EventLensTests(unittest.TestCase):
    def test_known_transfer_topic_and_zto_fixture(self):
        out = t.demo()
        self.assertEqual(out['signature'], 'Transfer(address,address,uint256)')
        self.assertEqual([a['value'] for a in out['arguments']], [t.ZTO,
            '0xd34a99bc0f67ae1bbd63c660e6d0b0dd03e263b7', 10**18])
        self.assertIn('not an observed', out['fixture'])

    def test_indexed_scalars_and_original_positions(self):
        e = event(param('int8', True), param('bool'), param('bytes2', True))
        out = t.decode_log(e, log_for(e, [word(-3), '0x1234'+'00'*30], word(1)))
        self.assertEqual([a['value'] for a in out['arguments']], [-3, True, '0x1234'])
        self.assertEqual([a['name'] for a in out['arguments']], ['arg0','arg1','arg2'])
        self.assertEqual([a['position'] for a in out['arguments']], [0,1,2])

    def test_hashes_for_all_compound_indexed_types(self):
        # Static arrays and one-word static tuples are hashed too.
        for p in [param('string', True), param('bytes', True),
                  param('uint256[1]', True), param('uint256[]', True),
                  param('tuple', True, components=[{'type':'uint256'}])]:
            e = event(p)
            a = t.decode_log(e, log_for(e, [word(7)]))['arguments'][0]
            self.assertEqual(a['encoding'], 'indexed_hash')
            self.assertEqual(a['hash'], word(7))
            self.assertFalse(a['recoverable'])
            self.assertNotIn('value', a)

    def test_dynamic_unindexed_string_independent_layout(self):
        e = event(param('string'))
        data = word(32) + word(2)[2:] + b'hi'.hex() + '00'*30
        self.assertEqual(t.decode_log(e, log_for(e, data=data))['arguments'][0]['value'], 'hi')

    def test_nested_tuple_and_fixed_array_unindexed(self):
        e = event(param('tuple', components=[{'type':'uint8'}, {'type':'bool'}]), param('int8[2]'))
        data = word(9) + word(1)[2:] + word(-1)[2:] + word(2)[2:]
        self.assertEqual([a['value'] for a in t.decode_log(e, log_for(e, data=data))['arguments']], [[9, True], [-1,2]])

    def test_anonymous_four_topics_and_empty_event(self):
        e = event(*(param('uint', True) for _ in range(4)), anonymous=True)
        self.assertEqual([a['value'] for a in t.decode_log(e, log_for(e, [word(i) for i in range(4)]))['arguments']], list(range(4)))
        for anonymous in [True, False]:
            e = event(anonymous=anonymous)
            self.assertEqual(t.decode_log(e, log_for(e))['arguments'], [])

    def test_wrong_topic0_and_topic_counts(self):
        e = event(param('uint', True))
        for log in [{'topics':[word(2),word(1)],'data':'0x'},
                    log_for(e), log_for(e, [word(1),word(2)])]:
            with self.assertRaises(ValueError):
                t.decode_log(e, log)

    def test_noncanonical_topic_words(self):
        for typ, value in [('bool', word(2)), ('address', word(2**160)),
                           ('uint8',word(256)), ('int8',word(255)),
                           ('bytes1','0x01'+'00'*30+'01')]:
            e = event(param(typ, True))
            with self.subTest(typ=typ), self.assertRaises(ValueError):
                t.decode_log(e, log_for(e, [value]))

    def test_strict_data_refuses_suffix_and_bad_offsets(self):
        e = event(param('string'))
        good = word(32) + word(1)[2:] + '78' + '00'*31
        bad = [good + word(0)[2:], good[:-2]+'01', good[:-2],
               word(64)+word(0)[2:]+good[66:]]
        for data in bad:
            with self.subTest(data=data), self.assertRaises(ValueError):
                t.decode_log(e, log_for(e, data=data))

    def test_selection_overloads_aliases_duplicates(self):
        a, b = event(param('uint')), event(param('address'))
        self.assertEqual(t.select_event([a,b], 'E(uint256)'), a)
        self.assertEqual(t.select_event([a,b], 'E(uint)'), a)
        for entries, ref in [([a,b],'E'), ([a,a],'E(uint256)'), ([a],'Missing'),
                             ([a],'E(uint256)junk'), ([a],'E( uint)')]:
            with self.assertRaises(ValueError):
                t.select_event(entries, ref)

    def test_invalid_schemas_and_unsupported_types(self):
        for e in [event({'type':'uint'}), event(param('uint', indexed=1)),
                  event(param('bytes[]')), event(*(param('uint',True) for _ in range(4))),
                  dict(event(), anonymous='false'), {'type':'function','name':'E'}]:
            with self.subTest(entry=e), self.assertRaises(ValueError):
                t.event_schema(e)
        p = param('uint')
        for _ in range(33):
            p = param('tuple', components=[p])
        with self.assertRaisesRegex(ValueError, '32 levels'):
            t.event_schema(event(p))

    def test_bad_log_shapes_no_tracebacks(self):
        for log in [None, [], {}, {'topics':None,'data':'0x'},
                    {'topics':[word(1)]*5,'data':'0x'},
                    {'topics':[None],'data':'0x'}, {'topics':['0x12'],'data':'0x'},
                    {'topics':['0x'+'gg'*32],'data':'0x'},
                    {'topics':[],'data':None}, {'topics':[],'data':3},
                    {'topics':[],'data':'0x1'}, {'topics':[],'data':'0x  '},
                    {'topics':[],'data':'0x'+'00'*(t.abi.MAX_DATA_BYTES+1)}]:
            with self.subTest(log=str(log)[:60]), self.assertRaises(ValueError):
                t.parse_log(log)

    def test_reader_and_cli(self):
        with tempfile.TemporaryDirectory(dir='test/scratch') as tmp:
            path = Path(tmp)
            e = event(param('uint'))
            (path/'abi.json').write_text(json.dumps([e]))
            (path/'log.json').write_text(json.dumps(log_for(e, data=word(8))))
            args = ['event-lens','--abi',str(path/'abi.json'),'--event','E(uint)','--log',str(path/'log.json')]
            out, err = io.StringIO(), io.StringIO()
            with patch('sys.argv',args), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                self.assertEqual(t.main(), 0)
            self.assertEqual(json.loads(out.getvalue())['arguments'][0]['value'], 8)
            for raw in ['{"topics":[],"data":null}', '{"topics":[],"topics":[],"data":"0x"}', '{}', 'x']:
                (path/'log.json').write_text(raw)
                with patch('sys.argv',args), contextlib.redirect_stderr(io.StringIO()) as err:
                    self.assertEqual(t.main(),2)
                self.assertNotIn('Traceback',err.getvalue())
            (path/'log.json').write_bytes(b' '*(t.abi.MAX_ABI_BYTES+1))
            with self.assertRaisesRegex(ValueError,'1 MiB'):
                t.read_json(path/'log.json')
        with self.assertRaisesRegex(ValueError,'inside the current workspace'):
            t.read_json(Path.cwd().parent/'never-opened.json')


if __name__ == '__main__':
    unittest.main()
