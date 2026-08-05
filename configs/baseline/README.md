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
exercise this study's own arms/policies over the frozen core, not a third-party system. Each
composes (disjoint keys) with the existing `configs/{model,dataset,experiment}/*.json` fragments
and drives an end-to-end `core.driver.run_experiment` call; see `tests/unit/test_driver.py` and
`tests/unit/test_config_composition.py`.
