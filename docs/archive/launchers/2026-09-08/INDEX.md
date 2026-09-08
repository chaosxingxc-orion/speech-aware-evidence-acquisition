# Archived launcher directories -- 2026-09-08 (WAVE R7)

Group B of the reuse map in
`docs/readiness/2026-09-08-openjiuwen-implementation-assessment-v1.md` section 6.2, under owner
Decision 12-F. The study base rule is **no `launcher/` directory under `docs/checks/`** (study
`CLAUDE.md`, "One base, thin derivations"), and `scripts/checks/engineering_base_check.py`
enforces it in ratchet mode: a launcher directory that is not already in
`scripts/checks/engineering_base_baseline.json` FAILS the gate, so no NEW one can appear. The
45 that predate the rule are the disposal question this index answers.

**Sealed bytes are never rewritten.** An archived launcher is moved with `git mv`, byte for
byte; its sha256 and its original path are recorded below so the move is reversible and the
provenance link is not lost.

## The disposal rule, stated once

A launcher directory is an **ORPHAN** when *nothing outside it names any of its files*: not an
artifact of its own receipt directory, not `docs/exposure-ledger.md`, not a test, not another
document or config. Its scripts are then unreferenced bytes -- whatever the flight sealed is
recorded by sibling artifacts that never name the script -- so moving the directory here costs
no citation, and this index restores the one link there was.

Everything else is **KEPT, immutable**, in place beside the receipt it produced. That includes
every directory a test pins (a test reading a launcher's content is a live reference, and the
launcher is still doing work as the pinned object of a preregistration test) and every
directory `docs/exposure-ledger.md` names.

Applying that rule to all 45: **3 orphans, 42 kept.**

## What moved

| archived path | sha256 | origin |
|---|---|---|
| `2026-08-24-dev500-confirmatory/launch_dev500_confirmatory.py` | `8049422875bd6833a6074a7c43afdd6fb9a87332737b6e6c0ea51a8c387fab5d` | `docs/checks/speech-aware-evidence-acquisition/2026-08-24-dev500-confirmatory/launcher/launch_dev500_confirmatory.py` |
| `2026-09-01-a2t-factor-top1-104-v1/launch_a2t_factor_top1.py` | `73f5c5a2be8515cfb9ab0ea4a211ef334ba81aeaad8413e5fad1c39f0bb1aeb4` | `docs/checks/speech-aware-evidence-acquisition/2026-09-01-a2t-factor-top1-104-v1/launcher/launch_a2t_factor_top1.py` |
| `2026-09-01-a2t-self-consistency-104-v1/launch_a2t_self_consistency.py` | `816dc902695f76ff056eb17a234a492242c6496330d8a3f65bbd9aee5d503bb9` | `docs/checks/speech-aware-evidence-acquisition/2026-09-01-a2t-self-consistency-104-v1/launcher/launch_a2t_self_consistency.py` |

Archived paths are relative to this directory. Each origin receipt directory still holds its
own sealed artifacts and is untouched: `2026-08-24-dev500-confirmatory` keeps its four per-arm
mechanical reports, `2026-09-01-a2t-factor-top1-104-v1` its `mechanism-result.json` and plans,
`2026-09-01-a2t-self-consistency-104-v1` its `result-summary.json` and plans. What left each
directory is a script none of those artifacts ever named.

`docs/checks/.../2026-08-25-dev1000-baseline-lock/launcher/launch_dev1000_baseline_lock.py`
carries a header comment naming `launch_dev500_confirmatory.py`. That file is sealed and is not
edited; the reference resolves through this index.

## The copy-paste families the inventory measured

The assessment's claim was "14 of them are copies of one class". Measured on the tree, the
number is larger and the shape is the same:

| kind | class | launcher directories | launcher files |
|---|---|---|---|
| controller | `RuntimeEmbeddedBlendController` | 11 | 19 |
| adapter | `DirectAdapter` | 2 | 2 |
| controller | `DirectDedupController` | 1 | 1 |
| controller | `DirectObservabilityController` | 1 | 1 |

