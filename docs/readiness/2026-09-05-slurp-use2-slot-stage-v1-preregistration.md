# Cells KC-S1a and KC-S1b: a separate slot stage conditioned on the sealed intent, and on the per-intent TRAIN slot schema — v1 preregistration (REGISTERED)

Status: drafted 2026-09-05 as step 4 of the owner-confirmed mechanism order and **completed and registered
the same day** as cells **KC-S1a** and **KC-S1b** of
`docs/readiness/2026-09-05-three-dimension-experiment-program.md` section 4a. The draft's cell names
(USE-2a/USE-2b/USE-2c) are retained below only where they name *later* cells; the two cells this document
registers are the program's KC-S1a and KC-S1b, and their machine-readable contracts are
`configs/experiment/slurp-slot-stage-kc-s1a-v1.json` and `configs/experiment/slurp-slot-stage-kc-s1b-v1.json`.

Registered before any model contact. Exposure rows: `SAEA-SLURP-KC-S1-PROMPT-FIT-V1`,
`SAEA-SLURP-KC-S1-SMOKE-4-V1`, `SAEA-SLURP-KC-S1A-SLOTS-DEV1000-V1`,
`SAEA-SLURP-KC-S1B-SLOTS-SCHEMA-DEV1000-V1`.

## 1. Question and hypothesis

Under the official `evaluate.py` the closed-list direct baseline reaches intent 71.40 but SLU-F1 35.80, and the
slot layer is recall-limited: 547 predicted entity mentions, precision 29.98, recall 17.26 (M0: 718, 25.49, 19.26).
A single JSON request asking for scenario, action and every slot at once under-produces slots; the only published
prompt-only result (ChatGPT over transcripts) shows the same shape (intent 79, slot F1 12-13). The locked BLEND
cell raised SLU-F1 to 41.69 by supplying slot knowledge as facets.

Hypothesis H1: splitting the task so that slots are extracted in a dedicated contact, conditioned on the predicted
intent and on the slot schema that intent has in TRAIN (which entity types occur with it, with example fillers and
the verbatim-lowercase filler convention), raises SLU-F1 without changing intent accuracy. This is a USE mechanism
(how the core is asked to use knowledge) with an ORG component (the per-intent schema organized from TRAIN); the
program files it under knowledge construction because the schema is the artifact under test.

## 2. Design: two cells, one factor each

The intent stays EXACTLY the sealed closed-list baseline's prediction for each row — no re-run, no second intent
contact. The sealed bytes are both the comparator and the input.

**KC-S1a (contact-count control).** One new contact per row: audio, the closed-list system message unchanged, and
a CONTROL turn (`configs/probes/slurp_phase_slots.txt`) asking for the entity list ALONE, with the sealed
closed-list response for that row appended under the fixed `Prior phase response` framing. Types come from the
55-type closed inventory the system message already carries; **no per-intent schema**. Without this cell, any gain
KC-S1b shows could be the extra contact rather than the schema.

**KC-S1b (the mechanism).** KC-S1a plus the per-intent TRAIN slot schema block of the intent that sealed response
names — the entity types holding at least 2 % of that intent's TRAIN slot mentions, each with its share and up to
five lower-case example fillers (`data.slurp.render_slurp_slot_schema_for_state_detail`, prerequisite MF-3,
receipt `docs/receipts/knowledge/slurp-intent-slot-schema-v1.json`). A row whose sealed response does not parse or
names a (scenario, action) pair TRAIN never carries falls back to the FULL 60-intent schema; those rows are
counted and named in the receipt. The schema is built from TRAIN only (`load_slurp_intent_slot_schema` has no
split parameter and can reach no devel or test file) and is rendered by a registered fill; the request carries no
gold of the row.

**The single factor, as bytes.** The block is appended AFTER the sealed state, so KC-S1b's contact instruction is
KC-S1a's contact instruction plus a pure per-sample suffix. The prompt-fit receipt asserts that on all 1,000 rows
before takeoff, and the two cells' system messages are asserted byte-identical.

Cells reserved for later, each one factor: USE-2b adds the model's own transcript (an OBS contact) as the
extraction source; USE-2c conditions on the top-2 intents' union schema to absorb intent errors.

## 3. Population, harness, scoring

DEV-1000 exactly as the closed-list baseline flew it (same runtime view, same split identity hash
`8580d199…3c84`; the DEV-500 / NEW500 partition preserved). No new exposure: these are the rows the sealed
2026-08-25 lock campaign and the 2026-09-05 closed-list baseline already read.

