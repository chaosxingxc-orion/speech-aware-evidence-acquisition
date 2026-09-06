# SLURP consumption cells KU-S1c and KU-S1 — verdict (2026-09-05)

Run id `SAEA-SLURP-KU-S1C-DRAFT-REVISE-DEV1000-V1` (attempt `attempt-20260906T042946Z-44720f`,
study commit `90b11039`), profile `bounded-discovery-probe`. Preregistration:
`docs/readiness/2026-09-05-slurp-consumption-ku-s1-v1-preregistration.md`. Receipts:
`docs/checks/speech-aware-evidence-acquisition/2026-09-05-slurp-consumption-ku-s1-v1/`.
One cell flown, one attempt, no recovery, one seal, one read. The second registered cell, **KU-S1,
was refused before registration and never flew** (section 6).

## Verdict

**KU-S1c is reported, never decided** — it carries no admission gate; it is the equal-contact,
no-knowledge control every two-contact SLURP cell's delta is now stated net of. What it establishes:

* **A second look at the same audio, with the same information, is worth essentially nothing.**
  Against its own draft, the revise contact moves intent by **+0.30 pp** pooled (CI90
  [−0.40, +1.00], 11 saves / 8 harms) and **+0.60 pp** on the unexposed NEW500 (CI90 [−0.60, +1.80],
  8 saves / 5 harms). Both CIs include zero. It changed the answer on **36 of 1,000 rows (3.6 %)**
  and the intent on **26 (2.6 %)**; 964 rows came back byte-identical.
* **The gain that does show up against the comparator is mostly the CONTROL TURN, not the contact.**
  KU-S1c reaches intent **72.90** against the closed-list baseline's **71.40** (+1.50 pooled, CI90
  [+0.30, +2.70]; **+1.60 on NEW500, CI90 [−0.20, +3.40] — includes zero**). The draft phase alone —
  still ONE contact, but carrying the phase CONTROL turn the direct baseline never sent — already
  reaches **72.60**. So **+1.20 of the +1.50 is the control turn** and +0.30 is the second contact.
  This is the cell's most useful product and it is a caution for every phase cell on this carrier:
  a phase program changes two things at once against a `policy: "fixed"` direct arm.
* **SLU-F1 does not move: 35.92 against 35.80, +0.12.** Per-sample SLU-F1 is if anything slightly
  negative (−0.68 pooled CI90 [−1.58, +0.22]; −1.47 on NEW500 CI90 [−2.90, −0.10] with 25 saves and
  30 harms, sign test p = 0.59). The slot layer is where the second contact does the only thing it
  reliably does: **+0.28 pp per-sample slot F1 over its own draft** pooled (CI90 [+0.05, +0.53],
  7 saves / 1 harm) and +0.29 on NEW500 (CI90 [+0.07, +0.55], 4 saves / **0 harms**) — real,
  consistent, and about a thirtieth of what KC-S1b's TRAIN slot schema bought.
* **Gain per extra contact: +0.41 SLU-F1 and +0.30 pp intent over its own draft; +0.12 SLU-F1 and
  +1.50 pp intent over the one-contact comparator, of which the contact itself owns +0.30.**

Read beside KC-S1a, the picture on this carrier is now consistent on both layers: the extra contact
alone was worth −0.05 SLU-F1 on the slot stage and is worth +0.30 pp intent here, both inside noise.
**Contacts are not the lever on SLURP; constructed knowledge is** (KC-S1b, +8.55 SLU-F1).

## 1. The official table

Official `evaluate.py` at pinned commit `8eb1654…311f1` in `~/.venvs/slurp-official-eval` (used,
never modified), `--average micro --errors --table-layout csv`, over complete 1,000-row roster
files, never sharded, one job per manifest through `core.scoring_batch`. The port-vs-official
identity check passed on all three scored sets (absolute difference 0.0, 0.0 and 5.6e-17).

