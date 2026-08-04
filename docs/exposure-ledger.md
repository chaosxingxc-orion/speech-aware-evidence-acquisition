# Exposure ledger

Every model or tool touch (including a single-sample smoke) gets a row **before results are read**.
Exposure claims elsewhere must carry four fields: scope, date, counts, inherited exposure.

Field semantics (consolidated contract §6/§7; umbrella 续92/续93):

- `execution profile` — one of `model-free-check` / `baseline-reproduction` /
  `bounded-discovery-probe`; paper-scale profiles never appear in this ledger.
- `split role` — `discovery` or `dev`. `confirmatory` rows require Stage-3 paper authority
  (`OWNER_GO_AND_PAPER_EXECUTION_CONTRACT`) or a dated owner allowance and do not occur in Stage-2.
- `split identity hash` — SHA-256 over the exact sample-identity list this touch may read.
- `consumed` — `yes` only when confirmatory results were read; **irreversible once `yes`**;
  model-free and discovery/dev rows write `no`.
- `inherited exposure` — scoped statement of prior exposure carried into this touch;
  monotonically non-decreasing across rows.

Inherited exposure baseline: program-level prior exposure (W1 probe campaigns on other carriers; no
Earnings21/Earnings22/ConEC model exposure inherited as of 2026-08-03). The carriers' only
processing so far is model-free acquisition/verification (D0).

| date | run/experiment id | execution profile | scope | model/tool | speech carrier + split | split role | split identity hash | consumed | calls | speech audio seconds | inherited exposure | artifacts | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-08-04 | SAEA-E0-CLOSURE-2026-08-04 | model-free-check | E0 D1–D4 closure + runtime receipt + gate dry-run: identity/byte enumeration of the three core carriers; ten-sample e22 subset10 provenance trace; GGUF + llama.cpp build/bin hashing; no audio decoded, no annotation content parsed into artifacts, no model loaded | none beyond local tooling (filesystem hashing; contract negative controls; local `git` metadata; `llama-server --version` build-hash query — no model file passed) | earnings21-original + earnings22-original + conec, identity layers; e22 subset10 (dev) | dev | 99a896359a504f463a1657281aa71f4a28a51161c804422d8e2f192b0486ad3e | no | 0 | 0 | W1 probe campaigns on other carriers; zero model exposure on the three core carriers | docs/receipts/e0-closure.json + docs/receipts/artifacts/ + docs/receipts/runtime.json | model-free; split identity hash = SHA-256 over the 213 carrier-prefixed sample IDs enumerated (44 e21 + 125 e22 + 44 conec); scope amended same-day after round-1 adversarial review to name the runtime receipt and tooling explicitly (git history preserves the pre-amendment text) |

(a model touch additionally requires the runtime receipt and a validated `ExecutionPlan`
whose `run/experiment id` is pre-registered above, per the consolidated execution contract)
