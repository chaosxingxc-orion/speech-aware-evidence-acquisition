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

(no rows yet — a model touch requires E0 closure + runtime receipt + a validated `ExecutionPlan`
whose `run/experiment id` is pre-registered above, per the consolidated execution contract)
