# Import Externals

Find the external import names in an unfamiliar Python project, their exact
source sites, and shortest local-import routes from detected entry points to
modules mentioning those names. Python standard library only, offline; inspected
source is parsed as bytes and never imported or executed.

From the repository root, with Python 3.9 or newer:

```sh
python3 -B line-3/tools/import-externals/externals.py line-3/tools/import-externals/examples
```

This working demonstration reports three name roots and four sites. `main`
reaches `json` and `urllib` through `pkg.worker`; `decimal` appears in `spare`
with no route from `main`. The two `urllib` from-import sites stay separate.
No package installation or configuration is needed. When copying this tool,
keep sibling `import-budget/budget.py` and `import-map/import_map.py` too.

`--json` emits the full inventory, collection limits, source-byte manifest with
SHA-256 hashes, retained scan issues, cycles and dynamic-call sites. Text output
shows all external sites, routes and warning counts; use JSON for warning detail.
The saved report identifies the bytes inspected, without authenticating them or
guaranteeing an atomic snapshot of a changing tree.

Use repeated `--from MODULE` to replace detected main-guard entry points with
chosen exact local module names. Routes use directed explicit local-import edges.
For each external root and start, the result selects one shortest route to any
module containing that external name, breaking ties by the lexicographically
first full module path. A route ends at a module containing an external import;
its distance counts local edges only. A direct site therefore has distance zero.
All external sites stay in the inventory, including unreachable sites. A group
with no route does not prove dead code or an unnecessary dependency. Conditional
and function-body imports count syntactically regardless of runtime behavior.

External means the inherited mapper did not resolve the name inside the chosen
import root. It includes standard-library names; a top-level name is **not** a
package-distribution name or an installation requirement. No installed-package
lookup, version guessing, manifest edit, or dependency installation occurs.
Local shadowing and namespaces follow Import Map's rules. Unresolved local and
relative imports remain warnings, rather than being guessed as external names.
Choose the actual import root explicitly (for example `src/`).

Input budgets are inherited from Import Budget: `--max-files` (1000),
`--max-file-bytes` (262144), `--max-total-bytes` (8388608), `--max-entries` (20000),
and `--max-depth` (64). All must be positive integers. The root must resolve
inside the current workspace. Hidden/dependency directories, symlinks and
nonregular files are skipped as documented by Import Budget. These input limits
do not precisely bound CPU, elapsed time, memory or output size. Routes across
many selected starts can make a large report.

Exit 0 means collection and inventory completed. `--strict` returns 1 on scan
issues, cycles or recognized dynamic calls; ordinary external imports are not
errors. Exit 2 refuses invalid input, unknown starts, failed reads or exceeded
budgets, without presenting a partial inventory as completed. Argument syntax
errors use argparse's stderr output. Dynamic imports, implicit package startup,
installed packages, external callers, import hooks and runtime conditions remain
outside this static model.

## What happened when tried

The example above succeeded. Nine behavioral tests passed, covering grouping,
aliases and duplicate sites, shortest-path tie breaking, selected/unreachable
starts, local shadowing, namespaces, unresolved relative imports, conditions,
star imports, parse/collision/dynamic warnings, a cycle with a 1200-edge path,
budget refusals, strict exits, determinism, and an execution trap that did not run.
The unchanged mapper and collector also passed their 27 regression tests on
scratch copies.

```sh
python3 -B -m unittest discover -s line-3/tools/import-externals -v
```

The real `shared/import-drift` worker was scanned as source only: 27 modules,
44 local edges, 18 external roots, 156 external sites, and no issues, cycles or
recognized dynamic calls. The compact [observed-source.json](observed-source.json)
retains the full result and exact source hashes. Its standard-library names are
external to that import root; this observation makes no claim about third-party
requirements. Reproduce it without running the worker:

```sh
python3 -B line-3/tools/import-externals/externals.py shared/import-drift --json --strict
```