Nineteen files carry `RuntimeEmbeddedBlendController`, not fourteen -- and the ratchet baseline
already lists all nineteen; the assessment's "14" undercounts the six `dev100-round0` attempt
variants and the three `a2t-g1` blend attempts. Eleven directories carry it. Nine of those
eleven are named by `docs/exposure-ledger.md` and are therefore kept; only
`2026-08-24-dev500-confirmatory` was disposable, and `2026-08-24-dev100-kwiden-k1` survives on
a single readiness-queue citation.

**This is the finding, not a shortfall.** The copy-paste tier is real and the E1/E6 config seams
did make it unnecessary -- but the same bytes that make it duplication also make it evidence,
and a sealed row's citation outranks a tidiness rule. What matters going forward is the gate: no
NEW launcher directory can be added, so the 42 are a fixed, shrinking set rather than a growing
one, and each becomes archivable the moment its last citation is superseded.

## The 45-directory disposition

| receipt directory | files | out-of-base classes | why it is kept |
|---|---|---|---|
| `2026-08-17-pslu-flight` | 9 | -- | own receipt names it (16 artifacts); 1 test pins it |
| `2026-08-18-a2t-s2-flight` | 16 | -- | own receipt names it (4 artifacts); 1 test pins it; `configs/probes/g0-binding/a2t-s2b-flight.json` |
| `2026-08-18-a2t-s2b-flight` | 14 | -- | own receipt names it (4 artifacts); 1 test pins it |
| `2026-08-18-a2t-s2c-flight` | 16 | -- | own receipt names it (4 artifacts); 1 test pins it |
| `2026-08-18-pa2t-a0-flight` | 19 | -- | own receipt names it (2 artifacts); 2 tests pin it |
| `2026-08-18-pslu-s2-flight` | 17 | -- | own receipt names it (4 artifacts); 1 test pins it |
| `2026-08-19-a2t-abst-flight` | 12 | -- | own receipt names it (3 artifacts) |
| `2026-08-19-a2t-pop-flight` | 11 | -- | own receipt names it (3 artifacts) |
| `2026-08-19-pemb1-flight` | 14 | -- | own receipt names it (3 artifacts) |
| `2026-08-19-pemb2-flight` | 17 | -- | own receipt names it (2 artifacts) |
| `2026-08-19-pfew-flight` | 14 | -- | own receipt names it (3 artifacts); 3 tests pin it |
| `2026-08-19-pkey2-flight` | 23 | -- | own receipt names it (5 artifacts); 1 test pins it |
| `2026-08-19-ptrap-flight` | 14 | -- | own receipt names it (3 artifacts); 3 tests pin it |
| `2026-08-20-pcorrf-flight` | 19 | -- | own receipt names it (4 artifacts); 3 tests pin it |
| `2026-08-20-pemb3l-flight` | 21 | -- | own receipt names it (3 artifacts) |
| `2026-08-20-pemb3m-flight` | 12 | -- | own receipt names it (5 artifacts) |
| `2026-08-20-pemb4r-flight` | 22 | -- | own receipt names it (4 artifacts) |
| `2026-08-24-dev100-kwiden-k1` | 1 | `RuntimeEmbeddedBlendController` | `docs/readiness/2026-08-24-kwiden-and-next-experiments-queue.md` |
| `2026-08-24-dev100-round0` | 6 | `DirectDedupController`, `RuntimeEmbeddedBlendController` | own receipt names it (4 artifacts); `docs/exposure-ledger.md` |
| `2026-08-24-dev100-round1` | 1 | `RuntimeEmbeddedBlendController` | `docs/exposure-ledger.md` |
| `2026-08-24-dev100-round2` | 1 | `RuntimeEmbeddedBlendController` | `docs/exposure-ledger.md` |
| `2026-08-24-dev100-round3` | 1 | `RuntimeEmbeddedBlendController` | `docs/exposure-ledger.md` |
| `2026-08-24-dev100-round4` | 1 | `RuntimeEmbeddedBlendController` | `docs/exposure-ledger.md` |
| `2026-08-24-dev100-round5` | 1 | `RuntimeEmbeddedBlendController` | `docs/exposure-ledger.md` |
| `2026-08-24-dev500-confirmatory` | 1 | `DirectObservabilityController`, `RuntimeEmbeddedBlendController` | **ORPHAN -- archived** |
| `2026-08-25-a2t-g1` | 4 | `RuntimeEmbeddedBlendController` | own receipt names it (2 artifacts); `docs/exposure-ledger.md` |
| `2026-08-25-dev100-retain-override` | 1 | `RuntimeEmbeddedBlendController` | `docs/exposure-ledger.md` |
| `2026-08-25-dev1000-baseline-lock` | 1 | `RuntimeEmbeddedBlendController` | `docs/exposure-ledger.md`; `configs/baseline/slurp-phase-blend-cl-v1.json` |
| `2026-09-01-a2t-contract-preserving-cascade-104-v2` | 2 | -- | 2 tests pin it |
| `2026-09-01-a2t-factor-top1-104-v1` | 1 | -- | **ORPHAN -- archived** |
| `2026-09-01-a2t-self-consistency-104-v1` | 1 | -- | **ORPHAN -- archived** |
| `2026-09-01-a2t-self-transcript-cascade-104-v1` | 1 | -- | 1 test pins it |
| `2026-09-02-a2t-executable-ground-qualification-104-v1` | 1 | -- | 1 test pins it; `.../2026-09-02-a2t-construction-semantic-ground-diagnostic-104-v1/launch_diagnostic.py` |
| `2026-09-02-a2t-g3-plain-english-v1` | 1 | -- | 1 test pins it |
| `2026-09-02-a2t-g4-executable-microground-e16` | 1 | -- | 1 test pins it |
| `2026-09-02-a2t-g4-executable-microground-se16` | 1 | -- | `docs/exposure-ledger.md`; 1 test pins it |
| `2026-09-02-a2t-g5-exhaustive-family-fixed16-v1` | 1 | -- | 1 test pins it |
| `2026-09-02-a2t-g6-exhaustive-family-sweep-fixed16-v1` | 1 | -- | 1 test pins it |
| `2026-09-02-a2t-g7-exhaustive-example-ground-fixed16-v1` | 1 | -- | 1 test pins it; `scripts/build_a2t_g7_example_ground.py` |
| `2026-09-03-a2t-g8-action-support-reachability-fixed16-v1` | 1 | -- | 1 test pins it |
| `2026-09-03-a2t-g8b-action-support-reachability-fixed16-v1` | 2 | -- | 2 tests pin it |
| `2026-09-03-a2t-g8c-action-support-reachability-fixed12-v1` | 1 | -- | 1 test pins it |
| `2026-09-03-a2t-native-structured-action-fixed8-v1` | 9 | -- | `docs/exposure-ledger.md`; 4 tests pin it |
| `2026-09-03-a2t-select-fill-agentloop-104-v1` | 3 | `DirectAdapter` | own receipt names it; 3 tests pin it |
| `2026-09-03-a2t-semantic-agentloop-104-v1` | 7 | `DirectAdapter` | own receipt names it; 1 test pins it |

