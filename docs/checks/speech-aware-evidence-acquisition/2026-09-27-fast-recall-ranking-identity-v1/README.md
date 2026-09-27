# Fast recall: the exemplar cosine sweep vectorised, every delivered recall bit-identical

Engineering-base follow-up to owner decision 159 (the dispatcher slot fill). The slot-fill gap decomposition
(`docs/checks/speech-aware-evidence-acquisition/2026-09-27-dispatch-slot-fill-byte-identity-v1/`, branch
`fable/slotfill`) located the largest share of the Solver #1 turnaround in the train-exemplars recall:
`rails.kb_policy.multidim_recall`, a pure-Python cosine over every exemplar key vector, run synchronously on the
one event loop every in-flight row shares. This receipt makes that recall itself fast for every cell, with no
config switch, and proves the delivered recall unchanged. Model-free throughout: zero model, server, encoder,
scorer, endpoint and network contacts; ports 8080 and 8081 were never touched.

## 1. Where the time went (profile, one Fold A row, CPU only)

cProfile of one `multidim_recall` call on the PLAN cell's exemplar store (snapshot
`size-pool-annotated-exemplars`, 9,354 content facets x 2,048 floats, k = 20): 4.15 s under the profiler, of
which 2.76 s is the `_cosine_with_norms` dot-product generator (19,166,346 steps = 9,354 pairs x 2,049 generator steps)
and 1.24 s the builtin `sum` driving it -- 97 % of the call. Key norms were already cached (`_KEY_NORMS`),
vector loading and JSON decoding happen once per flight (`load_sealed_vectors`), and the per-facet Python
checks cost about 50 ms. Unprofiled: 1.1 s per warm row, 2.0 s on the first row of a process (key norms).

