# NX R6 Perception instruction-template candidates v1 (SLURP, Stage 3): three hand-written arms from aggregate tables

**Status: CANDIDATES ONLY.** Nothing is registered, re-pinned, flown or admitted (registration waits for owner decision
246). Author: Claude Fable 5.1 (root coordinator), 2026-10-10, master. Every candidate is labelled
**`author: hand (Fable 5.1 from aggregate tables)`** (programme C0.5 / C3; decision 245 phase 1). The label lives here
and not inside the template files, because a phase template is sent to the model byte for byte.

**Contacts: zero.** No model, server, tokenizer, scorer, GPU or network contact; no gold, utterance text, transcript,
filler, note body or model output was read. Inputs were the aggregate tables of
`docs/results/2026-10-10-slurp-nx-r6-upstream-empty-decision-offline.md` and
`docs/results/2026-10-09-slurp-nx-exchange-rates-offline.md` only. Design of record:
`docs/readiness/2026-10-10-slurp-nx-r6-node-local-then-cascade-design-v1.md` (section 2.2).

## 1. What the arms replace

| item | value |
| --- | --- |
| locked Perception template (delivering arm, last) | `configs/probes/slurp_native_role_perception_v3.txt` |
| its sha256 (working bytes, LF, ASCII) | `767497809ccad58589f4f2537ffb29c3bb15120b4828dfa5edcb87abe63ac8a2` |
| its word count (`wc -w`) | 128 |
| how it is pinned | lock base `configs/baseline/slurp-native-stage3-nx-r5-composed-dev2000-added-baseline-v1.json`, `phase_material/perception/instruction_template: probes/slurp_native_role_perception_v3.txt` |
| output contract (grammar-enforced on the wire) | `slurp-intent-hypotheses-v1`: 1-3 candidates, each exactly `intent_id` (legal enum), `distinction` (<= 128 chars), `evidence_refs` and `unresolved_fields` (maxItems 0); no other key |
| the only free channel | the `distinction` string (plus candidate order and count); the pinned tag grammar `configs/probes/nx/perception/r6/TAG-GRAMMAR-v1.md` defines what the arms put at its head |

Each candidate is a complete replacement file: ASCII, LF, one trailing newline, no placeholder token, no example
utterance, no slot value, no confidence number. The intent instructions of v3 (coverage, complete legal ids, model
order, no duplicates, no padding, no confidence fields, distinctions are not answers, the closing tool sentence) are
kept word for word so that the intent guards measure the cost of the TAG alone. The only changes are the JSON shape
line (the distinction placeholder shows the tag head) and the tag instruction block.

| arm | file | sha256 | words | tag set | mentions |
| --- | --- | --- | ---: | --- | --- |
| p1 | `configs/probes/nx/perception/r6/r6-p1.txt` | `8cd1584653e8bd99db709728360e0c359651f90b16974a551e1c3b3bb986f2a8` | 187 | `E=none|some` | none |
| p2 | `configs/probes/nx/perception/r6/r6-p2.txt` | `2a27d0d446c6d83103412040d6dd50532acc2e5bbae18245c07362ddf45d0f42` | 243 | `E=none|some` | up to 3 `M=` (spoken words, <= 4 each) |
| p3 | `configs/probes/nx/perception/r6/r6-p3.txt` | `12ff7812e11f06bf4368ffd11129fee173c42f53dae268f4ae5ffe3863543a1e` | 264 | `E=none|some|unsure` | up to 3 `M=` |
| aa | twin `replicate_of: lock` | -- | 128 | -- | -- |
| lock | delivering, `configs/probes/slurp_native_role_perception_v3.txt` | `76749780...` | 128 | -- | -- |

Length note: the R1 Solver candidates kept a +-40 % length class around the locked template (96-224 words for a
160-word lock). p2 and p3 exceed that class (+90 % / +106 % of 128). They are kept at this length because the mention
rules are the mechanism under test; Perception contacts are far from the slot (P-SV-4 measured 2,577 base prompt
tokens at a 24,576 slot), so the cost is prompt tokens, which the reader reports per arm. `template_tokens` are
measured at registration (tokenizer pass on the cell's own FIT run), not here.

## 2. Mechanism hypotheses and the failure class each targets

| arm | hypothesis | failure class (aggregate counts, Fold B 1,080 rows, v4g base) | node-local prediction |
| --- | --- | --- | --- |
| p1 presence tag | the core can judge "no entity value expressed" from the speech at the Perception node, where it is not pulled toward filling by slot exemplars (the Solver's false fills rise with entity-bearing exemplars in view); a binary tag costs few tokens and no intent words | empty-gold false fill 91 (i1) / 93 (i2) rows; the Solver's own verdict as classifier: recall 0.81-0.83, precision 0.74-0.76 on empty-gold | `E=none` recall >= 0.80, precision >= 0.75 on the 392 empty-gold rows; intent guard within the twin's movement |
| p2 presence + heard mentions | offering the exact spoken words of each heard mention gives the Solver (and a deterministic consumer) options to VERIFY instead of values to extract from a long supply; targets the single-mention rows the aggressive Solver arm emptied and the "value in supply, not delivered" class | 22 / 23 non-empty rows lost by the aggressive arm (single `date` / `time` / `food_type` / `media_type` mentions, intent rate ~0.8, gold at rank 1 on 18 / 21); 107 / 407 delivered errors with the value in the supply | mention containment (gold entities whose spoken surface is offered) >= 0.70 on non-empty rows; option precision >= 0.60; `E=none` metrics as p1 |
| p3 presence with hedge + mentions | an explicit `unsure` raises the PRECISION of `none` (the gate consumer trades 0.033 per false fill removed against 0.070 per exact row lost, so precision matters more than recall); short / noisy SLURP audio is where the aggressive arm lost rows | same classes; audio duration AUC 0.665 for empty-gold (shorter = emptier) means duration alone confounds a naive verdict | `E=none` precision >= 0.80 with recall >= 0.70; `unsure` rate under 15 %; mentions as p2 |

## 3. What the read must report per arm (reader E2b, to be built after R5 seals)

Tag parse rate (`ok` / `absent` / `invalid`) on rank-1 and on all candidates; `E=none` AUC, precision, recall against
empty-gold; `E=some` precision / recall against non-empty gold; `unsure` rate by gold class; mention containment and
option precision (type-free, normalised surface) with per-slot-type splits; paired intent guards against lock (gold on
list, rank-1 share, candidate count, prompt tokens, `note_parse_status`); the information-gain term (cross-fitted AUC of
{N1, intent prior, verdict} minus {N1, intent prior}); the gate estimate (`verdict x N1 >= 0.2` on the lock Solver
column, v4g base: pp with CI, false fills removed, non-empty exact lost, intent rows moved); and each arm's own level-2
Solver column against lock's (normalised exact-set, false fill, non-empty exact, intent rows moved).

## 4. Checks against the refusal list (instrument README section 4)

No supply knob, release swap, per-arm bound or response-format change; templates under `configs/probes/`; distinct
paths and digests; none equal to the locked template; three candidates (<= 6); the delivering arm last and unpinned;
exactly one twin; node `perception`; no `{identifier}` placeholder; ASCII, LF, trailing newline (verified with `file`
and `wc` at authoring). Fit: Perception arms are bounded by the pre-flight estimate (2,577 + template tokens + 48 x 149
<< 20,862); the level-2 Solver contacts by the realised gate.
