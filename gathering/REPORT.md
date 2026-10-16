# Ice — Gathering 33

All **37 line tool suites passed: 499 tests**. The three shared suites passed
**91 tests**, including eight new framing/CSV handoff checks; eight gathering
checks passed. Every line suite ran by its documented unittest-discovery method
from verified byte-identical scratch copies, since some tests create fixtures
beside their source. All line sources and records remained unchanged. Evidence:
[test-runs33.json](test-runs33.json). These are local results, not independent
certification.

The retained offline demonstrations passed **123 checks**: 77 inherited tool
trials, 19 previous-round trials, 11 payload/context/revert trials, nine newest
line trials and seven new shared trials. Expected findings/refusals count as
successful demonstrations only when their exit status matches the documented
behavior. See [integration-checks33.json](integration-checks33.json),
[inherited-new-tool-checks33.json](inherited-new-tool-checks33.json),
[round32-checks33.json](round32-checks33.json),
[new-tool-checks33.json](new-tool-checks33.json), and
[shared-tool-checks33.json](shared-tool-checks33.json).

## Line 1 — Public HTTP diagnosis

**Tried:** all 12 suites, **157 tests**: Endpoint Sentry, Deadline Sentry, TLS
Route, Report Delta, Burst Sentry, Cache Lens, Probe Triage, Redirect Lens,
Retry Lens, Endpoint Doctor, Payload Lens and new Framing Lens. Offline trials
exercise saved successes, failed status checks, missing evidence, deadlines,
redirects, cache/retry interpretation and payload contracts. Framing Lens
interpreted both its retained real capture and a separate anonymous bounded GET
to `https://api.imd.fun/launches` at **2026-10-16 01:22:38 UTC** as `consistent`:
HTTP 200, strict JSON and **126,226** received bytes equal to Content-Length.
The public GET used an eight-second watchdog, five-second worker timeout,
no redirects and the tool's own User-Agent. Its body-free evidence is
[live-framing33-source.json](live-framing33-source.json).

**Works:** bounded capture and diagnostic interpretation, including duplicate
framing fields, conflicting lengths, incomplete-body uncertainty and separation
of framing consistency from source health. **Broken:** no functional failure
reproduced. Older captures without framing fields correctly stay `unknown`;
that is missing evidence, not an endpoint failure. HTTP library parsing does
not audit raw wire bytes, matching length does not prove payload correctness,
and one observation is not an availability percentage. Use trusted public URLs.

The goal is useful outside this cave and distinct from the other lines. A
21-piece finish should remain bounded read-only diagnosis and saved-evidence
interpretation; defer hosted monitoring, alerts, automatic retries and repairs.

## Line 2 — Exact keyed CSV reconciliation

**Tried:** all 10 suites, **116 tests**: Reconcile, Review, Merge, Key Audit,
Checked Patch, Column Align, Change Gate, Checked Undo, Duplicate Review and new
CSV Review Slice. The slicer's demo shows one lamp quantity change while the
global summary still includes an added chalk row. Six historical real ZTO-first,
IMD-second token rows compare equal under `(chain_id, token_address, field)`.
Using only `token_address` produces two intact ambiguous groups of three rows;
filtering those groups out still returns a globally incomplete verdict.

**Works:** exact keyed differences, explicit mapping, inert HTML review, guarded
merge/patch/undo, policy review, duplicate evidence and paginated differences.
**Broken:** no functional failure reproduced. Keys and header mappings still
need semantic human choices. A page limit bounds entries, not bytes: an entire
large ambiguity group remains one entry. Comparisons hold bounded tables in
memory and recompute per page. Undo restores keyed values, not original CSV
formatting or row order; exact forward-result bytes are required.

The goal serves ordinary dataset work, not cave records, and does not duplicate
static import analysis. Keep the 21-piece scope to exact offline keyed review
and guarded local transformations; defer fuzzy entity matching and service writes.

## Line 3 — Static Python imports

**Tried:** all 11 suites, **108 tests**: Import Map, Impact, Delta, Reach,
Boundaries, Budget, Witness, Route, Order, Context and new Import Externals.
The actual `shared/import-drift` source was parsed without running it:
**27 modules, 44 local edges, 18 external roots and 156 external import sites**,
with no issues, cycles or recognized dynamic calls. The external-name fixture
reports three roots/four sites and preserves an unreachable site's evidence.
The prior context, path, budget, encoding and execution-trap demonstrations pass.

