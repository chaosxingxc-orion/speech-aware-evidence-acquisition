# SLURP legal-label projection, re-locking the closed-list baseline — preregistration (2026-09-06)

Row id: `SAEA-SLURP-MF-LEGAL-LABEL-PROJECTION-RELOCK-V1`. Profile: `model-free-check`.
**Zero model contacts, zero GPU, zero tool, zero embedding, zero network.** Receipts:
`docs/checks/speech-aware-evidence-acquisition/2026-09-06-slurp-legal-label-projection-relock/`.

Authority: the owner ruling of 2026-09-06 that a legal-label projection is a **model-usage
local optimization**, allowed before any mechanism, on a carrier whose direct baseline is
already locked. This registration is written and committed **before any sealed output row of
any arm is read**, and before the projection code exists.

## 0. Why this is registered at all

Two already-published measurements say the same thing from opposite ends.

* The 2026-09-05 closed-list verdict
  (`docs/readiness/2026-09-05-slurp-closed-list-direct-baseline-v1-verdict.md`, section 4):
  the locked direct baseline still emits an **impossible `(scenario, action)` pair on 4.20 %
  of DEV-1000**, down from M0's 32.20 % but not zero. The largest residual classes are
  `locations/query` (10 rows) and `events/query` (8) — the model naming the *action* as the
  scenario for `recommendation_locations` / `recommendation_events`.
* MF-7, the SLURP retrieval-key audit (`wt/mf7`,
  `docs/readiness/2026-09-06-slurp-retrieval-key-audit-v1.md`, section 5.3): the only
  speech-containing query set that cleared its gate did so **not by retrieving anything**
  (echo rate 96.19 %) but because, on the ~37 per 1,000 rows whose draft label lies outside
  the 60 TRAIN intents, the vote fell back to a *legal* label. That note prices the effect at
  **about +1.4 pp intent** and states plainly that "legalisation is a decoding-constraint
  repair available far more cheaply than a retrieval plane".

A label the ontology cannot contain is certainly wrong. Mapping it onto the nearest label the
ontology *can* contain costs no contact, no parameter and no evidence. If that is worth
intent points, they belong to the **baseline**, not to a mechanism — otherwise every later
SLURP cell is measured against a comparator that is leaving free points on the table, and any
mechanism that merely legalises labels will be credited with a gain the prompt/decode side
should already own.

This registration therefore does one thing: it defines the projection, measures it against the
unprojected sealed rows, and either **re-locks** the direct comparator as "closed-list +
projection" or reports the projection and locks nothing.

## 1. The projection rule, stated deterministically

Identity: `slurp-legal-label-projection-v1`.

**The legal inventory.** The 60 `(scenario, action)` pairs of
`data.slurp.load_slurp_ontology(lock, root).actions_by_scenario` — mined from `train.jsonl`
alone (`include_synthetic=False`), the same TRAIN-only inventory the locked baseline's own
prompt suffix renders. 18 legal scenarios; each carries its own legal action list.

**The TRAIN prior.** `P(scenario, action)` is the number of TRAIN utterances carrying the
intent `f"{scenario}_{action}"`, read from
`data.slurp.load_slurp_intent_slot_schema(lock, root).intents[intent].n`. The scenario prior
`P(scenario)` is the sum of that quantity over the scenario's legal actions. TRAIN is
construction data and is readable; no devel or test label enters the rule.

**Edit distance** is Levenshtein over the raw label strings, computed by
`reproduction.slurp_scoring._levenshtein` — the function the char-distance metric already
uses. No normalization, no lower-casing, no tokenization: the labels are already a closed
lower-case vocabulary.

**The rule.** Let `(s0, a0)` be the `scenario` / `action` a row's response parsed to.

1. If the response **did not parse**, it stays unparsed. Nothing is invented, no placeholder
   label is written, and the row is scored exactly as it is scored today.
2. If `s0` or `a0` is **absent** (`None`) — the shape a slot-only arm such as KC-S1a/KC-S1b
   answers with — the row is **untouched**. There is no `scenario_action` to project.
3. If `(s0, a0)` is already one of the 60 legal pairs, the row is **untouched**.
4. Otherwise the row is **projected**:
   * **4a — the scenario is legal.** Keep `s0`. Choose the action `a*` from
     `actions_by_scenario[s0]` minimizing the ordered key
     `(lev(a0, a), -P(s0, a), a)`: smallest edit distance first, then the **larger TRAIN
     prior**, then the alphabetically first name. Emit `(s0, a*)`.
   * **4b — the scenario is illegal.** Choose the scenario `s*` from the 18 legal scenarios
     minimizing `(lev(s0, s), -P(s), s)` under the same three-level key, then choose `a*`
     within `actions_by_scenario[s*]` exactly as in 4a. Emit `(s*, a*)`.

