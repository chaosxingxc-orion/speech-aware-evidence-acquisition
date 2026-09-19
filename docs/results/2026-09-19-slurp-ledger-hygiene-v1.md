# Ledger hygiene — the 34 back-catalogue rows the finite-completion gate reported, closed or superseded

2026-09-19, model-free. Zero model, tokenizer, encoder, scorer, network and GPU contacts; read-only
under `SPEECHRL_DATA_DIR`. No utterance text, transcript or gold label was read, printed or
persisted: the only files opened under the data root are attempt records
(`attempts/<run id>/*.json`) and run manifests (`runs/<run id>/<attempt>/*.run-manifest.json`), and
only their `state`, `status` and `actual` counters were read.

This note decides no task quality, no comparator, no admission and no carrier claim. It closes
registrations.

## 1. Why

`scripts/checks/finite_completion_policy_check.py` (item E13, merged d0b28a95) treats a generation
plan as IN SCOPE when its run id has an exposure-ledger row with `consumed = no` **and** its cell's
`readiness.state` is `ready` or `held`. At 3ced28ea it reported **56 findings over 34 run ids**.
None of them was the live queue. Every one was a back-catalogue cell whose ledger row was never
closed: thirteen had flown (some to a COMPLETED manifest, some to an abort), twenty-one had never
contacted the model at all. A registration nobody closed keeps looking live to every gate that reads
the ledger, which is how a dead cell came to be told to arm a key it will never use.

The fates below are read from the data root, not asserted. `actual` is the attempt record's own
`{calls, audio_seconds}`.

## 2. What was done