Four of the kept directories -- `2026-09-02-a2t-g4-executable-microground-e16` and `-se16`,
`2026-09-02-a2t-g5-exhaustive-family-fixed16-v1` and
`2026-09-02-a2t-g6-exhaustive-family-sweep-fixed16-v1` -- are receipt directories whose ONLY
content is the launcher. They are preregistration scaffolds whose flight receipts live under
`docs/receipts/a2t/` and in `docs/exposure-ledger.md`, and each is pinned by a test. They are
the next archive candidates once those tests are re-pointed at the receipts themselves.

## Ratchet effect

| rule | before | after |
|---|---|---|
| `launcher_dirs` | 45 | 42 |
| `controller_classes_outside_controllers` | 33 | 31 |

The two controller entries that left are
`2026-08-24-dev500-confirmatory/launcher/launch_dev500_confirmatory.py::DirectObservabilityController`
and `::RuntimeEmbeddedBlendController`. `adapter_subclasses_outside_adapters` and
`probe_modules` are untouched by this wave; the ratchet moves down only.

`tests/unit/test_launcher_archive_index.py` pins this index: every archived file exists at the
recorded sha256, every origin receipt directory still exists and no longer carries a `launcher/`
directory, nothing listed here has reappeared under `docs/checks/`, and the baseline's
`launcher_dirs` rule agrees with the tree.
