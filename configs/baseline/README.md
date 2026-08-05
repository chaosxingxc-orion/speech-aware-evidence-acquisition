# Baseline configurations

The mandatory baseline set is frozen in the owner execution contract (umbrella
`wiki/experiments/speech-aware-evidence-acquisition/2026-08-04-owner-speech-domain-scope-and-identity-contract.md`):
ConEC context line (first reproduction target), RECOVER 1-Best ladder (mandatory contrast arm),
Siskos entity-resolution line, FlexCTC/TurboBias NeMo biasing group.

No runnable *external prior-work* baseline config exists yet **by design**: exact runnable
revisions are frozen by a dated contract amendment before the first reproduction run (R1 step
zero). A baseline failing to reach readiness reports `INCONCLUSIVE_BASELINE_NOT_READY`; silently
substituting a weaker opponent is forbidden. Each such baseline lands here as `<name>.json` (the
deterministic four-fragment config composer, `core.config.compose`, reads JSON only — see
`docs/engineering.md`) with its pinned revision when frozen.

This directory also carries this study's own **engineering controls** (owner contract, distinct
from the four external prior-work baselines above): `bare-core.json`, `fixed-legal-context.json`,
`fixed-retrieval.json` (the three named engineering controls) and `mismatched-evidence.json` (the
random/mismatched-evidence negative control, layered on `fixed-legal-context` via
`evidence_mismatch: true`). These are runnable today — no external revision to pin, since they
exercise this study's own arms/policies over the frozen core, not a third-party system — **but
only when paired with a dataset fragment whose carrier the baseline's `evidence_source` can
actually serve.** `evidence_source: "conec-contexts"` (`core/evidence.py::_conec_contexts`) is
`earnings21-original`-scoped in R0: it hardcodes an `earnings21/contexts/<sample_id>.txt` relpath
regardless of which carrier a run names. `fixed-legal-context.json`, `fixed-retrieval.json` and
`mismatched-evidence.json` therefore must compose with a dataset fragment whose
`carrier_lock_key` is `earnings21-original` — use `configs/dataset/earnings21-discovery.json`.
Pairing any of the three with `configs/dataset/earnings22-dev-subset10.json` instead composes
without error (keys are still disjoint) but the resulting run raises `EvidenceError: conec context
missing` for essentially every sample the first time it actually runs — composing cleanly is not
the same claim as running cleanly, and only the latter is asserted here. `bare-core.json` has no
such constraint (`evidence_source: "none"`) and pairs with either dataset fragment;
`earnings22-dev-subset10.json` is its documented pairing. Each baseline also names its own
`scorers` list (`asr-wer`, `cost` today — see `core/scorers.py` and
`docs/owner-decisions-pending.md` for why no entity/QA scorer is registered yet); a config that
omits `scorers` composes fine but produces a run manifest `core.scorers.score_bundle` will refuse
to score at all ("no configured scorers to run").

Each composes (disjoint keys) with the existing `configs/{model,dataset,experiment}/*.json`
fragments and drives an end-to-end `core.driver.run_experiment` call using the REAL, on-disk
fragment files (not hand-retyped values) — including at least one test per evidence-bearing
baseline that composes the full real four-fragment set with `earnings21-discovery.json` and one
proving a real composed config's manifest carries a non-empty `scorers` list that
`core.scorers.score_bundle` runs end to end; see `tests/unit/test_driver.py` and
`tests/unit/test_config_composition.py`.