| run id | readiness package | fate | actuals (calls / audio) | action | verdict pointer |
| --- | --- | --- | ---: | --- | --- |
| `SAEA-SLURP-DIRECT-VS-NATIVE-SYSTEM-DEV1000-V1` | `2026-09-13-slurp-direct-vs-native-system-dev1000-v1` | FLOWN, FINALIZED, manifest COMPLETED | 5,020 / 14,476.19 s | row closed | `docs/readiness/2026-09-13-slurp-direct-vs-native-system-v1-verdict.md` |
| `SAEA-SLURP-DIRECT-VS-NATIVE-SYSTEM-DEV1000-REPLICATION-V1` | `2026-09-13-slurp-direct-vs-native-system-dev1000-replication-v1` | FLOWN, ABORTED (root stopped the campaign after native revision-limit exhaustion) | 1,329 / 3,595.78 s | row closed | none |
| `SAEA-SLURP-NATIVE-TERMINAL-SYSTEM-DEV1000-RECOVERY-V1` | `2026-09-13-slurp-native-terminal-system-dev1000-recovery-v1` | FLOWN, ABORTED (Perception completion, finish reason `length`) | 629 / 1,733.29 s | row closed | none |
| `SAEA-SLURP-NATIVE-BOUNDED-PERCEPTION-PROOF-V1` | `2026-09-13-slurp-native-bounded-perception-proof-v1` | FLOWN, FINALIZED, manifest COMPLETED | 20 / 52.98 s | row closed | none (engineering proof) |
| `SAEA-SLURP-NATIVE-DUAL-STORE-DEV1000-REBOOT-RECOVERY-V1` | `2026-09-14-slurp-direct-vs-native-dual-store-reboot-recovery-v1` | FLOWN, FINALIZED, manifest COMPLETED | 5,046 / 14,580.56 s | row closed | none |
| `SAEA-SLURP-NATIVE-DUAL-STORE-DEV1000-BASE-REPLICATION-V1` | `2026-09-14-slurp-dual-store-base-replication-v1` | FLOWN, FINALIZED, manifest COMPLETED | 5,040 / 14,552.03 s | row closed | `docs/results/2026-09-17-slurp-a1-use-projection-audit-v1.md` (reads its sealed outputs) |
| `SAEA-SLURP-NATIVE-DUAL-STORE-TRAIN-FOLD-A-ANCHOR-V1` | `2026-09-14-slurp-native-dual-store-train-fold-a-anchor-v1` | FLOWN, ABORTED (Solver contact, remote end closed) | 5 / 12.58 s | row closed | none; the sealed anchor is its recovery `…-ANCHOR-RECOVERY-V1` |
| `SAEA-SLURP-NATIVE-BROAD-FACTORED-TRAIN-FOLD-A-V1` | `2026-09-15-slurp-broad-factored-train-a-v1` | FLOWN, FINALIZED, manifest COMPLETED | 5,407 / 15,448.24 s | row closed | `docs/results/2026-09-16-slurp-broad-factored-train-a.md` |
| `SAEA-SLURP-NATIVE-CANDIDATE-FIVE-TRAIN-FOLD-A-V1` | `2026-09-16-slurp-native-candidate-five-train-fold-a-v1` | FLOWN, FINALIZED, manifest COMPLETED | 5,421 / 15,477.03 s | row closed | `docs/results/2026-09-16-slurp-candidate-five-train-a.md` |
| `SAEA-SLURP-NATIVE-TYPED-ROLE-CONTEXT-TRAIN-FOLD-A-V1` | `2026-09-16-slurp-typed-role-context-system-vs-direct-train-fold-a-v1` | FLOWN, ABORTED (Reviewer tool request with no source-bound observation) | 507 / 1,080.82 s | row closed | `docs/results/2026-09-17-slurp-node-context-audit-v1.md` |
| `SAEA-SLURP-NATIVE-TYPED-ROLE-CONTEXT-TRAIN-FOLD-A-RECOVERY-V1` | `2026-09-16-slurp-typed-context-system-recovery-v1` | FLOWN, ABORTED (Reviewer contact exceeded the registered capacity; second failure closed the flight) | 6,645 / 18,136.49 s | row closed | `docs/receipts/2026-09-16-typed-context-terminal-exposure.md` |
| `SAEA-SLURP-NATIVE-TYPED-CONTEXT-TOOL-REJECTION-PROOF4-V1` | `2026-09-16-slurp-typed-context-system-recovery-v1` | FLOWN, FINALIZED, manifest COMPLETED | 44 / 116.55 s | row closed | none (engineering proof) |
| `SAEA-SLURP-CANDIDATE-SLOT-VIEW-PROOF4-V1` | `2026-09-16-slurp-candidate-slot-view-proof4-v1` | FLOWN, ABORTED (first Solver wire projection refused a target-slot mismatch) | 4 / 10.60 s | row closed | none (engineering proof) |
| `SAEA-SLURP-NATIVE-DUAL-STORE-DEV1000-V1` | `2026-09-13-slurp-direct-vs-native-dual-store-dev1000-v1` | NEVER STARTED (no attempt record) | 0 / 0.00 s | row closed, cell superseded | successor `…-DEV1000-REBOOT-RECOVERY-V1` |
| `SAEA-SLURP-NATIVE-KNOWLEDGE-PROOF-V1` | `2026-09-13-slurp-native-knowledge-proof-v1` | NEVER STARTED (session-attach receipt only, no attempt record, no trace) | 0 / 0.00 s | row closed, cell superseded | anchor-based SLURP v2 program |
| `SAEA-SLURP-NATIVE-KNOWLEDGE-PROOF-RECOVERY-V1` | `2026-09-13-slurp-native-knowledge-proof-recovery-v1` | NEVER STARTED (attempt ABORTED at the first Perception binding check, zero contacts) | 0 / 0.00 s | row closed, cell superseded | anchor-based SLURP v2 program |
| `SAEA-SLURP-NATIVE-EXEMPLARS-K20-TRAIN-FOLD-A-V1` | `2026-09-17-slurp-b1-exemplars-k20-v1` | NEVER STARTED | 0 / 0.00 s | row closed, cell superseded | cell B1 anchor-base v2 |
| `SAEA-SLURP-NATIVE-EXEMPLARS-K20-TWIN-TRAIN-FOLD-A-V1` | `2026-09-17-slurp-b1-exemplars-k20-v1` | NEVER STARTED | 0 / 0.00 s | row closed, cell superseded | cell B1 anchor-base v2 |
| `SAEA-SLURP-NATIVE-EXEMPLARS-K20-SMOKE-4-V1` | `2026-09-17-slurp-b1-exemplars-k20-v1` | NEVER STARTED | 0 / 0.00 s | row closed, cell superseded | cell B1 anchor-base v2 |
| `SAEA-SLURP-NATIVE-SAMPLES5-TRAIN-FOLD-A-V1` | `2026-09-17-slurp-b2-samples5-v1` | NEVER STARTED | 0 / 0.00 s | row closed, cell superseded | cell B2 anchor-base v2, then v3 |
| `SAEA-SLURP-NATIVE-SAMPLES5-GREEDY-TWIN-TRAIN-FOLD-A-V1` | `2026-09-17-slurp-b2-samples5-v1` | NEVER STARTED | 0 / 0.00 s | row closed, cell superseded | cell B2 anchor-base v2, then v3 |
| `SAEA-SLURP-NATIVE-SAMPLES5-SMOKE-4-V1` | `2026-09-17-slurp-b2-samples5-v1` | NEVER STARTED | 0 / 0.00 s | row closed, cell superseded | cell B2 anchor-base v2, then v3 |
| `SAEA-SLURP-NATIVE-SAMPLES5-ANCHOR-TRAIN-FOLD-A-V2` | `2026-09-17-slurp-b2-samples5-anchor-v2` | NEVER STARTED | 0 / 0.00 s | row closed, cell superseded | cell B2 v3 after E2c |
| `SAEA-SLURP-NATIVE-SAMPLES5-ANCHOR-SMOKE-4-V2` | `2026-09-17-slurp-b2-samples5-anchor-v2` | NEVER STARTED | 0 / 0.00 s | row closed, cell superseded | cell B2 v3 after E2c |
| `SAEA-SLURP-NATIVE-SAMPLES5-ANCHOR-GREEDY-TWIN-TRAIN-FOLD-A-V2` | `2026-09-17-slurp-b2-samples5-anchor-v2` | NEVER STARTED | 0 / 0.00 s | row closed, cell superseded | cell B2 v3 after E2c |
| `SAEA-SLURP-NATIVE-SAMPLES5-ANCHOR-GREEDY-TWIN-TRAIN-FOLD-A-V3` | `2026-09-17-slurp-b2-samples5-anchor-v3` | NEVER STARTED | 0 / 0.00 s | row closed unflown, cell superseded | none; the twin is not due under owner decisions 8/15 |
| `SAEA-SLURP-NATIVE-FALLBACK-QUIRKY-INTENT-V2-TRAIN-FOLD-A-V1` | `2026-09-17-slurp-b4-org-cells-v1` | NEVER STARTED | 0 / 0.00 s | row closed, cell superseded | cell B4 anchor-base v2 |
| `SAEA-SLURP-NATIVE-FALLBACK-QUIRKY-INTENT-V2-SMOKE-4-V1` | `2026-09-17-slurp-b4-org-cells-v1` | NEVER STARTED | 0 / 0.00 s | row closed, cell superseded | cell B4 anchor-base v2 |
| `SAEA-SLURP-NATIVE-SLOT-STORE-V2-TRAIN-FOLD-A-V1` | `2026-09-17-slurp-b4-org-cells-v1` | NEVER STARTED | 0 / 0.00 s | row closed, cell superseded | cell B4 anchor-base v2 (B4b admitted and replicated) |
| `SAEA-SLURP-NATIVE-SLOT-STORE-V2-SMOKE-4-V1` | `2026-09-17-slurp-b4-org-cells-v1` | NEVER STARTED | 0 / 0.00 s | row closed, cell superseded | cell B4 anchor-base v2 (B4b admitted and replicated) |
| `SAEA-SLURP-NATIVE-INTENT-STORE-V2-TRAIN-FOLD-A-V1` | `2026-09-17-slurp-b4-org-cells-v1` | NEVER STARTED | 0 / 0.00 s | row closed, cell superseded | cell B4 anchor-base v2 |
| `SAEA-SLURP-NATIVE-NCP-L2-REVIEW-CLEAN-ANCHOR-TRAIN-FOLD-A-V1` | `2026-09-17-slurp-b7b-ncp-l2-anchor-v1` | NEVER STARTED | 0 / 0.00 s | row closed, cell superseded | re-registration against cell B7a v2 |
| `SAEA-SLURP-NATIVE-NCP-L2-REVIEW-CLEAN-ANCHOR-SMOKE-4-V1` | `2026-09-17-slurp-b7b-ncp-l2-anchor-v1` | NEVER STARTED | 0 / 0.00 s | row closed, cell superseded | re-registration against cell B7a v2 |
| `SAEA-SLURP-NATIVE-INTENT-STORE-V2-ANCHOR-TRAIN-FOLD-A-V2` | `2026-09-17-slurp-b4-org-cells-anchor-v2` | NEVER STARTED, **still due** | 0 / 0.00 s | **left open on purpose** (section 4) | none yet |