| arm | contacts/row | scenario | action | **intent** | entities strict | Word-F1 | Char-F1 | **SLU-F1** | n gold | n predicted | skipped | unparsed |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **KU-S1c (sealed, revise)** | 2 | 81.50 | 75.20 | **72.90** | 23.26 | 33.99 | 38.07 | **35.92** | 1000 | 1000 | 0 | 4 |
| KU-S1c draft phase (same flight) | 1 | 81.40 | 74.90 | 72.60 | 22.50 | 33.62 | 37.62 | 35.51 | 1000 | 1000 | 0 | 2 |
| CLOSED-LIST (comparator) | 1 | 81.00 | 73.90 | 71.40 | 21.91 | 33.69 | 38.20 | 35.80 | 1000 | 1000 | 0 | 3 |
| KC-S1b (slot schema, admitted) | 2 | 81.00 | 73.90 | 71.40 | 31.37 | 41.58 | 47.51 | 44.35 | 1000 | 1000 | 0 | 0 |
| KC-S1a (slot contact control) | 2 | 81.00 | 73.90 | 71.40 | 21.82 | 33.62 | 38.17 | 35.75 | 1000 | 1000 | 0 | 2 |
| DEV-1000 BLEND (locked cell, reference) | ≤2 | 83.90 | 77.60 | 75.70 | 27.27 | 39.41 | 44.24 | 41.69 | 1000 | 1000 | 0 | 2 |
| DEV-1000 M0 (sealed 2026-08-25) | 1 | 70.00 | 61.50 | 53.60 | 21.94 | 34.66 | 39.46 | 36.90 | 1000 | 1000 | 0 | 5 |

The CLOSED-LIST row is this read's **identity anchor**: it reproduces its own 2026-09-05 verdict to
the second decimal on all seven metrics, from the same sealed bytes.

**The draft row is not a separate flight.** It is the first phase's own sealed responses, read from
`SAEA-SLURP-KU-S1C-DRAFT-REVISE-DEV1000-V1.phases.json` (sha256 `f6ed3c14…4e63`, recorded by the
seal receipt) and scored through the same registered scorer over the complete 1,000 rows. No extra
contact and no new exposure: those bytes were already paid for.

**N-predicted.** Zero skipped rows anywhere, so the unanswered-counted-wrong variant equals the
official number throughout. Four KU-S1c responses do not parse (three in the comparator, two in the
draft); an unparsed response is scored and counted wrong, never skipped.

## 2. Paired contrasts

`analysis.paired.paired_contrast`, delta = right − left on per-sample official scores, stratified
bootstrap N = 10,000 seed 20260903, CI90, exact sign test. Strata are the gold scenario. The
decision population for any cell this control serves is the unexposed NEW500; pooled 1,000 and the
prior-exposed DEV-500 are reported beside it.

**KU-S1c over the closed-list baseline (two contacts vs one, control turn included)**

| population | metric | closed-list | KU-S1c | delta | saves | harms | ties | p | CI90 |
|---|---|---|---|---|---|---|---|---|---|
| **unexposed 500** | **intent (scen_act)** | 73.20 | 74.80 | **+1.60** | 20 | 12 | 468 | 0.215 | **[−0.20, +3.40]** |
| unexposed 500 | scenario | 83.00 | 82.80 | −0.20 | 10 | 11 | 479 | 1 | [−1.60, +1.20] |
| unexposed 500 | action | 75.60 | 76.80 | +1.20 | 20 | 14 | 466 | 0.392 | [−0.60, +3.00] |
| unexposed 500 | slot F1 (per sample) | 14.49 | 13.84 | −0.66 | 15 | 14 | 471 | 1 | [−2.04, +0.67] |
| unexposed 500 | SLU-F1 (per sample) | 21.05 | 19.58 | −1.47 | 25 | 30 | 445 | 0.59 | [−2.90, −0.10] |
| pooled 1000 | **intent** | 71.40 | 72.90 | **+1.50** | 38 | 23 | 939 | 0.0722 | [+0.30, +2.70] |
| pooled 1000 | action | 73.90 | 75.20 | +1.30 | 39 | 26 | 935 | 0.136 | [+0.00, +2.60] |
| pooled 1000 | slot F1 | 12.96 | 13.00 | +0.04 | 29 | 24 | 947 | 0.583 | [−0.84, +0.92] |
| pooled 1000 | SLU-F1 | 19.75 | 19.07 | −0.68 | 50 | 51 | 899 | 1 | [−1.58, +0.22] |
| prior-exposed 500 | intent | 69.60 | 71.00 | +1.40 | 18 | 11 | 471 | 0.265 | [−0.20, +3.20] |

**The decomposition — what the control turn buys, and what the contact buys**

