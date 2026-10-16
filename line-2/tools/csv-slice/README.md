# CSV Review Slice

Review a manageable window of exact CSV differences without losing the full
comparison verdict. Python 3.9+ standard library only. Run from the repository
root; keep the sibling `csv-reconcile/reconcile.py` with this tool.

One command to see it working:

```sh
python3 -B line-2/tools/csv-slice/slice.py line-2/tools/csv-gate/demo-before.csv line-2/tools/csv-gate/demo-after.csv --key item --kind changed --limit 1
```

This returns the lamp's quantity change from `1` to `2`. The global summary
also retains the added chalk row, even though the selected window excludes it.
Exit **1** means the full files differ; it is expected for this demonstration.
Exit 0 means full equality under the chosen ignored columns; exit 2 means
invalid input/options. An empty window never changes the exit status.

Repeat `--kind` to select added, removed, changed or ambiguous entries. Omit
it for all four. `--match-key '{"item":"lamp"}'` selects an exact key;
for a composite key, provide every key column with a string value. Empty
strings remain literal, with no trimming, numeric conversion or inferred
matching. Repeat `--key` for composite keys and `--ignore` for non-key columns
that should be excluded from comparison.

The JSON has separate `comparison`, `selection`, `window` and `entries`
objects. The comparison always preserves global schema changes, summary,
equality and completeness. Selection counts describe all matching entries
before pagination. Ordering is added, removed, changed, ambiguous, then the
reconciler's sorted key tuples within each kind. `--offset` is zero-based;
`--limit` defaults to 50, from 1 to 1000 entries. Follow `next_offset` until
null. `omitted_entries` counts all entries outside the current window,
including earlier pages. An offset past the end returns no entries.

Each duplicate-key group occupies one entry and retains **every** before and
after occurrence. No group is split or paired automatically. Global
`complete: false` still appears when a filter excludes all ambiguous groups.
There is no unchanged-row section: the global unchanged count remains in the
summary. Field and record data retain the exact reconciler semantics.

What happened when tried: all 12 behavioral tests passed, including page
reconstruction, intact duplicates, composite-key collisions, missing keys,
schema-only evidence and CLI exit statuses. The command above returned one
changed entry, with global counts of one addition and one change. A retained
historical six-row ZTO/IMD snapshot compared equal using
`(chain_id, token_address, field)`; using only `token_address` instead returned
two complete ambiguous groups of three records each. These are offline checks
of retained observations, not fresh chain state.

Run the tests:

```sh
python3 -B -m unittest discover -s line-2/tools/csv-slice -p 'test_*.py' -v
```

Limits: both bounded CSV tables and the full comparison are held in memory
(16 MiB and 100,000 data records per file in the reused reader). A limit bounds
entries, **not bytes**: one ambiguous group can be large. Each invocation
recomputes the comparison, so preserve the same input bytes and options when
following pages; offsets are not durable cursors or authenticated evidence.
No files are modified, no network is used, and selection is not approval to
apply a patch. Keep schema and global completeness evidence in any handoff.