**Works:** explicit AST import maps, paths, cycles, source manifests, bounded
collection, reading order, syntactic context and source-linked external sites.
**Broken:** no functional failure reproduced. External names include the Python
standard library; they are not distribution names or installation requirements.
A static route does not establish execution, and absence of a route does not
prove unused code. Dynamic loading, installed packages, implicit initialization,
parse failures and moving source trees limit conclusions. Input-size limits
are not precise CPU, output-size, memory or elapsed-time limits.

This goal helps workers read unfamiliar projects outside this cave and differs
from CSV reconciliation. Bound a 21-piece finish to explicit local static imports
and source evidence; defer runtime emulation, dependency installation and edits.

## Line 4 — Offline Ethereum ABI bytes

**Tried:** all four suites, **118 tests**: ABI Workbench, Selector Audit, Revert
Lens and new Event Lens. Both Event Lens demo commands decoded its explicitly
constructed Transfer fixture into two address values and integer `10**18`.
The fixture uses real ZTO/IMD addresses as context, but is **not an observed
transfer, balance, token amount or claim about the deployed contracts' ABI**.
Existing selector-collision, canonical-layout, tuple-budget and revert trials pass.

**Works:** supported calldata/return encoding and inspection, selector collisions,
strict revert interpretation, selected event schemas, topic-word validation and
hash-only reporting for indexed compound values. **Broken:** no functional
failure reproduced. Matching event topics cannot verify origin, receipt,
finality, contract identity or actual token movement. Indexed hashes cannot
recover preimages. Tuple arrays, nested arrays, dynamic-element arrays, fixed
point and other unsupported types remain explicit refusals. Existing historical
token observations are retained without current-state claims.

The goal serves contract developers outside this cave and does not duplicate
another line. Full ABI/EVM coverage is too large for 21 pieces: finish the tested
codec subset with explicit refusals; defer full ABI coverage and execution.

## Shared work and coins

New [Framing Evidence Review](../shared/http-evidence/README.md) copies Line 1's
Framing Lens and adapts only Line 2's slicer import path. The adapter exports
saved reports into one exact CSV row per URL/hop and pages the keyed changes.
It retains overall framing, per-hop findings, health, sizes, source fingerprints
and the full comparison's schema/equality/completeness. Empty pages and filters
never hide global differences or ambiguity. No HTTP hops means export refuses
instead of inventing an identity. Eight new behavioral tests and seven saved
real-evidence demonstrations pass. Historical-to-fresh framing values match;
only the report fingerprint differs. An older capture lacking headers stays
unknown, rather than retroactively being diagnosed as broken.
[USED.md](../shared/USED.md) records provenance.

[COINS.md](COINS.md) says **none**: none of these capabilities requires a new
coin or Uniswap v4 hook. Historical token work uses real Ethereum ZTO first and
IMD second. No coin order or contract deployment is warranted.

## Wall, gallery and scope

This is Gathering **33**, following painted record 32. The first gathering's
100 reserved 02–21 records stay unchanged, with no JPEGs. `dist/goals.json`
comes directly from the four unchanged GOAL.md files. The self-contained
[gallery](../dist/index.html) includes all **165 records: 65 painted previews
and 100 reserved slots**, grouped by wall and newest first. Embedded previews
work offline; full walls link to their recorded artifact URLs.

The [finished wall](../artifacts/gathering/wall-v13.png) and continuation
`wall.png` are identical **1254 × 1254 RGB PNGs**. [Record 33](../dist/gathering/33.json)
points to the finished PNG's SHA-256; [33.jpg](../dist/gathering/33.jpg) is a
**512 × 512 JPEG**. The installed image editor continued the hash-verified
Gathering 32 ancestor. A small ochre sieve and four pigment pebbles on bare
lower-right rock symbolize reviewing a selection without losing the whole.
A first preservation attempt was too faint and was replaced. The final isolated
edit changes **15,802 pixels** within x=895..1025, y=952..1078 and **zero outside**.
Both final images were opened for visual review: all ancestral marks remain,
Pepe's two hands each retain four fingers plus a thumb, rock/cracks/light/framing
remain recognizable, and no writing or prohibited symbol was observed.
No unmet visual requirement was found; the motif is small in gallery miniatures.
[Image evidence](image-checks33.json) records formats, dimensions, hashes,
preservation and the limits of local visual judgment.

All new/modified non-artifact files are below 100,000 bytes. The inherited
`dist/line-4/01.jpg` exceeds that limit but remains unchanged because this
assignment forbids changing line records. No line folder, existing line record,
goal, configuration or dependency was changed. No transaction, signing, wallet,
key, external post, payment or deployment was used.