An empty-string scenario or action is a string, not an absence, and is projected under 4a/4b
like any other illegal label; the distance to an empty string is simply the candidate's
length, so the tie-break carries the choice. This is stated so the case is registered rather
than discovered.

**Entities are never touched.** The projection rewrites `scenario` and `action` and nothing
else, so `entities`, both distance blocks and SLU-F1 are structurally unchanged on any arm.
That is an assertion the read makes on every arm, not a hope.

**The official scorer is applied to the projected label, unchanged.** The projection runs
strictly between `reproduction.slurp_scoring.parse_slu_response` (byte-identical, untouched)
and the construction of the official prediction file. The real, unmodified `evaluate.py` at
the pinned commit `8eb16545762be97ace75334109d73824217311f1` in `~/.venvs/slurp-official-eval`
then scores the projected prediction exactly as it scores an unprojected one, and this
study's per-sample port runs beside it with the same identity check at tolerance 1e-6.

### 1.1 A property of the rule, stated before the run

Every gold intent that occurs in TRAIN is legal by construction, and the projection only ever
*replaces an illegal pair*. So a projected row was already wrong on intent, and:

* **intent harms are structurally zero**, and the intent delta is therefore `>= 0` on every
  population and every stratum — **unless** a devel gold intent lies outside the 60 TRAIN
  pairs and a row named it exactly. The read reports the count of devel gold intents outside
  the 60 TRAIN pairs, and the count of rows that lost a correct intent, whatever it is.
* **scenario harms are structurally zero** too: rule 4a keeps `s0`, and rule 4b only fires
  when `s0` is illegal and therefore already wrong.
* **action harms are NOT structurally zero.** Rule 4a can rewrite an action that happened to
  be right while the scenario was wrong (an illegal pair whose action half is the gold
  action). The action column is reported for exactly this reason, and a negative action delta
  is a finding, not a defect.
* **SLU-F1, entities-strict, Word-F1 and Char-F1 deltas are structurally zero.** Any non-zero
  value there is an implementation defect and stops the read.

## 2. Populations

The DEV-1000 roster of the locked baseline, split identity
`8580d199bffc95a51ad6d8c5b2a2e9e39faa2c551dd095f8afcd78174a1e3c84`, 1,000 rows, id for id.

| population | n | source |
|---|---|---|
| pooled DEV-1000 | 1000 | `docs/receipts/probe-samples/DEV-1000.json` |
| OLD500 (prior-exposed at the lock tier) | 500 | `docs/receipts/probe-samples/DEV-500.json` ∩ the roster |
| NEW500 (unexposed at the lock tier) | 500 | `docs/receipts/probe-samples/DEV-1000-NEW500.json` ∩ the roster |
| per scenario | 18 strata | the **gold** scenario of each row |

**No new exposure.** Every row re-scored here was exposed by the sealed 2026-08-25 lock
campaign and re-read by the 2026-09-05 closed-list, KC-S1 and KU-S1c reads. Nothing is
generated, no roster is drawn, and the held-out `test` split is never named, loaded or scored.

## 3. The arms

Each arm is scored **twice over the complete 1,000-row manifest** — once with
`slurp-slu-official` (unprojected, the identity anchor that must reproduce its own published
verdict to the second decimal) and once with `slurp-slu-official-projected` — through
`core.scoring_batch`, one job per manifest, `include_per_sample=True`, never sharded.

| arm | run id | why it is here |
|---|---|---|
| **CLOSED-LIST** | `SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1` | the locked direct baseline; **the lock decision rests on this arm alone** |
| KU-S1c revise | `SAEA-SLURP-KU-S1C-DRAFT-REVISE-DEV1000-V1` | the equal-contact control; full-SLU responses, so the projection applies |
| KU-S1c draft | the same flight's `.phases.json` | MF-7's own +1.4 pp legalisation estimate was measured on this arm's labels |
| KC-S1a | `SAEA-SLURP-KC-S1A-SLOTS-DEV1000-V1` | entity-only responses; the projection must leave them untouched |
| KC-S1b | `SAEA-SLURP-KC-S1B-SLOTS-SCHEMA-DEV1000-V1` | the admitted slot mechanism; same |

**KC-S1a / KC-S1b carry no intent of their own.** Their sealed rows answer
`{"entities": [...]}`; their published intent column is the sealed closed-list intent, copied
in by the model-free join their own read registered. Under rule 2 their sealed rows are
untouched, so their projected official table must be **identical to their unprojected one on
every metric** — a hard invariant this read asserts. Their intent column under the re-lock is,
by the same construction, the **projected** closed-list intent, and the verdict states it as
arithmetic rather than measuring it twice.