| contrast | population | metric | delta | saves | harms | CI90 |
|---|---|---|---|---|---|---|
| draft over closed-list (**the control turn**, one contact each) | pooled 1000 | intent | **+1.20** | 34 | 22 | [+0.00, +2.40] |
| draft over closed-list | unexposed 500 | intent | +1.00 | 17 | 12 | [−0.60, +2.60] |
| draft over closed-list | pooled 1000 | SLU-F1 | **−0.92** | 47 | 52 | [−1.83, −0.02] |
| draft over closed-list | unexposed 500 | SLU-F1 | −1.64 | 24 | 30 | [−3.03, −0.30] |
| **revise over draft (the second CONTACT)** | pooled 1000 | **intent** | **+0.30** | 11 | 8 | **[−0.40, +1.00]** |
| revise over draft | unexposed 500 | intent | +0.60 | 8 | 5 | [−0.60, +1.80] |
| revise over draft | pooled 1000 | **slot F1** | **+0.28** | 7 | 1 | **[+0.05, +0.53]** |
| revise over draft | unexposed 500 | slot F1 | +0.29 | 4 | **0** | [+0.07, +0.55] |
| revise over draft | pooled 1000 | SLU-F1 | +0.25 | 8 | 3 | [−0.01, +0.52] |

**Both weightings** (natural mixture / equal stratum):

| arm | intent pooled | intent NEW500 | slot F1 pooled | slot F1 NEW500 |
|---|---|---|---|---|
| closed-list | 71.40 / 71.45 | 73.20 / 74.71 | 12.96 / 12.62 | 14.49 / 13.50 |
| KU-S1c draft | 72.60 / 72.73 | 74.20 / 75.65 | 12.72 / 12.53 | 13.55 / 13.01 |
| **KU-S1c** | **72.90 / 72.94** | **74.80 / 76.17** | 13.00 / 12.77 | 13.84 / 13.26 |

The two weightings agree in sign on every intent contrast reported here.

**Realized contacts: exactly 2 per row, on every row.** `run_phases` records two phases,
`phase-draft-revise-v1:draft` and `…:revise`, each with rows 1,000 and contacts 1,000, in that
order — the stop rule `always-run-full-program` realized as two complete whole-roster waves, with no
row exiting after one contact.

## 3. Per stratum (intent, pooled 1,000)

| scenario | n | closed-list | KU-S1c | delta | saves | harms |
|---|---|---|---|---|---|---|
| alarm | 58 | 87.9 | 89.7 | +1.7 | 1 | 0 |
| audio | 30 | 73.3 | 80.0 | +6.7 | 2 | 0 |
| calendar | 61 | 65.6 | 67.2 | +1.6 | 1 | 0 |
| cooking | 37 | 59.5 | 64.9 | +5.4 | 2 | 0 |
| datetime | 61 | 82.0 | 83.6 | +1.6 | 1 | 0 |
| email | 61 | 83.6 | 88.5 | +4.9 | 3 | 0 |
| general | 61 | 34.4 | 32.8 | −1.6 | 2 | 3 |
| iot | 61 | 85.2 | 85.2 | 0.0 | 1 | 1 |
| lists | 60 | 86.7 | 85.0 | −1.7 | 0 | 1 |
| music | 51 | 84.3 | 78.4 | **−5.9** | 1 | 4 |
| news | 60 | 78.3 | 80.0 | +1.7 | 2 | 1 |
| **play** | 60 | 38.3 | 28.3 | **−10.0** | 0 | 6 |
| qa | 60 | 58.3 | 66.7 | +8.3 | 5 | 0 |
| **recommendation** | 60 | 46.7 | 58.3 | **+11.7** | 7 | 0 |
| social | 60 | 80.0 | 78.3 | −1.7 | 0 | 1 |
| takeaway | 39 | 76.9 | 69.2 | −7.7 | 0 | 3 |
| **transport** | 60 | 71.7 | 83.3 | **+11.7** | 10 | 3 |
| weather | 60 | 93.3 | 93.3 | 0.0 | 0 | 0 |

**Unlike KC-S1b, this arm harms strata as well as helping them.** Eight scenarios gain, six lose,
four are flat, and the two largest moves point in opposite directions (`transport` and
`recommendation` +11.7, `play` −10.0). That is the shape of a change with no information behind it:
it perturbs the answer rather than improving it, and the pooled +1.50 is a small net of large
cancelling movements. It is also why the NEW500 CI includes zero.

## 4. What the second contact actually did

