# Ice Gathering 33 — The Patient Sieve

This gathering checks all four lines and joins saved HTTP framing evidence to
exact, paginated CSV review. The report describes what works, what was tried,
limits and suggested 21-piece scope: [REPORT.md](REPORT.md).

See the new shared piece work offline from the repository root:

```sh
python3 -B shared/http-evidence/framing_review.py compare shared/http-evidence/observed-framing-unknown33.csv shared/http-evidence/observed-framing-live33.csv --limit 1
```

Tried: expected exit 1, one changed URL/hop. Missing historical framing evidence
is `unknown`; the separate 2026-10-16 01:22:38 UTC public capture has matching
126,226-byte Content-Length. This does not establish continuous availability.
The shared README documents fields, exits and limits.

Reproduce the local checks:

```sh
python3 -B gathering/run_checks33.py
python3 -B gathering/try_tools33.py
python3 -B gathering/try_new_tools33.py
python3 -B gathering/try_round32_again33.py
python3 -B gathering/try_round33.py
python3 -B gathering/check_delivery33.py
```

The newest line trials are recorded with their exact commands and results in
[new-tool-checks33.json](new-tool-checks33.json). Final totals: 499 line tests,
91 shared tests, eight gathering tests and 123 offline demonstrations. Worker
runtime is Python standard library only; no installation is needed. Tests use
verified scratch copies so fixture creation cannot modify line sources.

The wall is `artifacts/gathering/wall-v13.png`, also `wall.png`: 1254 × 1254
RGB PNG. `dist/gathering/33.jpg` is its 512 × 512 JPEG and `33.json` points to
the full PNG digest. The installed image editing tool added an ochre sieve
with pigment pebbles on bare lower-right rock. See [IMAGE_PROMPT33.md](IMAGE_PROMPT33.md)
for the final prompt. A reviewed, feathered patch preserves the ancestor
pixel-for-pixel outside x=895..1025, y=952..1078; all prior painted marks are
outside that patch. A too-faint first export was replaced. Final PNG and JPEG
were visually reviewed, including both five-digit hands; no unmet visual
requirement was found. [Image checks](image-checks33.json) record the formats,
dimensions and preservation; local review is not external certification.

The self-contained gallery at `dist/index.html` embeds every painting preview
and lists all 165 records. Rebuild offline with
`python3 -B gathering/build_gallery.py` using the already vendored Node JPEG
encoder/decoder. Latest painted previews are refreshed during rebuilds so
reviewing an updated wall cannot leave a stale miniature.

[COINS.md](COINS.md) says none. All line sources and records remain unchanged.
