# Baseline configurations

The mandatory baseline set is frozen in the owner execution contract (umbrella
`wiki/experiments/speech-aware-evidence-acquisition/2026-08-04-owner-speech-domain-scope-and-identity-contract.md`):
ConEC context line (first reproduction target), RECOVER 1-Best ladder (mandatory contrast arm),
Siskos entity-resolution line, FlexCTC/TurboBias NeMo biasing group.

No runnable baseline YAML exists yet **by design**: exact runnable revisions are frozen by a dated
contract amendment before the first reproduction run (R1 step zero). A baseline failing to reach
readiness reports `INCONCLUSIVE_BASELINE_NOT_READY`; silently substituting a weaker opponent is
forbidden. Each baseline lands here as `<name>.yaml` with its pinned revision when frozen.
