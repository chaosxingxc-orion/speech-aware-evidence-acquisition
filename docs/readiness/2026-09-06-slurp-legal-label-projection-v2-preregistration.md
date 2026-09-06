# SLURP legal-label projection v2, promoting an action-named scenario — preregistration (2026-09-06)

Row id: `SAEA-SLURP-MF-LEGAL-LABEL-PROJECTION-V2-V1`. Profile: `model-free-check`.
**Zero model contacts, zero GPU, zero tool, zero embedding, zero network.** Receipts:
`docs/checks/speech-aware-evidence-acquisition/2026-09-06-slurp-legal-label-projection-v2/`.

Authority: the same owner ruling of 2026-09-06 that admitted `slurp-legal-label-projection-v1`
— a legal-label projection is a **model-usage local optimization**, allowed before any
mechanism, on a carrier whose direct baseline is already locked. This registration is written
and committed **before the v2 code exists and before any sealed output row is re-read under
the v2 rule**.

## 0. Why a second rule is registered at all

`slurp-legal-label-projection-v1` locked on 2026-09-06
(`docs/readiness/2026-09-06-slurp-legal-label-projection-relock-v1-verdict.md`). It works and
it is worth almost nothing: intent 71.40 → 71.60 on the closed-list arm, **2 of the 39
legalised rows landing on gold**, and the action column losing 0.60 pp. Its verdict says so
plainly, and then names the reason.

**19 of those 39 rows put a legal ACTION name in the SCENARIO slot** — `locations/query`,
`events/query`, `movies/query` — because the model answered the *action* of
`recommendation_locations` / `recommendation_events` / `recommendation_movies` as if it were
the scenario, and then put a generic `query` beside it. Edit distance is structurally blind to
that: it sends `locations` to `lists`, because that is what `locations` is spelled like. The
label's legality was never the problem; **which** legal label the repair picks is.

v1's verdict priced the alternative descriptively (section 5) and refused to lock it, because
the class was found by reading v1's own output. That is the correct discipline and this
document is its consequence: the promotion rule gets its own identity, its own registration,
its own read and its own lock decision, before it touches a number.

### 0.1 What is already known, stated so this registration is not read as blind

Honesty first, because it changes how this registration should be trusted. v1's verdict is a
published document, and it already reports, **for the closed-list arm only**, that the
action-as-scenario class has 19 rows and that promoting them would land 15 on gold — roughly
+1.5 pp intent. So the *direction and rough size of the headline number on one arm is already
public*, and no claim is made here that the intent result on that arm is a surprise.

Everything else is genuinely unread and is what this registration binds: the complete v2
official table on all five arms, the action and scenario columns, the OLD500 / NEW500 split,
the per-stratum harm table, the branch accounting, the residual after v2, and — the thing that
actually decides the lock — whether the promotion harms any stratum. A rule that gains 15 rows
and harms two strata does not lock here, and that is not knowable from v1's verdict.

## 1. The projection rule, stated deterministically

Identity: `slurp-legal-label-projection-v2`. It is a **different rule**, not a revision of v1:
v1 stays registered, stays locked, and stays readable under its own scorer ids, so the
comparison below is against a live comparator rather than a deleted one.

**The legal inventory and the TRAIN prior are v1's, unchanged**: the 60 `(scenario, action)`
pairs of `data.slurp.load_slurp_ontology(lock, root).actions_by_scenario` (mined from
`train.jsonl` alone, `include_synthetic=False`), and `P(scenario, action)` =
`data.slurp.load_slurp_intent_slot_schema(lock, root).intents[f"{scenario}_{action}"].n`, the
number of TRAIN utterances carrying that intent. TRAIN is construction data and is readable;
no devel or test label enters the rule.

**Ownership.** An action name `x` is *owned* by every legal scenario whose action list
contains `x`. `owners(x)` is that set, and it is derived from the same 60 pairs — nothing else.

**The rule.** Let `(s0, a0)` be the `scenario` / `action` a row's response parsed to.

1. If the response **did not parse**, it stays unparsed. Nothing is invented. *(branch
   `unparsed`)*
2. If `s0` or `a0` is **absent** (`None`) — the shape a slot-only arm such as KC-S1a / KC-S1b
   answers with — the row is **untouched**; there is no `scenario_action` to project.
   *(branch `no-label`)*
3. If `(s0, a0)` is already one of the 60 legal pairs, the row is **untouched**.
   *(branch `already-legal`)*
4. Otherwise the pair is illegal and the row is **projected**:
   * **4-PROMOTE (the new branch).** If `s0` is **not** a legal scenario **but is** a legal
     action name — `owners(s0)` is non-empty — emit `(s*, s0)` where `s*` is the owner
     minimizing the ordered key `(-P(s, s0), s)`: the **larger TRAIN prior** first, then the
     alphabetically first scenario name. When `owners(s0)` holds exactly one scenario that key
     is degenerate and `s*` is that scenario; the multi-owner case is the same expression, and
     is written as one rule rather than two so there is no second code path to keep in sync.
     `a0` is **discarded** on a promoted row. *(branch `promote`)*
   * **4-FALLBACK.** Otherwise apply **v1 unchanged** — `reproduction.slurp_scoring.project_slu_label`,
     the same function object, not a copy: keep a legal `s0` and take its nearest action by
     Levenshtein with `(-P(s0, a), a)` as the tie-break; else take the nearest legal scenario
     by `(lev(s0, s), -P(s), s)` and then its nearest action the same way.
     *(branch `edit-distance`)*

