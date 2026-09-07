# KC-E1 — the Earnings-21 pre-meeting brief, whole prompt (v1, DRAFT — SUPERSEDED)

> **Superseded 2026-09-06 by `docs/readiness/2026-09-06-e21-kc-e1-pre-meeting-brief-v2-preregistration.md`.**
> The owner ruled on the pairing question this draft's §4 put to them (the 90-second window is the
> paired unit, the call is the bootstrap cluster), and precondition 1 of §7 is now closed by the
> additive D1 evidence supplement `docs/receipts/artifacts/d1-e21-participant-names.json`. §3, §4,
> §7 and §8 below are REPLACED by v2's; §1, §2, §5, §6 and §9 stand and v2 restates only what moved.
> Read v2 for anything the flight will act on.

**Status: DRAFT. Not authorized to fly.** E5 built the pieces — the evidence source, its form twin,
the semantic taxonomy, the comparator's fourth metric, the per-call provenance receipt and the config
fragments — with **zero model contacts and no GPU**. This document states, before any result exists,
what the cell would measure and what would count as an answer. Two preconditions in §7 are unmet
today and one of them is a hard gate.

Experiment fragment: `configs/experiment/e21-kc-e1-brief-44-v1.json`. Arms:
`configs/baseline/e21-kc-e1-brief-whole-prompt.json`, `configs/baseline/e21-ku-e1c-brief-placebo.json`.
Program context: `docs/readiness/2026-09-05-three-dimension-experiment-program.md` §4a (KC-E1) and
§4b (KU-E1c).

---

## 1. The question, and the one factor

ConEC's own Table 1 says the participant roster lifts PERSON coverage from 30 % to 82 %, and the
2026-09-06 comparator says PERSON is the open class on this core: **22.5 %, between Whisper large's
published 28.9 and ConEC's post-hoc oracle ceiling of 13.0**. ORG, by contrast, is already at 17.2
against that oracle's 17.7, so there is almost nothing there to win. KC-E1 asks whether supplying the
call's own pre-meeting brief — the thing a human reads before joining the call — closes part of the
PERSON gap without costing corpus WER.

**The one factor is the brief's CONTENT**, and it is isolated by the twin, not by the comparator:

| contrast | what moves | what it can attribute |
|---|---|---|
| KC-E1 vs **KU-E1c** (the form twin) | the entity strings alone — same labels, same entry count, same whitespace-token count per line, every entry token replaced by a neutral placeholder chosen by position | **knowledge**: a gain here cannot be prompt shape, length, or the instruction |
| KC-E1 vs the **sealed comparator** | the evidence AND the task instruction | brief-plus-instruction; reported, but never quoted as the content effect |

The second row is stated rather than hidden: an evidence arm needs an instruction that names the
reference material, or the core receives an unexplained block of text. The study's own
`fixed-legal-context` precedent (`configs/baseline/fixed-batch-matched-locked-buf90.json`) makes the
same change for the same reason. The two arms' fragments differ in exactly one key,
`evidence_source`; against the sealed baseline fragment, five keys differ (`arm`, `evidence_source`,
`brief_max_entries_per_class`, `scorers`, `task_instruction`) and nothing else.

## 2. What the brief contains, and where every line comes from

Two ConEC files per call, and nothing else. No reference transcript, no timestamp file, no `wer_tags`
sidecar, no bias list — asserted by `tests/unit/test_class_lists.py::
test_the_renderer_opens_no_reference_path`, which records every path the renderer opens and demands
each one live under `contexts/`.

| line | source | labelled by ConEC? |
|---|---|---|
| Participants and roles | `contexts/participant_names/<call>.names.txt`, one `Name - Role` line per speaker | **yes** |
| Organizations named in the roster | the role field of every roster line carrying no title cue — ConEC lists sell-side analysts by their firm alone | **yes** |
| Divisions and segments named in the roster | a roster role naming a division | **yes** |
| Company and ticker **candidates** | `contexts/<call>.txt`, tokens beside a legal-entity suffix or an exchange cue | no — a cue scan |
| Product and segment **candidates** | the same file, tokens beside a segment cue | no — a cue scan |
| Other terms from the call's documents | the same file, de-duplicated in document order | no |

The distinction is not cosmetic. ConEC's roster is labelled data; its context document is a
lowercased, function-word-stripped token stream with no casing, punctuation or sentence structure, so
nothing can be read off it and the cue-scan lines say **CANDIDATES** in the brief's own text. A
verdict must report the two families apart, because a gain carried by the labelled roster lines is a
different finding from one carried by a keyword dump.

Each entry carries its Whisper-normalized form in brackets **only where casing or punctuation moves
it** (`C.L. King [normalized: c l king]`). Both sides of every metric are normalized, so an
all-lowercase token whose only change is the number normalizer is not annotated — that annotation
would be pure token cost.