**The KU-S1c draft phase has no run manifest of its own** (its bytes live in the flight's
sealed `.phases.json`, already paid for), so it is scored through the same registered scorer
functions directly, over the same complete 1,000 rows, exactly as its own 2026-09-05 read did.
That is stated here so the deviation from "through `core.scoring_batch`" is registered in
advance rather than explained afterwards.

**The 42 KC-S1b fallback rows.** KC-S1b selected its per-intent TRAIN slot-schema block from
the sealed closed-list response; 42 of 1,000 rows (3 unparsed + 39 impossible pairs) fell back
to the full 60-intent schema. The read reports how many of those 42 name a legal intent under
the projection, and how many of the newly legal ones land on the **gold** intent — i.e. how
many would have received the right block, not merely a block. This is a forward-looking
statement about a possible successor cell; **no KC-S1b number is restated because of it.**

## 4. Metrics

Official `evaluate.py`, micro, `--errors --table-layout csv`: scenario, action,
**intent (scen_act)**, entities strict, Word-F1, Char-F1, **SLU-F1**, n gold, n predicted,
skipped, unparsed. Reported for every arm, projected beside unprojected.

Per-sample, for the paired statistics: `scenario_action_exact`, `scenario_exact`,
`action_exact`, `slot_f1_exact_f1`, `slu_f1_f1` — the port's own per-sample fields, the same
ones every SLURP verdict on this carrier has used.

Projection accounting, per arm and per gold scenario: rows projected, rows left alone, rows
unparsed, and the projection map itself (`from -> to`, with counts) so every changed label is
inspectable.

## 5. Paired statistics

`analysis.paired.paired_contrast`, `delta = projected − unprojected` on per-sample official
scores, **10,000 stratified bootstrap replicates, seed 20260903**, strata = the gold scenario,
**CI90**, exact two-sided sign test (McNemar exact). Computed on the SAME sealed rows for both
arms of every contrast — there is no re-flight and no resampling of anything but the rows.

Reported for pooled 1,000, OLD500 and NEW500 separately, plus the per-stratum table every
verdict on this program carries, and both weightings (natural roster and equal-stratum).

## 6. The lock rule (frozen before the read)

The re-locked comparator is **"closed-list + projection"** if and only if, on the CLOSED-LIST
arm:

1. the **intent delta is `>= 0` on BOTH OLD500 and NEW500**, and
2. **no gold-scenario stratum is harmed on intent by more than 1 row.**

A local optimization must not hurt any stratum; that is what condition 2 enforces. If either
condition fails, the projection is **reported and NOT locked**, the comparator stays exactly
the sealed closed-list arm as it is, and the note says so.

The rule is deliberately not a "must gain" gate. A projection worth 0.0 pp is still the right
comparator to lock if it costs nothing and harms nothing, because it removes a free gain from
every future mechanism's reach. Whether the gain is large enough to matter is a reporting
question, not a locking one, and the verdict states the number either way.

**What locking means, exactly.** If the rule passes, the verdict names the comparator identity
— run manifest sha256 + scorer id — that every pending SLURP cell must pair against from that
point on. It does **not** re-open, restate or re-score any published verdict: KC-S1b stays
admitted on its own sealed numbers, KU-S1c stays reported on its own, and the closed-list
verdict's own table is unchanged. The re-lock is prospective.

## 7. Boundaries

* Zero model contacts of any kind; no GPU; no `pip install`; no venv is modified. The pinned
  official evaluator venv `~/.venvs/slurp-official-eval` is **used, never modified**.
* Gold opens **only** through the registered official scorer, on `split_id="devel"` with
  `allow_heldout=False`. **No SLURP devel sentence text is read** anywhere in this work — not
  into a receipt, a document, a table cell or a log line. The held-out `test` split is never
  named, loaded or scored; the scorer refuses any row id naming `slurp:test:`.
* No sealed byte is altered. The derived run manifests this read writes to drive
  `core.scoring_batch` differ from the sealed manifests **only in the `scorers` list**, live
  beside the artifacts they name (as `core.bundle.verify_bundle` requires), carry their own
  sha256 in the receipt, and never replace a sealed manifest.
* Rung 1 of the claim ladder: no admission, no promotion, no superiority claim, no
  generalization claim, no test contact, no Stage-3 activity. The carrier set stays
  Earnings-21+ConEC, SLURP and Audio2Tool.
