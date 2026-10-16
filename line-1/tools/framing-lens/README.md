# Framing Lens

Explain declared response length, conflicting framing fields, and missing capture
evidence in a saved Endpoint Sentry GET report. Python 3.9+ standard library only;
no installation or sibling imports. This command works offline from repository root:

```sh
python3 -B line-1/tools/framing-lens/framing_lens.py line-1/tools/framing-lens/observed-live.json
```

On 2026-10-16 at 01:03:18 UTC, one anonymous bounded GET to the real swarm's
`https://api.imd.fun/launches` returned HTTP 200, strict JSON, and 126,226 bytes.
Its declared Content-Length matched. The command prints `consistent`, the saved
source SHA-256, per-hop evidence pointers and findings. `observed-analysis.json`
retains that result. This is historical evidence, not current availability.
No response body is saved. The supplied observation was captured with:

```sh
python3 -B line-1/tools/deadline-sentry/deadline_sentry.py --deadline 8 https://api.imd.fun/launches --timeout 5 --max-redirects 0 --json
```

The producer now retains only Content-Length and Transfer-Encoding as ordered
`framing_headers` pairs, preserving duplicates and explicit absence (`[]`).
Other headers are still excluded except the earlier cache/retry allowlists.
Older captures without this field produce `unknown`, never inferred absence.
The GET and existing success checks have not changed.

The lens accepts Endpoint Sentry and Deadline Sentry reports. Exit 0 means all
recorded hops have consistent supported framing evidence; exit 1 means an issue
or unknown evidence; exit 2 means invalid input. Redirect bodies are not captured,
so redirect routes normally have an unknown overall outcome; each terminal hop
still has its own verdict. Source health is reported separately: a status/JSON
failure can coexist with consistent framing.

Supported findings include invalid or conflicting decimal lengths, equal repeated
lengths, coexistence of Transfer-Encoding and Content-Length, complete-body length
mismatches, and no-body status rules. A 304 length is representation metadata and
is never compared with the empty body. Bare `chunked` means the HTTP library
removed chunk framing; it does not establish that this lens inspected wire bytes.
Other transfer-coding sequences or parameters remain unknown. Connection-delimited
responses remain unknown because there is no independent promised length. Partial
reads, watchdog failures, missing digests, and ignored redirect bodies never become
length mismatches. A body-stage error is conservatively incomplete even when the
producer computed a digest before its own length rejection.

Input must resolve to a regular file within the current workspace, at most 1 MiB.
Strict JSON rejects duplicate keys and nonfinite values. Hop counts, field shapes,
length arithmetic and body byte counts are bounded. Reports are unauthenticated
claims; a matching byte count is neither content validation nor a raw-wire security
audit. The lens never fetches, follows URLs, retries, repairs, or reads response bytes.

Rules follow [RFC 9112 sections 6.2–6.3 and 8](https://www.rfc-editor.org/rfc/rfc9112.html#section-6.3)
and [RFC 9110 section 8.6](https://www.rfc-editor.org/rfc/rfc9110.html#section-8.6).
This is a deliberately conservative subset, not a complete HTTP conformance validator.

Run the offline behavioral checks:

```sh
python3 -B -m unittest discover -s line-1/tools/framing-lens -v
```

Twelve tests pass, covering conflicting and identical duplicate lengths, malformed
ASCII decimals, chunked/competing framing, incomplete bodies, 204/304 semantics,
watchdog and redirect evidence, invalid input shapes, bounded loading and CLI output.
The Endpoint Sentry suite passes 20 tests (including duplicate capture and header
allowlisting); Deadline Sentry passes 11. Synthetic failure cases are labelled by
the tests and are separate from the real retained observation.