Per-call provenance for all 44 calls, with both source sha256s and the token cost:
`docs/checks/speech-aware-evidence-acquisition/2026-09-06-e21-pre-meeting-brief-provenance/`. **88
distinct source files for 44 calls**, each keyed by its own sample id — so an evaluation call's brief
is built from that call's own context, which is the benchmark's intended use of the layer.

## 3. Population, comparator and pairing

**Population**: all 44 `earnings21-original` discovery calls, 39.263 h, 1,593 fixed 90-second windows
per cell, split identity `fcc1b0bc…d69e`. No draw: the same population the comparator was measured
on. The **E5 split** (34 `kb-construction`, 10 `r4-e21-sub10` evaluation) is a REPORTING split; every
figure is reported on all 44 and on both halves, and an evaluation claim quotes the ten's column
only.

**Comparator**, by name, with the pairing rules of
`docs/readiness/2026-09-06-earnings-agentic-metric-baseline-v1.md` §7 and §9:

| | all 44 | evaluation 10 |
|---|---:|---:|
| corpus WER % (`asr-wer-whisper`) | 8.200 | 7.185 |
| ConEC-mirror PERSON / ORG entity WER % | 22.5 / 17.2 | in `verdict/result-summary.json` |
| numeric-value accuracy % | 90.73 | 92.43 |
| negation-critical error rate % | 0.0278 | 0.0185 |

## 4. Power, stated honestly

**The program's own rule is `n >= 400` paired units for an effectiveness claim, and this carrier
has 44 calls.** That is the central statistical fact about every Earnings cell and it is not solved
by choosing a smaller unit and pretending the units are independent.

* **PERSON is thin.** 2,917 PERSON reference words over 44 calls — about 66 per call. A per-call
  PERSON WER is a ratio over ~66 words; its call-to-call variance will dominate any plausible effect.
* **Corpus WER is not thin.** 359,765 reference words over 1,593 windows.
* **The negation-critical rate is far too thin to gate anything.** 100 HIGH reference words on all 44
  and **14 on the evaluation ten**, with 15 of the 44 calls carrying none at all.

**Inference this cell will run**, and it is the conservative one:

1. the statistic is computed at **mention level** (ConEC entity WER is `(S + D) / tagged reference
   words`, pooled), so the count that enters it is 2,917 PERSON words, not 44 calls;
2. the interval is a **cluster bootstrap over the 44 calls**, resampling whole calls with
   replacement. The effective sample size is therefore the 44 clusters, whatever the mention count
   says, and the interval will be wide. That is the honest width;
3. the naive mention-level interval is reported **beside** it, labelled as the optimistic bound, so a
   reader can see how much of the apparent precision is clustering.

**Proposed to the owner, not assumed: a segment-level pairing.** The natural finer unit is the
**90-second window** — 1,593 paired units per cell, each an independent model contact with its own
reference span, which would satisfy the `n >= 400` rule at the level the contacts actually happen.
The objection is that windows within a call share a speaker set, an acoustic channel and a
vocabulary, so they are correlated, and a window-level interval that ignores that is the same
optimism as a mention-level one. **The proposal is: adopt the window as the pairing unit AND keep the
call as the bootstrap cluster.** That combination gets the resolution of 1,593 units and keeps the
independence claim at 44, and it is a design decision for the owner rather than an implementer's
choice, because it decides what an Earnings effectiveness claim means for every later Earnings cell.
Until it is decided, **this cell's decision rule uses the call-clustered interval** — the strictest of
the three.

## 5. Metrics and the decision rule

Manifest scorers, declared in the flight's own manifest rather than produced out of band:
`asr-wer-whisper`, `conec-entity-wer-official`, `numeric-value-accuracy-v1`,
`semantic-high-impact-error-rate-v1`, `cost`.

**Primary**: ConEC-mirror **PERSON** entity WER, then all eight published classes with their
reference-word counts, beside ConEC Table 2 rows 1 (biasing floor), 8 (Whisper large, no biasing) and
5 (the post-hoc oracle ceiling).

**Decision**:

> **ADMITTED** iff, on the reported roster, the call-clustered CI90 **lower bound** on the PERSON
> entity-WER reduction is **> 0 against the sealed comparator** AND **> 0 against KU-E1c**, and every
> guard below holds.
>
> **NULL** if either lower bound includes 0. A NULL with a positive point estimate against the twin
> and a negative one against the comparator is reported as "the form carried it", and the next cell
> is a supply-form question, not a content one.
>
> **HARMFUL** if any guard fails, with the failing guard named and the per-class table published
> either way.

**Guards**:

| guard | test |
|---|---|
| corpus WER non-inferiority | CI90 **upper** bound on (KC-E1 − comparator) corpus WER **<= 0** |
| numeric-value accuracy not worse | CI90 lower bound on (KC-E1 − comparator) accuracy **>= 0** |
| negation-critical rate not worse | point estimate reported with the ConEC taxonomy id; **advisory only**, with §4's power caveat attached, because 14 HIGH reference words on the evaluation ten cannot support a gate |
| over-generation not worse | insertions per reference word reported against the comparator's 10,700 / 359,765; a brief that gets read aloud shows up here first |

**Reported whatever the outcome**: the per-class table with reference-word counts; all 44 / 34 / 10
apart; the roster-line versus candidate-line split of §2; the brief's flight-tokenizer token
distribution; sector and sample-rate slices under natural-mixture and equal-stratum weighting;
throughput and token totals against the comparator's 1,935,965 prompt / 439,532 completion.

## 6. Budget

| | value | basis |
|---|---:|---|
| planned model calls | 3,500 | 1,593 windows x 2 cells = 3,186, plus 314 retry headroom; the comparator realized exactly 1,593 |
| planned speech audio seconds | 300,000 | 141,345.85 realized per pass x 2 = 282,692, rounded up |
| planned GPU hours | 3.2 | the comparator realized 3,504.38 GPU-s (0.973 GPU-h) for one pass at this geometry; two passes is 1.95 before the brief, and the brief roughly triples the prompt (comparator mean 1,215 prompt tokens per window; the brief adds a median 969 and a maximum 2,565 whitespace tokens) |
| paid API spend | 0 | unchanged and still in force |

Re-measured on the preflight; the flight **stops and reports** if the measured rate projects past 3.2
GPU-h.

## 7. Preconditions — two, and the first is a hard gate

1. **`e21_participant_names` is absent from D1.** `docs/receipts/artifacts/d1-identity.json` records
   four ConEC layers (`e21_contexts`, `e21_nlp_references`, `e21_timestamps`, `e21_wer_tags`) and not
   this one, and `data.identity.conec_layers` does not build it. The routing rule exists
   (`contracts.gate_evidence_identity._route_evidence_layer_key` maps
   `contexts/participant_names/<file>` to `e21_participant_names`), so a gated run **fails closed at
   the evidence-identity rail** the moment the roster half of the brief is resolved. This is the
   pre-existing state `core.evidence`'s own `conec-names` paragraph already records; nothing in E5
   weakened or bypassed it. **The flight cannot take off until a D0/D1 update adds that layer**, and
   that update is its own registered action, not a step inside this cell.
2. **Prompt fit is unmeasured on the flight tokenizer.** The brief runs **263 to 2,565 whitespace
   tokens** (median 969) against a 6,144-token slot whose certified worst request was 2,258 tokens.
   Whitespace tokens are a lower bound on model tokens. The preflight must measure the real
   distribution and either confirm the fit with the study's usual margin or set
   `brief_max_entries_per_class`, and **the cap it sets applies identically to both cells** or the
   twin stops being a twin.

## 8. What the flight agent must do, in order

1. **Close precondition 1** or stop. Do not fly with the roster half disabled: dropping it would
   change the cell from "the pre-meeting brief" to "a keyword list", which is a different question
   and already has an arm (`conec-contexts`).
2. **Prompt fit.** Tokenize every call's brief with the flight tokenizer; report the per-call
   distribution beside the whitespace counts in the E5 provenance receipt, and the worst-case total
   request. Set `brief_max_entries_per_class` if needed and record the value in both fragments.
3. **Wire check.** A 4-row dry run through the committed launcher path on construction calls only:
   confirm two `[evidence …]` blocks arrive in the request in roster-then-document order, that
   `evidence_provenance` carries both relpaths, that the derivation registry accepts both records,
   and that the placebo cell's requests match the arm cell's token counts line for line.
4. **Register the exposure row** `SAEA-E21-KC-E1-BRIEF-44-V1` before the first contact, with the
   split identity, both cells, the budget of §6 and the inherited exposure of these 44 calls, and
   **commit it** before takeoff.
5. **Fly both cells** under one build, one serving geometry, one audio path. One experiment in
   flight; at most one recovery re-registration, and a second failure stops the flight.
6. **Score** each complete manifest once through `core.scoring_batch`, never sharded, under the four
   metrics plus cost.
7. **Verdict** against §5, with the per-stratum tables of §5 and the power statement of §4 restated
   in it. If the owner has by then ruled on the window-level pairing, use it and say so; if not, the
   call-clustered interval governs.

## 9. Claim surface

Discovery data. No superiority, generality or Stage-3 claim; no knob tuned on the evaluation ten; no
Earnings-22 contact; no confirmatory read; no retrieval or multi-contact variant (that is
KU-E1 / E1c / E2). `paper-scale-confirmatory` is not available to this repository and is not
requested.