`core.flight.FlightRuntime` with the roster-bound, label-free SLURP adapter of
`scripts/flights/run_slurp_closed_list_cell.py`, the one-phase program `configs/policy/phase-slots-given-intent-v1.json`
through `rails.phase_runner.run_program`, phase material built from the baseline fragment alone
(`rails.phase_material`; no launcher-written material), sealed as a `core.bundle` run manifest declaring
`slurp-slu-official`, `slurp-slu`, `cost`, and scored once per manifest through `core.scoring_batch`.
N-predicted and skipped rows reported. Model usage is the closed-list baseline's: Q4_K_M, featcache build
04ccc72a, mmproj-free over the DEV-1000 promotion receipt's packets, greedy temperature 0 seed 20260803
max_tokens 64.

**The response shape, and why the primary metric needs no projection.** The slot contact returns
`{"entities": [{"type": …, "filler": …}, …]}`. `reproduction.slurp_scoring.parse_slu_response` — the same
fail-closed parser the official scorer's prediction side uses — accepts an object whose scenario and action are
absent, and the official `evaluate.py` computes `entities`, `entities (distance word)`, `entities (distance
char)` and **SLU F1** from the entity lists alone (`slu_f1` is fed only the two distance metrics; the intent never
enters it). The sealed manifest's entity blocks, including the primary SLU-F1, are therefore real numbers from
`core.scoring_batch` over the complete manifest with no projection anywhere in the primary metric's path. The
scenario/action/intent columns of that same scoring job are meaningless by construction and are never reported as
a result.

**The full-row table.** For the complete official table the final row per sample is assembled post-seal by a
MODEL-FREE projection: `{"scenario", "action"}` copied from the sealed closed-list row and `"entities"` from this
cell's sealed row, joined on `sample_id`, with the source manifest sha256, the source outputs sha256 and the
projection sha256 recorded, and with intent identity against the closed-list arm asserted row by row. This is the
same device the 2026-09-04 alignment audit used for the August SLURP flights. The projection is scored by the SAME
registered `slurp-slu-official` scorer over the same complete 1,000-row roster, in one call, never sharded; its
entity columns must equal the sealed manifest's exactly, which is a free consistency check on the join.

## 4. Budget

Per cell: 1,000 calls + 8 canaries planned, registered ceiling 1,050; speech seconds 2,884.7937 in one pass,
ceiling 3,000; GPU hours planned 0.3, ceiling 1.0; paid API spend 0. Plan cells are run-cumulative across every
attempt of a run id; at most one recovery re-registration per cell.

Two run ids, one per cell, each with its own experiment fragment, plan, exposure row and recovery allowance —
`core.attempts` keys on `(run_id, attempt_id)` and a shared run id would meter both cells against one budget and
spend the single recovery allowance on whichever cell failed first. The 4-row smoke uses ONE run id for both
cells because it is a wiring proof whose numbers are never read.

Before takeoff, in order: this preregistration; the four exposure rows; the exact prompt fit and material audit
(`scripts/slurp_kc_s1_prompt_fit.py`, zero generated tokens); a contact-free wire check on a clean committed
tree; the 4-row smoke; then the two flights.

## 5. Analysis and decision (fixed before takeoff)

Paired against the sealed closed-list baseline on the same 1,000 rows and separately on the unexposed NEW500
(`analysis.paired.paired_contrast`, 10,000 replicates stratified by gold scenario, seed 20260903, CI90, exact
sign test): SLU-F1 (primary; per-sample slot F1 paired the way the closed-list verdict paired it, with the
official corpus SLU-F1 as the aggregate anchor), entity strict precision / recall / F1, Word-F1, Char-F1, per
entity type and per scenario; intent accuracy identical by construction and asserted; N-predicted and skipped
rows from `evaluate.py`; beside the locked BLEND arm (41.69) and the published brackets (weakest trained pipeline
64.02; prompt-only ChatGPT slot F1 12–13). Both weightings (natural mixture and equal scenario) and the gain per
extra contact are reported.

- **ADMITTED** — KC-S1b only: its SLU-F1 paired CI90 lower bound is above 0 against the closed-list baseline on
  NEW500 **and** the (KC-S1b − KC-S1a) lower bound is above 0 on the same population. The schema, not the contact,
  has to be the lever. USE-2 then becomes the SLURP slot mechanism the next cells (USE-2b transcript, USE-2c
  top-2) and the TRAIN prompt rollouts build on.
