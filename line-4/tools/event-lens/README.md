# Event Lens

Decode one Ethereum event log offline with an explicitly selected ABI event.
Python 3 standard library only; uses the sibling ABI Workbench's Keccak and
strict codec. Keep `line-4/tools/abi-workbench/abi_workbench.py` alongside it.
No network, wallet, signing or transaction submission is involved.

From the repository root, see it work:

```sh
python3 -B line-4/tools/event-lens/event_lens.py --demo
```

The constructed fixture decodes the standard `Transfer(address,address,uint256)`
topic, two address words and an integer value of 1000000000000000000. It uses the
real ZTO address as token context and ZTO/IMD as address values. These are explicitly
invented log bytes for demonstrating the codec, **not an observed transfer, token
amount, balance, holder or claim about these contracts' event ABIs**. No decimals
are inferred. The emitter is not verified.

Use your own saved ABI and log (both must be inside the current workspace):

```sh
python3 -B line-4/tools/event-lens/event_lens.py --abi line-4/tools/event-lens/transfer-abi.json --event 'Transfer(address,address,uint256)' --log line-4/tools/event-lens/transfer-log.json
```

The included files reproduce the same constructed fixture. A log input is one
JSON object with `topics` (up to four exact 32-byte `0x` strings) and `data`
(even-length `0x` hex). Extra RPC fields are ignored; in particular `address`,
`removed`, block and transaction fields are not authenticated or interpreted.
Each file is bounded to 1 MiB; duplicate JSON fields are rejected. CLI exit 0
means decoding succeeded; exit 2 means an input/schema/selection error.

Select by event name if unique, or full signature for overloads. Type aliases
such as `uint` are canonicalized. Duplicate matching entries are refused.
Non-anonymous logs require the full 32-byte event signature hash in topic0;
anonymous events omit it and may have four indexed arguments. The ABI's
`anonymous` defaults to false and every input must explicitly specify boolean
`indexed`. Selection cannot establish that an anonymous event was emitted.

Each output argument retains its original position, type, name and indexed flag.
Scalar indexed words are decoded with high-bit, sign-extension and padding checks.
Indexed strings, bytes, arrays and tuples are reported as **unrecoverable hashes**,
including fixed arrays and static tuples. The tool never guesses their preimages.
Non-indexed data uses exact canonical re-encoding to reject surplus data, gaps,
misordered/shared tails, malformed padding and offsets.

Supported types follow ABI Workbench: scalar integers, address, bool, bytes1..32,
string/bytes, one-dimensional scalar arrays, and nested tuples. Tuple arrays,
nested arrays, arrays of dynamic elements, fixed point and function types are
refused. Even hashed indexed types must be in this supported schema subset.
A matching signature does not establish chain inclusion, finality or origin;
unrelated contracts can emit identical topics and supplied bytes can be fabricated.

Tried locally: 13 regression tests passed, and both commands above returned the
expected three values. Tests cover independent word layouts, the known Transfer
topic, anonymous and empty events, hash-only compound arguments, overloads,
malformed JSON, workspace confinement, strict data and invalid topic words.

```sh
python3 -B -m unittest discover -s line-4/tools/event-lens -v
```

Encoding rules were checked against the official
[Solidity ABI event specification](https://docs.soliditylang.org/en/latest/abi-spec.html#events).
No observed on-chain event is claimed by these checks.