Four boundary cases are registered here rather than discovered later:

* **`s0` is both a legal scenario and a legal action name.** 4-PROMOTE does not fire — its
  guard is "`s0` is not a legal scenario" — and v1's rule 4a keeps `s0` and moves only the
  action. The promotion exists to repair a scenario slot that cannot be right; a legal
  scenario slot may well be right.
* **`s0` is the empty string.** The inventory refuses an empty action name, so `owners("")` is
  empty and the row takes 4-FALLBACK, exactly as it does under v1.
* **`a0` is a legal action name too.** Irrelevant: 4-PROMOTE reads only `s0`.
* **The promoted pair can never equal the parsed pair**, because `s*` is a legal scenario and
  `s0` is not, so a promoted row is always `changed`.

**Entities are never touched.** The rule rewrites `scenario` and `action` and nothing else, so
`entities`, both distance blocks and SLU-F1 are structurally unchanged on any arm. That is an
assertion the read makes row by row on every arm, not a hope.

**The official scorer is applied to the projected label, unchanged.** The projection runs
strictly between `reproduction.slurp_scoring.parse_slu_response` (byte-identical, untouched)
and the construction of the official prediction file. The real, unmodified `evaluate.py` at
the pinned commit `8eb16545762be97ace75334109d73824217311f1` in `~/.venvs/slurp-official-eval`
then scores the projected prediction exactly as it scores an unprojected one, and this study's
per-sample port runs beside it with the same identity check at tolerance 1e-6.

### 1.1 Properties of the rule, and the expected direction of every metric, in advance

The v2 rule replaces an illegal pair and only an illegal pair, exactly as v1 does. So:

* **Intent harms are structurally zero**, and the intent delta is `>= 0` on every population
  and every stratum against **both** baselines — unless a devel gold intent lies outside the
  60 TRAIN pairs and a row named it exactly. v1's read re-derived that count as **0** on this
  roster; this read re-derives it again rather than citing it.
* **Scenario harms are structurally zero.** 4a keeps `s0`; 4b and 4-PROMOTE fire only when
  `s0` is illegal and therefore already wrong.
* **Expected scenario direction: UP, for the first time.** v1's scenario column did not move
  at all (81.00 → 81.00): its edit-distance scenario choice never happened to be gold.
  4-PROMOTE chooses a scenario for a reason rather than by spelling, so a positive scenario
  delta is expected against both baselines. A zero would be a finding.
* **Expected intent direction: UP against both baselines**, by construction of the class and,
  on the closed-list arm, at roughly the +1.5 pp v1's verdict already published.
* **Action harms are NOT structurally zero, and the expected direction is stated before the
  read.** Against **v1**: **UP or flat.** On a promoted row v1 typically emitted the generic
  action it was handed (`locations/query -> lists_query` keeps `query`) while v2 emits `s0`
  itself as the action; where the row's gold action is that specific name, v2 converts an
  action miss into an action hit. A harm needs `a0` to have been the gold action while `s0`
  was not, which the class makes unlikely but not impossible. Against **unprojected**: v1 lost
  0.60 pp there; v2 is expected to give some of that back, so **better than −0.60**, but the
  **sign is not predicted** and will be reported whatever it is. v2 keeps every one of v1's
  4-FALLBACK action rewrites, including the ones that caused those losses.
* **SLU-F1, entities-strict, Word-F1 and Char-F1 deltas are structurally zero** on every arm.
  Any non-zero value there is an implementation defect and stops the read.

## 2. Populations

Identical to v1's, id for id. The DEV-1000 roster of the locked baseline, split identity
`8580d199bffc95a51ad6d8c5b2a2e9e39faa2c551dd095f8afcd78174a1e3c84`, 1,000 rows.

| population | n | source |
|---|---|---|
| pooled DEV-1000 | 1000 | `docs/receipts/probe-samples/DEV-1000.json` |
| OLD500 (prior-exposed at the lock tier) | 500 | `docs/receipts/probe-samples/DEV-500.json` ∩ the roster |
| NEW500 (unexposed at the lock tier) | 500 | `docs/receipts/probe-samples/DEV-1000-NEW500.json` ∩ the roster |
| per scenario | 18 strata | the **gold** scenario of each row |

**No new exposure.** Every row re-scored here was exposed by the sealed 2026-08-25 lock
campaign and re-read by the 2026-09-05 closed-list, KC-S1 and KU-S1c reads and by v1's own
read. Nothing is generated, no roster is drawn, and the held-out `test` split is never named,
loaded or scored.

## 3. The arms

