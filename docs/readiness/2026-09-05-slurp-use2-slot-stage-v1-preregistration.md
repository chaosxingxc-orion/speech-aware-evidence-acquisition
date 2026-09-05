# SLURP-USE-2: a separate slot stage conditioned on the intent and the per-intent TRAIN slot schema, v1 preregistration (DRAFT, not registered)

Status: drafted 2026-09-05 as step 4 of the owner-confirmed mechanism order. Not registered until the owner's GO;
ordering relative to A2T-ORG-2 is the owner's call.

## 1. Question and hypothesis

Under the official `evaluate.py` the closed-list direct baseline reaches intent 71.40 but SLU-F1 35.80, and the
slot layer is recall-limited: 547 predicted entity mentions, precision 29.98, recall 17.26 (M0: 718, 25.49, 19.26).
A single JSON request asking for scenario, action and every slot at once under-produces slots; the only published
prompt-only result (ChatGPT over transcripts) shows the same shape (intent 79, slot F1 12-13). The locked BLEND
cell raised SLU-F1 to 41.69 by supplying slot knowledge as facets.

Hypothesis H1: splitting the task so that slots are extracted in a dedicated contact, conditioned on the predicted
intent and on the slot schema that intent has in TRAIN (which entity types occur with it, with example fillers and
the verbatim-lowercase filler convention), raises SLU-F1 without changing intent accuracy. This is a USE mechanism
(how the core is asked to use knowledge) with an ORG component (the per-intent schema organized from TRAIN).

## 2. Design: one factor per cell

Cell USE-2a (this preregistration): the intent stays EXACTLY the sealed closed-list baseline's prediction for each
row (no re-run, no second intent contact; sealed bytes are the comparator and the input). One new contact per
row: audio + the closed-list instruction's entity conventions + "the intent of this request is
`{scenario}_{action}`" + the per-intent schema (entity types with TRAIN frequency at least 2 % for that intent,
each with up to 5 example fillers from TRAIN, lowercase), asking for ONLY the entities as a JSON list of
`{"type", "filler"}` with fillers copied verbatim from the speech, lowercase. Final row = sealed intent + new
entities, scored with the official script. Cells reserved for later, each one factor: USE-2b adds the model's own
transcript (an OBS contact) as the extraction source; USE-2c conditions on the top-2 intents' union schema to
absorb intent errors.

The schema is built from TRAIN only (`slurp_real` train split; never devel or test), decontaminated by identity
against the DEV ladder as the KB build was; its receipt records the per-intent tables and their hashes. It is
rendered by a registered instruction fill; the request carries no gold of the row.

## 3. Population, harness, scoring

DEV-1000 exactly as the closed-list baseline flew it (same receipt, same split identity hash; the DEV-500 /
NEW500 partition preserved). `core.flight.FlightRuntime` with the SLURP adapter, the shared controller's phase
program extended by one phase (slot stage) in `configs/policy/`, sealed as a `core.bundle` manifest declaring
`slurp-slu-official`, `slurp-slu`, `cost`, scored once through `core.scoring_batch`; N-predicted and skipped rows
reported. Model usage unchanged (Q4_K_M, build 04ccc72a, greedy, the closed-list baseline's serving profile).

## 4. Budget

1,000 calls + 8 canaries planned (ceiling 1,050), speech seconds 2,884.79 (ceiling 3,000), GPU hours 0.3
(ceiling 1.0), paid API spend 0. 4-row dry run through the extended phase program first.

## 5. Analysis and decision (fixed before takeoff)

Paired against the sealed closed-list baseline on the same 1,000 rows and separately on the unexposed 500
(`analysis.paired`, 10,000 replicates stratified by scenario, seed 20260903, CI90): SLU-F1, Word-F1, Char-F1,
entity strict F1, precision and recall, per entity type and per scenario; intent accuracy identical by
construction (asserted). Also beside the locked BLEND arm (41.69) and the published brackets (weakest trained
pipeline 64.02).

- ADMITTED: SLU-F1 paired CI90 lower bound above 0 on the unexposed 500. USE-2 becomes the SLURP slot mechanism
  the next cells (USE-2b transcript, USE-2c top-2) and the TRAIN prompt rollouts build on.
- NULL: CI90 includes 0; the per-type table names which types did not move, and USE-2b (transcript) is
  registered next as the single factor.
- HARMFUL: CI90 upper bound below 0; dropped with the reason recorded.

## 6. What this preregistration does not authorize

No test contact; no re-run of the intent stage; no retrieval; no second LLM; no change to the closed-list direct
baseline; no prompt search on DEV (rollouts are TRAIN-only and are a separate cell); at most one recovery
re-registration; no superiority or Stage-3 claim.
