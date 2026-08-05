# Owner decisions pending

Explicit scope items this repository's implementers cannot resolve on their own authority.
Per-item disposition (accept, defer with a dated amendment, or reject) is an owner action; this
file only records what is open and why. See design spec §6
(`docs/superpowers/specs/2026-08-05-saea-r0-repair-trust-boundary-design.md`, umbrella) for the
governing framing.

## 1. Entity/QA scorer adapters (R0 repair T8, invariant I8 partial)

**Status:** not registered. `core/scorers.py` registers `asr-wer` and `cost` only.
`scoring/entity.py` (`score_entities`) and `scoring/qa.py` (`qa_exact_match`, `qa_token_f1`) remain
frozen, hash-pinned pure functions with no adapter wiring them to a reference layer through the
`SCORERS` registry.

**Why no adapter was written (do not fake one):**

- **Entity.** A reference layer *exists on disk* for `earnings21-original` (and the ConEC
  Earnings21 side): `transcripts/wer_tags/<sample_id>.wer_tag.json` plus the `.nlp` file's own
  `wer_tags` column (inspected locally under `SPEECHRL_DATA_DIR`; no content committed by this
  task). Freezing an adapter over it requires resolving three format decisions this task has no
  authority to make unilaterally:
  1. the `.nlp` file's `wer_tags` column is **Python-repr list syntax** (e.g. `['0', '1', '6']`),
     not JSON — parsing it needs a decision (regex vs. `ast.literal_eval`) that becomes part of
     the frozen scoring contract, not an implementation detail;
  2. an entity ID can label **multiple, not-necessarily-contiguous** tokens (README:
     "Entities can be comprised of single and multiple tokens... only one entity can be labeled
     with any given ID") — grouping token spans into one entity mention needs a specified,
     hash-pinned algorithm, exactly the kind of decision E0 D3 froze for WER/entity/QA
     normalization and that a later, unreviewed choice should not quietly make;
  3. `scoring.entity.score_entities(expected, predicted)` takes flat entity **strings**; whether
     the expected-side string is the entity mention text, the `entity_type` label, or a
     `"{type}:{text}"` composite is itself a scoring-contract decision;
  4. only `earnings21-original` (and ConEC's Earnings21 side) carries this layer at all —
     `earnings22-original`'s `data/identity.py` layers have no `wer_tags` entry, so any adapter
     would start carrier-scoped, another explicit-scope decision.

  This is not a new finding: `.superpowers/sdd/2026-08-05-speech-aware-evidence-acquisition-r0-vertical-slice/task-14-brief.md`
  already named "entity/QA reference extraction from `wer_tags`/ConEC annotations" as a known,
  intentional deferral pending a **readiness memo that pins the format** — that memo was never
  written. The R0 repair design spec (`docs/superpowers/specs/2026-08-05-saea-r0-repair-trust-boundary-design.md`
  §6.1, umbrella) independently lists "entity/QA scorer adapter 是否属于 R0 交付（其参考层格式尚未冻结）"
  as an owner-disposition item, not an implementer one.
- **QA.** No spoken-QA reference layer is wired into this study at all. `data/identity.py` defines
  no QA layer for any carrier. `slue-sqa-5` and `contextasr-bench` (the secondary carriers named in
  `docs/engineering.md`) do exist as raw acquired bytes under `SPEECHRL_DATA_DIR/datasets/` (Parquet
  files for `slue-sqa-5`, inspected locally for file presence only), but neither has a carrier
  loader, an identity layer, nor any per-sample reference format ever specified in this repository.
  Registering a QA adapter would mean inventing a new carrier's reference contract from scratch,
  which is new-experiment-shaped work, not a scorer-seam wiring task.

**What was inspected (format discovery only, per task-8 brief; no dataset content committed):**
`transcripts/wer_tags/*.wer_tag.json` structure and one sample's parsed keys/values under
`earnings21-original`; the `.nlp` file header and `wer_tags`/`tags` column values for the same
sample; `datasets/earnings21-22/earnings21/README.md`'s own file-format documentation (entity ID
semantics, multi-token entities); `datasets/conec/README.md`'s directory layout; the presence and
top-level layout of `datasets/slue-sqa-5/` and `datasets/contextasr-bench/`.

**Requested disposition:** either (a) commission a readiness memo that pins the entity reference
format (parse rule for the `wer_tags` column, span-grouping rule, and the string a scorer compares)
so a later task can implement `core.scorers` adapters against a frozen contract, explicitly scoped
to `earnings21-original` first; or (b) accept that entity/QA scoring is out of scope for R0 and
defer it to R1 or later, recorded as a deviation rather than silently absent.

## 2. GPU/CPU/peak-VRAM cost accounting (design spec §6.2, I8)

Restated here for visibility, not newly raised by T8: `core.model.FrozenCoreAdapter.cost_summary()`
reports `calls_used`, `audio_seconds_used`, `latency_seconds_total`, `prompt_tokens_total`,
`completion_tokens_total` — no measured GPU-hours, CPU-hours, or peak VRAM. The design spec commits
to *measured sampling*, not deferral, but notes that if sampling is unavailable on this machine the
owner must accept a deviation. T8 adds a `cost` scorer over exactly this block (see
`core/scorers.py::score_cost_outputs`) but does not change what the adapter measures — that remains
open per the design spec, not resolved by this task.

## 3. R0.3 `SAEA-E-001` execution authorization

Restated for visibility (design spec §6.3): R0.3 smoke and R1 do not start before the fresh
independent re-review passes and the owner has acted on items 1–2 above.