Each arm is scored **three times over the complete 1,000-row manifest** — with
`slurp-slu-official` (unprojected, the identity anchor that must reproduce its own published
verdict to the second decimal), with `slurp-slu-official-projected` (v1, the locked
comparator, which must reproduce v1's verdict to the second decimal), and with the new
`slurp-slu-official-projected-v2` — through `core.scoring_batch`, one job per manifest,
`include_per_sample=True`, never sharded.

| arm | run id | why it is here |
|---|---|---|
| **CLOSED-LIST** | `SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1` | the locked direct baseline; **the lock decision rests on this arm alone** |
| KU-S1c revise | `SAEA-SLURP-KU-S1C-DRAFT-REVISE-DEV1000-V1` | the equal-contact control; full-SLU responses, so the projection applies |
| KU-S1c draft | the same flight's `.phases.json` | MF-7's legalisation estimate was measured on this arm's labels |
| KC-S1a | `SAEA-SLURP-KC-S1A-SLOTS-DEV1000-V1` | entity-only responses; every entity-side metric must be untouched |
| KC-S1b | `SAEA-SLURP-KC-S1B-SLOTS-SCHEMA-DEV1000-V1` | the admitted slot mechanism; same |

**KC-S1a / KC-S1b carry no intent of their own.** Their sealed rows mostly answer
`{"entities": [...]}`; their published intent column is the closed-list intent, copied in by
the model-free join their own read registered. v1's read corrected one of v1's own
preregistered expectations here and that correction is carried forward rather than repeated as
a fresh discovery: **those arms are not label-free** — KC-S1a volunteers a pair on 194 of 1,000
rows and KC-S1b on 456 — so their as-sealed label columns do move under a projection. What
must hold, and what this read asserts row by row, is that **every entity-side metric is
identical across all three views on both arms**.

**The KU-S1c draft phase has no run manifest of its own** (its bytes live in the flight's
sealed `.phases.json`, already paid for), so it is scored through the same registered scorer
functions directly, over the same complete 1,000 rows, exactly as its own 2026-09-05 read and
v1's read did. That deviation from "through `core.scoring_batch`" is registered here in
advance rather than explained afterwards.

## 4. Metrics

Official `evaluate.py`, micro, `--errors --table-layout csv`: scenario, action,
**intent (scen_act)**, entities strict, Word-F1, Char-F1, **SLU-F1**, n gold, n predicted,
skipped, unparsed. Reported for every arm in all three views.

Per-sample, for the paired statistics: `scenario_action_exact`, `scenario_exact`,
`action_exact`, `slot_f1_exact_f1`, `slu_f1_f1` — the port's own per-sample fields, the same
ones every SLURP verdict on this carrier has used.

Projection accounting, per arm: rows per **rule branch** (`already-legal`, `promote`,
`edit-distance`, `ineligible`), the projection map itself (`from -> to`, with counts) split by
branch, the rows changed per **gold scenario**, and how many changed rows land on the gold
intent. Reported for v1 and v2 side by side so the branch that carries the difference is
visible rather than inferred.

## 5. Paired statistics

`analysis.paired.paired_contrast` on per-sample official scores, **10,000 stratified bootstrap
replicates, seed 20260903, strata = the gold scenario, CI90**, exact two-sided sign test
(McNemar exact) — v1's settings, unchanged, so the two reads are comparable.

**Three contrasts, all on the SAME sealed rows**, no re-flight and no resampling of anything
but the rows:

| contrast | what it answers |
|---|---|
| **v2 − v1** | does the new rule beat the **locked comparator** |
| **v2 − unprojected** | what the projection is worth **in total** against the raw sealed labels |
| v1 − unprojected | the anchor: it must reproduce v1's published verdict exactly |

Reported for pooled 1,000, OLD500 and NEW500 separately, plus the per-stratum table every
verdict on this program carries, and both weightings (natural roster and equal-stratum).

## 6. The lock rule (frozen before the read)

The comparator is re-locked as **"closed-list + projection v2"** if and only if, on the
CLOSED-LIST arm, **in BOTH the `v2 − v1` and the `v2 − unprojected` contrast**:

1. the **intent delta is `>= 0` on BOTH OLD500 and NEW500**, and
2. **no gold-scenario stratum is harmed on intent by more than 1 row.**

If either condition fails in either contrast, v2 is **reported and NOT locked**, and the
comparator stays exactly what v1's verdict locked: the sealed closed-list arm read through
`slurp-slu-official-projected`, intent 71.60.

This is v1's rule, applied against two baselines instead of one, for a reason: v1 is now the
incumbent, and a successor must beat the incumbent *and* not have quietly reintroduced a harm
the incumbent avoided. As in v1 the rule is deliberately not a "must gain" gate — a projection
worth 0.0 pp is still the right comparator to lock if it costs nothing and harms nothing —
but unlike v1, v2 is expected to gain, and a v2 that does not gain is a finding worth stating.

**What locking means, exactly.** If the rule passes, the verdict names the comparator identity
— run manifest sha256 + scorer id — that every pending SLURP cell must pair against from that
point on. It does **not** re-open, restate or re-score any published verdict: KC-S1b stays
admitted on its own sealed numbers, KU-S1c stays reported on its own, and neither the
closed-list verdict's table nor v1's is changed. The re-lock is prospective. v1 stays a
registered, resolvable scorer whatever the outcome.

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
