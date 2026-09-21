# Cell B9a: acquisition on demand, kind (a) knowledge-requery (item E18), on the locked default-plan base: preregistration

Registered 2026-09-21 by the coordinator (Fable 5.1), by script from the registered cell PLAN package (decision 58), before any
contact. Development numbers only (owner decision 28).

## 1. Why this cell exists

Owner decision 43 requires every carrier to instantiate all six nodes and forbids a registered absence; decision 44 built the
Acquisition node (item E18) as everyday inference and named its first cell B9a, kind (a) knowledge-requery, on the best
not-HARMFUL base; decision 78 makes B9a a Stage-2 seal flight. The base is the locked default plan (cell PLAN).

## 2. The cell

| item | value |
| --- | --- |
| base | the sealed PLAN arm `SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1` (the locked default plan; official numbers pending its read) |
| factor | `native_episode.acquisition` = {"policy": "saea-acquire-knowledge-requery-v1", "budget": {"max_acquisitions_per_row": 1, "contact_budget": 0}} with `roles.acquisition` = {"phase_id": "acquisition", "max_iterations": 0, "kinds": ["knowledge-requery"]} (one module, E18) |
| not factors | E13 / E20 / E22 declarations |
| unchanged | roster (TRAIN Fold A 1,080), geometry (np4 x 24,576), session, template, stores, k = 20, no phase_tools, ceiling 11 |
| contacts per row | 4 (at most 11 with a revision; kind (a) costs none) |
| comparator | `SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1`, never re-flown |
| margins | the plan's own null from `SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-REPLICATE-V1`; decision-38 fallback 1.2350 / 1.2212 only if PLANr has not read, stated |
| smoke | four engineering rows, structural acceptance (loader accepts the pair; ACQUIRE advertised; receipts if routed) |
| runs | `SAEA-SLURP-NATIVE-PLAN-ACQUISITION-B9A-V1` / `-FIT-V1`; smoke `SAEA-SLURP-NATIVE-PLAN-ACQUISITION-B9A-SMOKE-4-V1` / `-FIT-V1` |

## 3. Decision rule (fixed here)

{
  "comparator": "the sealed PLAN arm SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1, and nothing else, for every gating clause; margins the plan's own null (PLANr)",
  "NEUTRAL": "BOTH guards non-inferior at the plan's own null: the CI95 LOWER bound of the paired official pooled SLU-F1 delta (B9a minus PLAN) exceeds -h_SLU AND the CI95 LOWER bound of the paired intent delta exceeds -h_intent; the Acquisition node is then instantiated in the base as it flew (kind (a), budget 1 / 0) and the base-lock v3 document records it.",
  "ADMITTED": "NEUTRAL and, in addition, the pooled SLU CI95 lower bound above zero: reported as a gain.",
  "HARMFUL": "owner decision 25's form: a MEASURED LOSS on either guard -- a point estimate below -h or a CI95 UPPER bound below zero. Then the owner decides between locking the node at its OFF null arm (which decision 43 forbids as a registered absence) and a re-scoped kind; nothing is automatic.",
  "acquisition_diagnostic": "rows routed to ACQUIRE, items acquired, saves / harms on the acquired rows: reported whatever the verdict; a zero-acquisition flight (the Planner never routes ACQUIRE) is a finding about the Planner, not a NEUTRAL by default -- it is stated as such.",
  "efficiency_is_reported_regardless": "every efficiency deliverable is reported whatever the verdict",
  "scenario_diagnostic": "the decision-17 net-harmed flag per scenario (five or more) is reported; a breach is a diagnostic beside the verdict, never a gate"
}

## 4. Efficiency read (mandatory) and the frontier row

As cell PLAN's: prefilled tokens per row (server.log join), GPU hours per 1,080 rows, contacts per minute, projected
13,078-row read hours, the frontier row (decision 75) beside PLAN and the tool-free base.

## 5. Budgets, failure rule, what is not claimed

Ceilings as cell PLAN's (11,880 generation calls run-cumulative, 47,520 FIT endpoints, 33,930 repeated speech seconds, 12.0 GPU
hours, native task-contract calls 0, one official complete score). First failure stops and preserves; one root-diagnosed
recovery re-registration at most. No claim about kinds (b) / (c), no test-split, Fold B or DEV-1000 claim.