| quantity | value |
|---|---|
| rows whose revise response is byte-identical to their own draft | **964 of 1,000 (96.4 %)** |
| rows whose answer changed at all | 36 (3.6 %) |
| rows whose (scenario, action) changed | 26 (2.6 %) |
| predicted entity mentions, draft → revise | 481 → 486 |
| rows answering no entity at all, draft → revise | 568 → 567 |
| most frequent intent moves | `audio/volume_up → play/radio` (3), `transport/query → transport/traffic` (3), `transport/query → transport/ticket` (2) |

The instruction did what it asked: told to revise or repeat, the frozen core repeated on 96 % of
rows. The 26 intent changes it did make were 11 saves and 8 harms against gold (the rest neutral),
which is the whole of the +0.30 pp.

Against the comparator the arm is far less conservative on entities than the comparator is — 486
mentions against 547, and 567 rows with no entity at all against 514. That difference belongs to the
**control turn**, not the contact: the draft phase already sits at 481 and 568.

## 5. Distance to the published brackets

Owner rule: aligned = within 3 points, or better. Every published row is the official **TEST** split
and a natural mixture; this is a scenario-stratified **DEV** roster, and no published prompt-only
SLU-F1 computed with this script exists for any audio LLM, so no like-for-like target is available
and none is claimed.

| metric | KU-S1c | published target (system, split) | delta | verdict |
|---|---|---|---|---|
| intent | 72.90 | Google/SF-ID 72.06 (weakest published pipeline, test) | **+0.84** | **aligned-better**; the degraded-model floor is cleared for the first time on this carrier |
| intent | 72.90 | ChatGPT on Whisper ASR, 10-shot 72.89 | +0.01 | **aligned** |
| intent | 72.90 | Multi-SLURP/HerMiT 78.33 (strong pipeline, test) | −5.43 | not aligned |
| intent | 72.90 | ChatGPT on oracle transcripts, 0-shot, 60 intents listed 79.25 | −6.35 | not aligned |
| intent | 72.90 | Gold/HerMiT 84.84 (oracle transcripts, test) | −11.94 | not aligned |
| scenario | 81.50 | Google/SF-ID 78.87 | +2.63 | **aligned-better** |
| action | 75.20 | Google/SF-ID 74.31 | +0.89 | **aligned-better** |
| SLU-F1 | 35.92 | Google/SF-ID 64.02 (degraded-model floor) | −28.10 | not aligned; **floor still failed** |
| SLU-F1 | 35.92 | KC-S1b 44.35 (this study, same roster) | −8.43 | the constructed schema is worth 70x this cell's contact |

Clearing the weakest published pipeline's **intent** row by 0.84 points is worth recording, but it
must be read with the caveat this whole verdict turns on: 1.20 of the 1.50 points that got there is
the control turn, the NEW500 CI includes zero, and the comparison is dev-vs-test.

## 6. KU-S1: refused before registration, and the component to fix

