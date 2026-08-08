# Probe prompt templates (P0.C)

Frozen prompt templates for the sampled reproduction probes
(`docs/readiness/2026-08-07-r1-replan-reproduction-plan.md`, R1–R5). Each
`.txt` file is a byte-exact template; `{placeholders}` are filled at runtime
with logged values. `manifest.json` records the SHA-256 of every template —
an ExecutionPlan's protocol hash binds to the manifest entry it uses. Any
template edit requires a new file (never edit in place after a probe has
run) and a manifest regeneration via
`python scripts/build_probe_manifest.py`.

Decode discipline: scoring arms run greedy (temperature 0, fixed seed where
the server honors one); n-best/self-consistency arms (R7, conditional) will
add their own templates + sampling spec when designed.

Fidelity caveat (recorded in the plan): Audio2Tool's own prompts are
unreleased; R1 templates are our reconstruction from the paper's protocol
description. If their release later shows different prompts, R1 re-runs
under the released ones with a new manifest entry.

Sample binding (owner alignment 2026-08-07): `manifest.json` also carries a
`samples` section binding each probe to its frozen sample receipt under
`docs/receipts/probe-samples/` — the split-identity hash is recomputed from
the receipt's items at manifest build and any mismatch fails closed. Each
carrier is sampled exactly once (`scripts/build_probe_samples.py`, seeded,
order-independent); all later experiments on a carrier resolve their items
through this binding, never through a fresh draw.