Counts: **13 flown rows closed, 20 never-flown rows closed and their cells marked `superseded`, 1
left open.** No row was deleted, reordered, or changed in any column but `consumed` (column 9, `no`
to `yes`) and `notes` (column 15, one appended English sentence). No fragment was changed but its
one cell's `readiness.state` and one appended `readiness.reason` sentence; every fragment diff is
exactly two lines.

## 3. Two findings worth keeping

**The finite-completion failure mode is not new.** `SAEA-SLURP-NATIVE-TERMINAL-SYSTEM-DEV1000-
RECOVERY-V1` died on 2026-09-13 at 629 contacts with a Perception completion whose finish reason was
`length` — the same condition that killed the B7a recovery arm at 1,451 contacts on 2026-09-18, six
days and one whole cell family later. The exposure scan
(`docs/results/2026-09-19-slurp-finite-completion-exposure-v1.md`) counted zero finite completions
among **sealed** rows and was right to: this one aborted, so it sealed nothing and the scan never
saw it. Two flights, same leaf, one of them before the key existed.

**Closing a row shadows readiness.** After this pass the gate's summary reports `0 not-live cell(s)`
and `119 consumed`, not twenty `superseded` cells: `consumed = yes` is tested first, so the
superseded state never reaches the readiness clause. The fragment edits are therefore documentation,
not the mechanism — the ledger row is what takes a cell out of scope. That is also why a FLOWN cell
needed no fragment edit at all.