- **NULL** — either interval includes 0: the per-type table names which types did not move, and USE-2b (the
  self-transcript source) is registered next as the single factor.
- **HARMFUL** — an upper bound below 0: dropped with the form/content attribution recorded, and the slot branch
  ends.

KC-S1a has no gate of its own; it is the contact-count reference and carries KC-S1b's second condition.

## 6. Deviations decided before takeoff, with their reasons

1. **The bound knowledge snapshot is the TRAIN snapshot without its `content` dimension.** Every phase program
   binds a frozen snapshot even when all its phases declare `knowledge: "none"`, because
   `rails.runner.run_speech_native_agent_loop` requires one; the snapshot is what the leakage rule
   `_assert_agent_control_excludes_knowledge_payloads` is enforced against. The default `size-full` snapshot's
   `content` dimension carries one facet per TRAIN utterance whose representation is that utterance's raw text,
   and SLURP has one- and two-word utterances — `calendar`, `shopping`, `how much`. The rule's raw substring test
   over payloads of 8 characters or more therefore refuses **78 of the 1,000 sealed closed-list responses** (58 of
   them for the word `calendar`) and **all 60 per-intent schema blocks** (for `how much`, which occurs in the
   schema header). This is a defect in the enabler chain, not in these cells: with `size-full` bound, no SLURP
   phase cell can send SLURP's own scenario names, which blocks KC-S1a/b, KU-S1c and KU-S3 alike. The fix taken
   here is the one `data.slurp.render_slurp_intent_slot_schema` itself prescribes — exclude the content
   dimension from the bound snapshot, not trim the schema. `KnowledgeBuildSpec.validate` explicitly allows any
   dimension set containing `content` **or** `label`; `scripts/build_knowledge_snapshot.py --dimensions
   label,speaker,prior` builds it (receipt `docs/receipts/knowledge/slurp-kb-size-full-label-prior-speaker.json`,
   snapshot content hash `07f94807…fa65`). The leakage rule stays at full strength over 11,863 protected payloads
   — every one of the 11,514 exemplar values and every label, speaker and prior facet — and this is the
   strictest available snapshot that these cells can send at all: measured against it, zero hits in the full
   schema, zero in all sixty per-intent blocks, zero in all 1,000 sealed responses. Reported to the owner as a
   program-level item: KU-S1, which actually consumes facets, cannot take this way out and needs its own ruling.
2. **Serving geometry `-np 4 -c 65536` instead of the baseline's `-np 8`.** Per-slot context, not throughput.
   KC-S1b's fallback rows carry the full 60-intent schema (26,720 characters) on top of a 7,583-character system
   message and do not fit an 8,192-token slot; at `-np 4` the same server context divides into 16,384-token
   slots. Request bytes, decoding parameters and packets are unchanged, and both cells fly the same geometry so
   the (S1b − S1a) contrast is geometry-matched. Concurrency is not a request-content variable (closed-list
   verdict, deviation 2). The declaration lives in the baseline fragments (`serving_slots` /
   `serving_slot_tokens`), so it is inside the config hash.
3. **`FlightRuntime`'s own pre-flight prompt budget cannot see this cell's prompt.**
   `_phase_prompt_payloads` renders one representative request per phase with a fixed 256-character pad in place
   of the predecessor state and applies no `state_fill`, and `rails.context_budget`'s registered
   `PER_SLOT_LIMIT_TOKENS` is 32,768 rather than the physical per-slot context. Its ALLOW is therefore not
   evidence for these cells, and `scripts/slurp_kc_s1_prompt_fit.py` measures every one of the 2,000 real
   envelopes exactly, through the resident server's own `/apply-template` + `/tokenize`, against
   `-c / -np`. Reported, not patched: `core/flight/runtime.py` is owned by another track this wave.
4. **One new seam in `rails/phase_material.py`.** A phase may declare `state_fill: "<registered name>"`, and
   `build_material_for_phase` appends that fill's per-sample text after the predecessor state. It is resolved
   through `PHASE_STATE_FILLS` from config alone, so `core/flight/runtime.py` needed no change; unit tests in
   `tests/unit/test_phase_material.py` pin the append order, the pure-suffix property, the registry resolution
   and every refusal.

## 7. What this preregistration does not authorize

No test contact; no re-run of the intent stage; no retrieval; no second LLM; no change to the closed-list direct
baseline; no prompt search on DEV (rollouts are TRAIN-only and are a separate cell); at most one recovery
re-registration per cell; no superiority or Stage-3 claim.