The dumps also expose a second, hidden cost of the old path: `_KEY_NORMS.retain` keeps only the key set the
last recall touched, so a process that alternates key sets (exemplars, then intent boundaries) recomputes all
9,354 exemplar norms on its next exemplar recall. In the old-tree dump the first exemplar call of every row
(k = 8, right after the previous row's intent-boundary calls) averaged 2.37 s against 1.32 s for the next two.

## 2. The change (`src/speech_aware_evidence_acquisition/rails/kb_policy.py`)

* **A per-process key matrix.** `_KeyMatrixCache` holds the float64 matrix of one key set, keyed by the
  identity of its key tuple objects (a flight's vectors are the same tuples for its whole life), built once
  per key set per process under a build lock, bounded to four key sets (least recently used dropped). The
  norms it carries are `_KEY_NORMS` / `_l2_norm` floats -- the exact loop's own.
* **BLAS chooses, the exact loop scores.** `_preselected_exact_scores` computes every cosine with one
  matrix-vector product, keeps every row whose BLAS cosine reaches `max(k-th BLAS cosine, 0) - 2e-9`, and
  re-scores exactly those rows with `_cosine_with_norms` -- the unchanged builtin-`sum` arithmetic. The
  caller's stable `(-score, facet_id)` sort and `[:k]` truncation are untouched, so the delivered mapping is
  the exact loop's: the same facets, the same order, the same score bits.
* **Why 2e-9 is enough (the proof, in the function's docstring).** A BLAS cosine and the builtin-`sum`
  cosine of one pair, divided by the same `fl(norm_q * norm_k)`, differ by at most `2 gamma_n + 4u`
  (`u = 2**-53`): 4.6e-13 at width 2,048, under 2.4e-10 at the widest width admitted (`2**20`); every
  admitted norm lies in `[2**-400, 2**400]` so nothing overflows or underflows into the bound. With slack
  `delta = 1e-9 >= |s - t|`, every row of the exact top k has BLAS cosine `>= max(T, 0) - 2 delta` (T the
  k-th BLAS cosine), ties included. Measured on the real rosters the largest disagreement is 7.2e-16.
* **The exact loop still runs** for list vectors, non-`float` components, non-finite values, out-of-range
  norms, widths above `2**20`, or no numpy; a refused key set is remembered so the refusal is not
  re-derived per row. `_KEY_NORMS` keeps its contract (the existing norm-cache tests pass unchanged).
* The per-facet eligibility checks short-circuit the ABC `isinstance` for `dict` / `tuple` (both ARE a
  Mapping / Sequence); any other type takes the full check, so admission is unchanged.

## 3. Identity proofs

**Every delivered recall, three full rosters, old tree vs new tree.** `scripts/analysis/fast_recall/
recall_dump.py` ran once on a pristine export of master `c369d864` (four fork workers) and once on this
tree (one process), writing every recall mapping with its insertion order and every score as `float.hex`;
`compare_dumps.py` compared them record by record:

| roster (query file) | rows | train-exemplars k | intent-boundaries (key encoding) k | centroid keys k |
| --- | ---: | --- | --- | --- |
| TRAIN Fold A | 1,080 | 8, 20, 60 | 8, 16, 60 (segment recall) | 8, 60 |
| DEV-2000-ADDED | 1,000 | 8, 20, 60 | 8, 16, 60 | 8, 60 |
| TRAIN Fold B | 1,080 | 8, 20, 60 | 8, 16, 60 | 8, 60 |

25,280 records (3,160 rows x 8), **0 mismatches**; both dumps hash to
`538444aef3b458a9a337851b70cd04c590fe8d7c3103defba6f94fb9a169b47c`. The exemplar store is the PLAN cell's
(`size-pool-annotated-exemplars`, keys `vectors/slurp-kus3/facet-vectors.jsonl`); the intent-boundary store
is `intent-boundaries-v1` with the two committed key files (`SAEA-SLURP-INTENT-BOUNDARY-KEY-ENCODING-V1`,
`SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1`). A dump taken before the `dict`/`tuple` short-circuit landed
is byte-identical to the final one.

**Near-ties on the real rosters.** `flip_census.py` asked, for 28,440 real recall calls, whether ranking by
the BLAS floats alone would have delivered a different ordered top k: **0 order flips, 0 membership flips**;
the pre-selection re-scored exactly k rows every time (no real row lies within 2e-9 of a k-th score). No flip
was found, so none needed resolving on real data; the resolution is structural and is exercised where it
matters by the synthetic fixture below.

**Synthetic near-ties** (`tests/unit/test_kb_policy_vectorised_recall.py`). A cluster of 184 keys that are
permutations of one base vector, recalled by a constant query, has one real cosine and floats that differ only
by summation order (plus exact value duplicates as distinct objects, a zero-norm key and a background). The
test asserts that the BLAS floats differ from the exact ones AND that ranking by them would deliver a
different top 60, and that the fast path's recall is nevertheless bit-identical to the exact loop and to the
per-pair oracle of `2afb4b5c`, at k = 1 ... 500, for three seeds; also segment recall, every fallback, the
cache's identity and bound, and two real-roster checks against `SPEECHRL_DATA_DIR`.

**First-phase supplies.** `mint_supply.py` built each cell with `core.flight.factory.build_flight_runtime`,
composed it without its committed pin (item E16: the pin binds its flip commit's implementation files, as
the slot-fill bench does) and minted the supply model-free with `FlightRuntime.prepare_phase_supply`:

| cell | registered pin | pinned output sha256 | minted on this tree | output block |
| --- | --- | --- | --- | --- |
| PLAN (`slurp-native-default-plan-lock-v1`) | `prepared/SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1/phase-supply-v1.json` | `ba5e1faa...` | `ba5e1faa...` | equal |
| AGREE (`slurp-native-stage3-agree-w1-fold-a-v1`) | `prepared/SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1/phase-supply-v2.json` | `eab5c61e...` | `eab5c61e...` | equal |

The artifact hashes differ (`12f4f390...`, `6da201b6...`) only because the artifact identity binds the implementation files (item E16);
a flip on this code re-pins with no `--allow-output-change`.

**End to end.** The slot-fill bench (`scripts/analysis/slotfill_fake_server_harness.py` from `fable/slotfill`
commit `583f04c9`, run as an untracked copy and not committed here) drove the REAL locked PLAN cell through
the real dispatch against its fake four-slot server on master and on this tree with one shared scratch run id
(`--pair FASTRECALL-IDPAIR`, 60 rows, 285 contacts): all 285 request bodies, all client payloads, every sealed
dispatch row, every canonical output row and the normalised trace multiset (`7d581ad7...`) are identical.

## 4. Timings

Per-row exemplar recall (PLAN store, k = 20, first 100 Fold A rows, one process, load average about 4):

| tree | first row | warm median | warm mean | warm p90 |
| --- | ---: | ---: | ---: | ---: |
| master | 1.44 s | 783 ms | 786 ms | 848 ms |
| fable/fastrecall | 1.30 s (matrix build) | 17.9 ms | 21.5 ms | 36.3 ms |
| fable/fastrecall, `OPENBLAS_NUM_THREADS=1` | 1.38 s | 15.3 ms | 17.0 ms | 29.1 ms |

About 44x on a warm row. Under the heavy host load of the proof dumps (load average 30-60) the means were
1.31-2.37 s old (four workers) against 47-73 ms new.

## 5. Slot-fill bench, key off (contacts per hour of the contact window)

Service model `measured` (ROLL-2's sealed per-role server times), 60 rows, 285 contacts, dispatch key absent,
master and this tree interleaved:

| pair | host load | master | fast recall | gain | empty slot share | Solver role input mean |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| 3 | 2-4 | 2,912.4 | 3,082.2 | +5.8 % | 10.2 % -> 4.9 % | 0.98 s -> 0.29 s |
| 2 | 31-34 | 2,669.1 | 2,999.6 | +12.4 % | 17.6 % -> 7.3 % | 1.66 s -> 0.44 s |
| 1 | 62 / 40 | 2,123.4 | 2,984.0 | (loads differ) | 34.3 % -> 7.8 % | 3.21 s -> 0.46 s |

On a quiet host the fast recall alone is worth about +6 % contacts per hour of window -- the same as the
slot-fill key's three switches together on its bench (+6.0 %, 2,736 -> 2,899), and it lands above that
key-on figure in absolute terms; the gain grows with host CPU contention because the old recall was CPU-bound
on the shared loop. The fast recall and `recall_prefetch` address the same cost, so their gains are not expected to add; the
key's two other switches are independent of it. The remaining Solver role-input time (about 0.27 s per row
after the one-off matrix build) is spent outside recall -- snapshot validation and content hashing
(`KnowledgeSnapshot.validate`, `qualify_supply`'s `content_hash`) and the attempt store's usage scan -- the
next levers, not addressed here. The one-off build (1.3-2.6 s on the first Solver row of a process) is the
key-norm pass the old path also paid on its first row.

## Files

| file | what it holds |
| --- | --- |
| `proof-summary-v1.json` | every number above: dump hashes and per-(roster, store, k) record counts, the near-tie census, the two minted supplies, the end-to-end pair, the timings and the bench table |
| `MANIFEST.sha256` | `<sha256> *<relpath>` over every other file |

Tooling: `scripts/analysis/fast_recall/` (`recall_io.py`, `recall_dump.py`, `compare_dumps.py`,
`flip_census.py`, `mint_supply.py`, `recall_timing.py`); run under WSL with `PYTHONPATH=<tree>/src`,
`SPEECHRL_DATA_DIR` set and `PYTHONDONTWRITEBYTECODE=1`.