## 4. The one row deliberately left open

`SAEA-SLURP-NATIVE-INTENT-STORE-V2-ANCHOR-TRAIN-FOLD-A-V2` (cell B4c, intent-boundary store v2 on
the sealed dual-store anchor) has never flown, but it is **not** back-catalogue:

* its own registration carries owner decision 9 of 2026-09-17 — *this cell flies ONLY IF cell B4a
  admits* — and cell B4a v2 is in flight now;
* the 2026-09-18 B5e verdict restates the live order as "keep admitting B2 v3, B7a and B4a (B4c only
  if B4a admits)";
* its primary comparator, the sealed dual-store anchor recovery, exists and is sealed. Nothing about
  this registration is dead.

So its row stays `consumed = no` and its cell stays `held`, and the gate keeps reporting its two
plans. **That finding is correct and the repair is the coordinator's, not this pass's:** re-pin the
cell with `scripts/flights/repin_cell.py` so `slurp-native-anchor-intent-store-v2-train-fold-a-v2`
declares `native_episode.finite_completion_policy: "deliver-latest-or-abstain"` and the package's
dependent hashes are recomputed in the same cycle. This pass touched neither that package nor that
baseline. Cell B7b's two rows were superseded instead, on a different fact: their primary comparator
is the sealed bytes of cell B7a **v1**, which was closed unsealed after its second failure
(`docs/results/2026-09-19-slurp-b7a-v1-closure.md`), so those registrations can never open as
written.

## 5. Gates

| check | before | after |
| --- | --- | --- |
| `scripts/checks/finite_completion_policy_check.py` | FAIL, 56 findings over 34 run ids | FAIL, 2 findings, both cell B4c v2 (section 4) |
| `scripts/checks/results_ledger_check.py` | PASS | PASS |
| `scripts/checks/harness_admission_check.py` | PASS | PASS |
| `scripts/checks/engineering_base_check.py` | PASS | PASS |
| `pytest tests/unit/test_finite_completion_policy_check.py` | 13 passed | 13 passed |

`results_ledger_check.py` reports seven more findings than before (56 to 63), all of them
cross-check B — "has a closed exposure-ledger row and no verdict note". That is the intended
consequence of closing rows: an engineering proof, an aborted flight and a never-started
registration each close without a verdict note, and cross-check B lists verdict notes under
`docs/readiness/` only, so two rows whose verdicts live under `docs/results/` are listed as well.
All seven are reported, none fails the check, and none is a defect this pass introduced into the
data.