KU-S1 (BLEND-CL: `phase-direct-evidence-alpha-blend-v1` with `KbFacetProvider` top-5 supply at the
lock candidate's alpha 0.45 / tau 0.65 / k 5) **never flew, and is UNREAD** — neither ADMITTED nor
NULL nor HARMFUL. It was refused on a measured, structural blocker before it had an exposure row,
not on a judgment call and not by relaxing any rule. Receipt:
`containment-analysis.json` (sha256 `36267753…f9bf`), zero model, GPU, tool, embedding, network,
audio and gold contacts. Preregistration section 6 carries the full argument; the measurements:

1. **The supply cannot ride the control turn, on 100 % of rows.**
   `rails.controllers.EvidenceAgentController._dispatch` folds a `SupplyPacket.prompt_block` into
   `plan.instruction`; `rails.runner._assert_agent_control_excludes_knowledge_payloads` reads
   exactly `plan.instruction`; a `KbFacetProvider` packet renders `KnowledgeValue.content`
   **verbatim**, and **11,514 of 11,514 values are at or over 8 characters**, i.e. protected
   material by construction. A measured top-5 block is 3,224 characters carrying **19** distinct
   protected payloads. This is not a tunable rate.
2. **The substrate refuses 7.8 % of the cell's own phase-2 control turns anyway.** Under
   `slurp-kb-size-full` (23,267 protected payloads, content dimension included — the BLEND lock's
   own substrate) **78 of 1,000** rendered phase-2 control turns collide: `calendar` 57, `shopping`
   7, `politics` 4, `change song` 2, `next episode` 2, `to do list` 2, `clothing` 1, `donald trump`
   1, `jane doe` 1, `new york time` 1. Under the snapshot KU-S1c actually bound, **zero**. This
   replicates the KC-S1 deviation-1 measurement on this cell's own bytes.
3. **There is no config seam at all.** `core/flight/runtime.py`'s
   `_default_phase_program_binding` returns `supply_for_phase: None` unconditionally, and the hook
   has no caller in `src/` or `scripts/`.

**The fix, named and not done here.** The traced channel already exists and already works:
`rails.runner._agent_messages` renders every facet in `QueryState.visible_facet_ids` and every value
in `retrieved_value_ids` as typed content blocks carrying `evidence_id` / `source_uri` /
`knowledge_role`, validated by `assert_knowledge_use_binding`; the containment rule does not read it
precisely because it is traced. `EvidenceAgentController` cannot reach it — every transition it
emits is `organize` with empty `new_value_ids` — and `FlightRuntime.run_phases` cannot dispatch the
one controller that can (`rails.kb_policy.KbAlphaBlendController`), because `policy` is either
`"fixed"` or a `configs/policy/phase-*.json` program id. The enabler is: give
`EvidenceAgentController` a supply path that emits an `acquire` transition with its `RankResult` and
`FusionDecision` and advances the successor `QueryState`'s `retrieved_value_ids`, plus a
`core.base`-registered provider id `_default_phase_program_binding` can resolve. **Until that lands,
no knowledge-supplying phase cell can fly on this base — KU-S1, KU-S2 and KU-A1 alike.** That is the
single highest-value engineering item the consumption dimension has, and it is why this flight
returns one cell instead of two.

The preregistered decision rule for KU-S1 stays on the books unchanged for the day the enabler
lands. Nothing here says anything about alpha-blend: the sealed BLEND arm remains a reference, the
one-contact closed-list arm remains the SLURP comparator, and the question of what retrieval adds
over the closed-list instruction is still open.

## 7. Mechanics, cost and provenance

| item | value |
|---|---|
| run id / attempt | `SAEA-SLURP-KU-S1C-DRAFT-REVISE-DEV1000-V1` / `attempt-20260906T042946Z-44720f` |
| study commit at takeoff | `90b11039` |
| config hash / protocol hash | `f7404fbc…6957` / `8824a871…654f` |
| population | DEV-1000, 1,000 devel rows, identity `8580d199…3c84` |
| system message | 7,583 chars, sha256 `4073f79e…37db` — byte-identical to the comparator's, asserted before takeoff as the sealed M0 instruction plus a pure 1,836-char suffix |
| control turns | `probes/slurp_phase_direct.txt` 262 chars `d02f194c…f9d50`; `probes/slurp_phase_revise.txt` 477 chars `236d1ee5…c518` |
| knowledge | none supplied or rendered; snapshot `07f94807…fa65` (label/prior/speaker, 11,863 protected payloads) bound with empty bootstrap ids for the leakage rule only |
| model / geometry / decoding | frozen Qwen3-Omni-30B-A3B-Instruct GGUF Q4_K_M, llama.cpp featcache `04ccc72a`, mmproj-free over the DEV-1000 promotion receipt's packets; `-np 8 -c 65536` (the comparator's own); greedy, temperature 0, seed 20260803, max_tokens 64 |
| contacts | 2,000 of 2,100 registered; 5,769.5874 of 6,000 audio seconds; about 0.3 of 1.0 GPU-h; 0 tool, 0 embedding, 0 paid spend |
| throughput | 2,000 contacts in 1,098.0 s, 1.82 contacts/s, slot occupancy 0.497; 4,642,758 prompt and 51,200 completion tokens; 1,000 packets preprocessed in 7.5 s; 21 min takeoff to report |
| prompt fit | measured, not estimated: worst envelope **2,558** tokens against an 8,192-token slot, margin **+5,634**; pinned in the fragment and **re-rendered and reproduced at preflight** |
| seal | run manifest sha256 `1b5143aa…1a74d`, 1,000 canonical rows, 2 phases, phases file `f6ed3c14…4e63`, attempt FINALIZED |
| scoring | `core.scoring_batch`, 1 job, 0 failed, 49.4 s, no sharding |
| GPU health | 88–91 W against a 100 W enforced cap, SW power cap active, no thermal or HW slowdown |

