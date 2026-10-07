# Bounded sealed-vector decoding: engineering evidence

The sealed-vector loaders eagerly retained whole-file bytes and a decoded list of
all source lines while building the full Python vector table. Replace only that
transient allocation with bounded I/O and record decoding. Preserve every source
row, the exact vectors, complete source verification, retrieval ordering and all
existing validation. This is an engineering memory reduction; the reported
approximately 20 GiB Windows memory drop remains unexplained by this component.

## Authorization and scope

The latest direct human instruction asks the owners to inspect prepared model-input
cache volume and eager loading, and use batching or on-demand loading where the
problem is demonstrated while keeping data and knowledge contents fixed. Root
prospectively authorized the demonstrated whole-file buffer correction, required
full-source checks and exact output parity, and retained serial integration and
runtime admission. This package implements that bounded loader correction only.
No model/API/tokenizer/encoder/scorer contact, attempt, exposure, admission, retry,
queue, STOP, lock, cache clearing or service modification occurs through this work.
The original frozen natural-four worker and all failed/historical preparation bytes
remain intact. The failed natural-four run is not a qualified natural proof.

## Actual sources and lifetime

The frozen source is `3f3c30af26ad70086970876656ac5a36e1268cc4` at
`/home/chao/saea-worktrees/codex-simple-consumption-natural4-v3`. The active seed
configuration declares Perception retrieval from intent-boundaries and Solver
retrieval from train-exemplars. It declares no supply variants, Perception branches
or dispatch extension. Each store callback retains one query table and one facet
table per declared retrieval phase. Prepared-artifact verification constructs an
uncached binding; the native runtime subsequently constructs and retains a dispatch
binding. Overlap and lifetime therefore need evaluation at the full process level.

The prepared four-row phase-supply envelope is 10,796 bytes; its inline output is
1,888 compact JSON bytes containing selected IDs for four inputs. There is no
separate large output object. The three released snapshots total approximately
15.2 MB on disk. Full knowledge snapshots and the full facet index remain available.

| Active source | File bytes | Rows | Width | Float components |
| --- | ---: | ---: | ---: | ---: |
| train-exemplar facet vectors | 528,621,826 | 11,514 | 2,048 | 23,580,672 |
| exemplar content queries | 47,273,105 | 1,080 | 2,048 | 2,211,840 |
| intent-boundary segment queries | 47,557,177 | 1,080 | 2,048 | 2,211,840 |
| intent-boundary centroid keys | 2,634,031 | 60 | 2,048 | 122,880 |

The largest file is about 504 MiB, which differs from the size of its parsed Python
objects. All four source checksums match the frozen config pins. The largest
record is 46,035 bytes. A rough component-plus-tuple payload estimate for one router
is about 0.84 GiB before dictionaries, IDs, snapshots and allocator overhead; this
is an estimate rather than an RSS measurement. Full-source queries remain loaded,
even for the four active inputs. This change does not selectively drop knowledge
or unselected records. The existing bounded immutable SLURP contract cache is
unchanged.

## Root-owned original allocation profile

`actual-original-profile-bindings-v1.json` raw-pins the root-owned profiler and its
completed external stage/guard metadata. It used the exact frozen original loader,
the unchanged facet input pin, the released snapshot and the first configured
sealed query. It called the existing key-matrix cache and repeated the same query
with the configured retrieval bound. The existing 4 GiB startup/running guard
completed successfully; the helper had a 180-second limit and one owned process.
No inference or official scoring ran.

The original 528,621,826-byte vector file loaded in 7.80 seconds. The measured
process peak was 1,960.84 MiB; post-load RSS was 1,456.95 MiB. The released snapshot
selected 8,554 of the 11,514 loaded key vectors for a read-only 8,554-by-2,048
float64 matrix (140,148,736 bytes), rather than inventing a full-file matrix.
Post-matrix RSS was 1,564.66 MiB. Two repeated recalls returned the same digest and
reused the same matrix object. Deleting local references left 1,498.72 MiB RSS
because existing bounded process-global key caches remain until process exit.
Windows available memory stayed at or above 24.92 GiB. This reproduces a roughly
2 GiB component allocation, not the reported roughly 20 GiB loss. It is not a
full natural-four runtime profile or a causal diagnosis of that loss.

## Prospective change and proof

`rails/phase_supply.py` adds one private helper reused by the two existing loaders.
The first bounded pass verifies the full SHA-256 and UTF-8 source before any JSON
parsing; checksum refusal retains precedence over decoding and JSON errors. The
second pass incrementally decodes records through `str.splitlines` semantics,
including CRLF across chunks and all previously accepted Unicode line boundaries.
It rehashes that same open source before returning a table. No partial table escapes
on late corruption or a same-size change between passes. Existing generic numerical
acceptance and stricter segment finite/nonzero/coverage checks are unchanged.

I/O uses the standard library buffer size and retains at most a chunk plus one
logical record outside the growing validated table. No experiment batch/window
policy or arbitrary maximum-record rejection is added. The full table remains
resident because existing retrieval still needs it.

The synthetic profile uses fresh child processes and equivalent 2,048-component
rows; it never reads actual task values or model outputs. Every old/new full-table
float.hex digest matches, and synthetic input file hashes remain unchanged.

| Loader / rows | File MiB | Original traced peak MiB | Streaming traced peak MiB | Retained MiB |
| --- | ---: | ---: | ---: | ---: |
| vectors / 128 | 5.01 | 18.09 | 8.20 | 8.05 |
| vectors / 1,024 | 40.05 | 144.52 | 64.49 | 64.35 |
| segments / 128 | 5.03 | 18.17 | 8.22 | 8.08 |
| segments / 1,024 | 40.25 | 145.15 | 64.73 | 64.58 |

When file size and retained table scale eightfold, original transient allocation
above the table scales from about 10 MB to 84 MB; streaming transient allocation
stays around 0.15 MB for the same record width. Retained tables are unchanged apart
from a few hundred bytes. Tracemalloc instrumentation raises RSS, so its process
RSS cannot be substituted for the uninstrumented actual-source profile. This
proves removal of proportional transient buffers, not a constant total memory cap.

The focused old/new loader suite passes 72 tests, including late-record validation,
changed-source refusal, checksum-before-UTF8/JSON precedence, exact float values,
all line boundaries, segment frame coverage and existing nonfinite semantics.
Focused lint also passes. `validation-v1.json` records these checks. The profiled
source and final source differ only by wrapping the line-ending tuple; the immutable
profile is preserved and `final-source-binding-v1.json` records that succession.

## Remaining prerequisites

Root serially integrates this reviewed commit. Changing the shared source changes
prepared-artifact fingerprints: prior C4/natural-four/N20 envelopes must not be
called source-compatible or rewritten in place. Any subsequent natural attempt or
N20 admission requires its own prospective source-bound preparation and existing
root admission gates. This package grants no runtime authority. Further diagnosis
should measure the actual native runtime and Windows/WSL accounting by stage if
the original large drop recurs; source inspection alone does not establish it.
