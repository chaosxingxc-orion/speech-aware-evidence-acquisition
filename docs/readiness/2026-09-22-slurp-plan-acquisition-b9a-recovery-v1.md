# Cell B9a-rec: the one root-diagnosed recovery of cell B9a (the Acquisition node, kind (a) knowledge-requery, item E18) after item E36: registered before contact

Registered 2026-09-22 by the coordinator (Fable 5.1), by script from the registered cell B9a package (decision 58), before
any contact. This note is the addendum to
[`2026-09-21-slurp-plan-acquisition-b9a-v1-preregistration.md`](2026-09-21-slurp-plan-acquisition-b9a-v1-preregistration.md),
whose question, factor, metrics, resampling, decision rule and caps stand unchanged; it allows at most one root-diagnosed
recovery re-registration per run, and this is it. Development numbers only (decisions 28, 86).

## 1. What happened

Run `SAEA-SLURP-NATIVE-PLAN-ACQUISITION-B9A-V1`, attempt `attempt-slurp-native-plan-acquisition-b9a-train-fold-a-generation-v1`, flight commit `a2fe1ce3`, flown by the SAEA-Batch-Driver scheduled task,
**ABORTED 2026-09-21T20:16Z** on the first row whose Planner routed `ACQUIRE`. Verbatim from the attempt record:

```
generation failed during run_phases or seal: NativeEpisodeError: native episode node failed: [100054] component 'acquisition_0' execute 'invoke' error, reason='the knowledge re-query acquisition requires an acquisition_requery binding'
```

The mechanism in one sentence: the Acquisition node's kind (a) callable is read from the run binding
(`acquisition_requery`); the E18 / E32 proofs supplied it through the test harness, and the production `FlightRuntime`
never built it, so the first live ACQUIRE route died. The four-row smoke could not reach the path (no smoke row routed
ACQUIRE).

## 2. What was spent and what is preserved

| item | value |
| --- | --- |
| attempt state | `ABORTED` |
| generation calls / repeated speech seconds | 327 / 712.342 (charged run-cumulatively to `SAEA-SLURP-NATIVE-PLAN-ACQUISITION-B9A-V1`) |
| trace | `runs/SAEA-SLURP-NATIVE-PLAN-ACQUISITION-B9A-V1/attempt-slurp-native-plan-acquisition-b9a-train-fold-a-generation-v1/SAEA-SLURP-NATIVE-PLAN-ACQUISITION-B9A-V1.trace.jsonl`, sha256 `85f082a72b85d740cf48b2bfb7d2e327ffda495da883f608b2361862f37d62b8` (327 MODEL_REQUEST records) |
| flight lock | reconciled with quiescence receipt `coordination/slurp-plan-acquisition-b9a-v1/flight-lock-reconciliation-20260922T000128Z.json` |
| score | none; no partial quality read was taken or is permitted |

## 3. The fix and its proofs

Item E36, merged `fef4341e`: `FlightRuntime._acquisition_requery_binding(native_config, supply_for_phase, snapshot)` builds the
kind (a) callable from the SAME phase supply the Solver uses and the released stores' composite snapshot (drops ids already
visible, restricts by the Reviewer / Planner state tokens, returns `rails.acquisition.AcquiredItem` triples; zero contacts).
Proofs: `tests/unit/test_e36_acquisition_requery_binding.py` (14 tests: None on unarmed / wrong-kind / no-supply arms, the
bare-snapshot and named-store paths, filters, excludes, determinism, empty result, scope refusal, and two wire proofs that
re-run the real E32 ACQUIRE -> ACCEPT episode with the production binding); the E18 byte-pinned "unarmed request bytes
unchanged" test still passes; gates green on the merged main (206 tests in the touched areas).

## 4. Why nothing else changes

Runner-binding defect only. Same roster (TRAIN Fold A 1,080, split identity
`61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6`), same fragment on every key (the proof test shows the
recovery baseline equal to the B9a baseline outside its bookkeeping), same policy `phase-native-candidates-review-revise-acquire-v1`
(ceiling 11), same stores and pins, same geometry and session, same caps (11,880 calls run-cumulative, 33,930 repeated speech
seconds, 12.0 GPU hours, one official complete score), same comparator (the sealed PLAN arm) -- now at the plan's own null
from PLANr (h_SLU 1.2485, h_intent 0.9943). The E10 resume form does not apply: the code changed. The whole roster flies
from row one under new ids: `SAEA-SLURP-NATIVE-PLAN-ACQUISITION-B9A-RECOVERY-V1` / `-FIT-V1`, smoke `SAEA-SLURP-NATIVE-PLAN-ACQUISITION-B9A-RECOVERY-SMOKE-4-V1` / `-FIT-V1`.

## 5. What is not claimed

Nothing about kinds (b) / (c); no test-split, Fold B or DEV read; the aborted attempt's rows carry no quality information
and are not reused. A second failure closes cell B9a (no third registration).