Gold never enters the flight process: samples are built label-free from the frozen runtime view and
the adapter's `gold()` refuses outright. The held-out test split is never named, loaded or scored.

**Before the flight:** a contact-free wire check on the smoke cell (8 contacts through the fake gate
and fake transport, zero sockets, seal-and-score OK — `wire-check-ku-s1c.json`), and a four-row
end-to-end smoke (`SAEA-SLURP-KU-S1C-SMOKE-4-V1`, attempt `attempt-20260906T042625Z-26425d`, 8 of 8
contacts in 10.6 s, run manifest `20e9ab13…6056`) whose gate passed on every clause: exactly two
phases in order with rows 4 / contacts 4 each; four canonical outputs rows, one per sample, each
carrying the revise phase's response; a phases file whose sha256 the seal receipt records; and every
revise contact instruction verified row by row to be the static directive plus that sample's own
draft under the `Prior phase response` prefix. **The smoke's eight responses are a wiring proof and
are not a result.**

## 8. Deviations, defects and fixes

1. **KU-S1 was refused before registration** (section 6). It has no experiment fragment, no exposure
   row and no attempt. The flight therefore delivers one cell where the brief planned two, and the
   consumption dimension's retrieval question stays open.
2. **KU-S1c changes two things against the comparator at once** — it adds a CONTROL turn and it adds
   a CONTACT — where the ideal equal-contact control would change only the second. This was
   unavoidable: the comparator is a `policy: "fixed"` direct arm that sends no control turn at all,
   and every phase program sends one. Rather than leave it as a confound, the draft phase's own
   sealed responses were scored as a third view and the two effects are separated in section 2. Any
   future phase cell on this carrier should quote **the draft row**, not the direct baseline, when
   it wants a contact-matched, control-turn-matched comparison.
3. **The prompt-fit entry point raised a `KeyError` in its final summary print on its first run**
   (it used the KC-S1 script's percentile key names against the Audio2Tool script's `distribution`),
   *after* the receipt had already been written. Fixed and re-run so the committed script is the one
   that produced the committed receipt; zero generated tokens on either pass, and the two receipts
   differ only in timestamps.
4. **The read script had two defects, both scoring-side and both fixed before the read stood:** a
   local variable shadowed the outputs mapping, and the aggregate-metric key names in its summary
   print were wrong. No contact was spent on either; `read.json` is the output of the corrected,
   committed script.
5. **`configs/probes/manifest.json` was edited surgically rather than regenerated.** The committed
   file already carries probe entries `reproduction.manifest.PROBES` no longer holds
   (`R1-audio2tool-official-tier258-population`, `…-tier3467-population`, `SLURP-SLOT-STAGE-KC-S1`),
   so regenerating would have deleted other campaigns' rows. Reported, not repaired — the same
   deviation the closed-list verdict recorded, now one entry longer.
6. **Geometry `-np 8`, not KC-S1's `-np 4`.** This cell carries no per-sample block, its worst
   envelope is 2,558 tokens, and matching the comparator's own geometry removes a difference rather
   than adding one. It does mean KU-S1c and the KC-S1 cells are **not** geometry-matched to each
   other; each is geometry-matched to the comparator they are paired against, which is what the
   pairing requires.
7. **Throughput was 1.82 contacts/s against the comparator's 4.43** at the same geometry. The
   difference is the agent loop's per-sample OpenJiuwen workflow construction, which is serial and
   CPU-bound and cost about two minutes per phase before its first contact. Not a defect; recorded
   because it is what sizes every future two-contact SLURP cell (about 18 minutes of `run_phases`
   for 2,000 contacts).

## 9. What this authorizes

KU-S1c becomes **the equal-contact reference for the SLURP consumption dimension**: every later
two-contact SLURP cell states its delta net of it, and — per deviation 2 — quotes the draft row when
it wants a control-turn-matched comparison. Under the claim ladder this reaches **no rung at all**:
KU-S1c has no admission gate, it is a control, and its value is that other cells can be stated
against it.

It authorizes nothing else: no test contact, no superiority claim, no generalization claim, no
Stage-3 activity, and no statement whatever about the alpha-blend mechanism, which was never flown.
The next thing this dimension needs is not another cell — it is the traced-supply enabler named in
section 6.
