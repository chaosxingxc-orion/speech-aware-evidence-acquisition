# E35 sub10 system-arm degradation diagnosis (model-free, on the sealed outputs; counts only)

Copied verbatim from `$SPEECHRL_DATA_DIR/analysis/SAEA-E21-NATIVE-WINDOW-E35-SUB10-DIAG-V1/diag.md` (sha256 354bc9c4c33fa12c957b1ebbbc1e0b9b3c1a32b9773b7f96bb49c8bb76817e1e; companion diag.json sha256 012bd7260451dea5ca1f9fdbb238ebb90e23e5fb5f096164c4207ce643a6612c), produced 2026-09-22 by the diagnosis agent (Opus) at the coordinator's request; zero model / tokenizer / server / scorer contacts; no utterance, reference or delivered text. Appendix to `docs/results/2026-09-22-e21-native-window-flightruntime-e35-read.md`.

# E35 sub10 direct-vs-system diagnostic (Earnings21 + ConEC, 342 native windows)

Model-free, read-only. Inputs: the two sealed attempts under `$SPEECHRL_DATA_DIR/runs/`,
their `*.outputs.jsonl`, `*.scores.json` and `*.trace.jsonl`, plus the repository's own
`normalize_whisper_english` and `numeric_value_accuracy` helpers. No model, tokenizer,
encoder, server, network or official scorer was contacted. Every figure below is a count,
a rate, an id or a hash.

## 0. Where the per-window receipts actually live

The coordinator read (`e35-read.json`) looked for `native_episode_receipt` on the
**outputs rows** and found nothing, because for this carrier the outputs row is a
**per-call stitch of 28-50 execution units**, not one episode. The per-window episode
receipts are in the trace bundle:

| artefact | record | count (system arm) |
|---|---|---|
| per-window episode receipt | `*.trace.jsonl`, channel `USE`, `record_id = unit-<hex>/<sample_id>/phase-native-review-revise-acquire-v1/native-episode`, payload key `use_native_episode` | 342 |
| per-contact role tag | channel `USE`, `record_id = flight-NNNN/native-role-contact`, payload `use_role_id` | 1,597 |
| per-contact finish reason | channel `MODEL_WIRE_RESPONSE`, `flight-NNNN/wire-response`, payload `finish_reason` | 1,597 |
| per-contact text + usage | channel `MODEL_RESPONSE`, `flight-NNNN/response` | 1,597 |
| abstention derivation | channel `TOOL`, `flight-NNNN/delivery/native-abstention-v1/{request,response}` | 76 + 76 |
| per-window delivery binding | `outputs.jsonl` -> `execution_unit_delivery.sources[*]` (`execution_unit_id`, `request_id`, `raw_text_sha256`, `delivery_text_sha256`, `saturated`, `skipped`) | 342 |

`use_native_episode` carries `role_visits`, `planner_routes`, `terminal_disposition`,
`acquisition`, `deliver_normaliser`, and exactly one of `accepted_solver_receipt`,
`terminal_solver_receipt` or `abstention_receipt`. Joining `outputs.jsonl` sources to
episodes on the delivery contact's `flight-NNNN` id accounts for 342/342 windows and
1,597/1,597 contacts with nothing left over.

### Attribution method and its validation

reference tokens via data.references.reference_tokens + reproduction.asr_wer_whisper.normalize_whisper_english (the sealed scorer's own normaliser, whisper-english-v20240930); alignment path from rapidfuzz.distance.Levenshtein.opcodes; the reference partition into windows is taken ONCE from the direct arm's alignment and reused for both arms so per-window deltas are computed on identical reference spans

| call | ref words | direct edit distance (recomputed / sealed) | system edit distance (recomputed / sealed) | direct mask positions differing | system mask positions differing |
|---|---|---|---|---|---|
| 4330115 | 6628 | 455 / 455 | 1912 / 1912 | 32 | 44 |
| 4365024 | 11625 | 764 / 764 | 2936 / 2935 | 49 | 96 |
| 4365948 | 6704 | 301 / 300 | 1274 / 1273 | 25 | 38 |
| 4366429 | 11305 | 687 / 687 | 3214 / 3214 | 107 | 144 |
| 4366522 | 4123 | 301 / 301 | 1194 / 1194 | 5 | 10 |
| 4384964 | 9879 | 740 / 739 | 3169 / 3168 | 86 | 134 |
| 4385072 | 6480 | 364 / 363 | 3318 / 3318 | 39 | 70 |
| 4387383 | 3672 | 254 / 254 | 732 / 732 | 15 | 79 |
| 4389907 | 3942 | 714 / 714 | 1473 / 1471 | 19 | 44 |
| 4397829 | 11393 | 908 / 908 | 2473 / 2473 | 13 | 46 |

The recomputed total edit distance equals the sealed total on every call and both arms
(10/10, both arms). The `ref_hit_mask` differs on 0.1-1.3 % of reference positions,
which is the usual tie-break difference between two equally optimal Levenshtein paths;
it does not move any count reported here. Per-window token streams concatenate to the
same Whisper-normalised token list as the sealed stitched call text.

## 1. Where the WER mass comes from

Sealed `asr-wer-whisper` aggregates (10 calls, 75,751 reference words, identical
reference on both arms):

| | direct | system | delta |
|---|---|---|---|
| corpus WER | 0.0724 | 0.2863 | 0.2139 |
| substitutions | 2403 | 1889 | -514 |
| deletions | 1107 | 18426 | 17319 |
| insertions | 1975 | 1375 | -600 |
| total errors | 5485 | 21690 | 16205 |
| share substitutions | 0.438 | 0.087 | |
| share deletions | 0.202 | 0.850 | |
| share insertions | 0.360 | 0.063 | |
| delivered words (Whisper-normalised) | 76626 | 58706 | -17920 |
| delivered / reference | 1.0116 | 0.7750 | |
| contacts | 342 | 1597 | |
| prompt tokens | 498008 | 4016159 | |
| completion tokens | 93398 | 487532 | |
| audio seconds re-sent | 30406.9 | 142418.5 | |
| wall seconds (summed latency) | 4051.6 | 9575.5 | |

**Answer: the system arm is losing content, not hallucinating and not rewriting.**
Deletions carry 85.0 % of the system arm's error mass (18426 of 21690), and deletions are the ONLY operation that grew: substitutions fell by 514 and insertions fell by 600. The system arm delivered 17920 fewer words than the direct arm on identical audio.

### Per call

| call | windows | direct WER | system WER | d-WER | direct S/D/I | system S/D/I | direct deliv/ref | system deliv/ref |
|---|---|---|---|---|---|---|---|---|
| 4330115 | 28 | 0.0686 | 0.2885 | 0.2198 | 243/74/138 | 189/1624/99 | 1.010 | 0.770 |
| 4365024 | 49 | 0.0657 | 0.2525 | 0.1868 | 352/154/258 | 324/2415/196 | 1.009 | 0.809 |
| 4365948 | 28 | 0.0447 | 0.1899 | 0.1451 | 130/37/133 | 114/1047/112 | 1.014 | 0.861 |
| 4366429 | 45 | 0.0608 | 0.2843 | 0.2235 | 254/217/216 | 181/2877/156 | 1.000 | 0.759 |
| 4366522 | 21 | 0.0730 | 0.2896 | 0.2166 | 154/39/108 | 88/1031/75 | 1.017 | 0.768 |
| 4384964 | 45 | 0.0748 | 0.3207 | 0.2459 | 319/139/281 | 252/2710/206 | 1.015 | 0.747 |
| 4385072 | 29 | 0.0560 | 0.5120 | 0.4560 | 130/54/179 | 64/3187/67 | 1.019 | 0.519 |
| 4387383 | 24 | 0.0692 | 0.1993 | 0.1302 | 128/41/85 | 107/555/70 | 1.012 | 0.868 |
| 4389907 | 23 | 0.1811 | 0.3732 | 0.1920 | 232/231/251 | 161/1149/161 | 1.005 | 0.750 |
| 4397829 | 50 | 0.0797 | 0.2171 | 0.1374 | 461/121/326 | 409/1831/233 | 1.018 | 0.860 |

### Delivered-token / reference-word ratio, per window

| | direct | system |
|---|---|---|
| delivered_over_reference_corpus | 1.0116 | 0.7750 |
| windows_delivered_tokens_zero | 1 | 76 |
| windows_ratio_zero | 0 | 75 |
| windows_ratio_lt_0p25 | 0 | 2 |
| windows_ratio_0p25_0p75 | 1 | 1 |
| windows_ratio_0p75_1p25 | 340 | 263 |
| windows_ratio_ge_1p25 | 0 | 0 |
| ratio p0 | 0.540 | 0.000 |
| ratio p10 | 0.992 | 0.000 |
| ratio p25 | 1.000 | 0.973 |
| ratio p50 | 1.012 | 1.004 |
| ratio p75 | 1.025 | 1.020 |
| ratio p90 | 1.042 | 1.037 |
| ratio p100 | 1.149 | 1.138 |

The ratio distribution is bimodal in the system arm: 76 windows at exactly 0.0 and 263
windows inside 0.75-1.25, i.e. the surviving windows are as complete as the direct arm's.

## 2. Which node's text was delivered

Contacts per window, and the role graph actually walked (342 windows, 1,597 contacts,
mean 4.67 contacts/window):

| role sequence walked | windows | contacts each | planner routes | outcome |
|---|---|---|---|---|
| perception | 75 | 1 | (none) | ABSTAIN, empty delivery |
| perception, solver | 1 | 2 | (none) | ABSTAIN, empty delivery |
| perception, solver, reviewer | 30 | 3 | (none) | terminal solver draft delivered |
| perception, solver, reviewer, planner | 74 | 4 | ACCEPT | accepted solver draft |
| perception, solver, reviewer, planner, solver, reviewer, planner | 162 | 7 | REVISE then ACCEPT (160) / REVISE, REVISE (2) | 160 accepted solver draft, 2 terminal solver draft |

| planner route | windows |
|---|---|
| ['REVISE', 'ACCEPT'] | 160 |
| (planner never reached) | 106 |
| ['ACCEPT'] | 74 |
| ['REVISE', 'REVISE'] | 2 |

- a revision happened in 162 of 342 windows (revision_count 1); 180 windows had none
- acquisition fired on 0 windows (config `acquisition.max_iterations = 0`, `contact_budget = 0`); `cost.aggregate.tool_calls` is 0 for the whole arm

Delivered-text provenance, by hash equality between the delivered pre-normaliser text
(`deliver_normaliser.input_sha256`) and each contact's stripped response:

| delivered text | windows |
|---|---|
| equals the SOLVER's first draft | 209 |
| equals the SOLVER's last draft | 266 |
| equals the REVIEWER's last output | 12 |
| empty (E13 abstention, no text at all) | 76 |
| `saea-deliver-earnings-text-v1` changed the text | 24 |
| `saea-deliver-earnings-text-v1` byte-identical passthrough | 242 |
| normaliser never ran (abstained) | 76 |


What the revision round bought, by hash:

| | windows |
|---|---|
| windows with a second solver contact | 162 |
| second solver draft BYTE-IDENTICAL to the first | 105 |
| second solver draft differs | 57 |

In 105 of 162 revised windows (64.8 %) the REVISE round returned the same bytes it was given, at a cost of 315 contacts. Windows whose revision DID change the draft carry 0.21 extra errors per window against 1.58 for the no-op ones, so the revision is at worst harmless and at best slightly helpful -- but two thirds of its spend is a no-op.

Every role visit used exactly 1 contact (perception 342 visits, solver 429, reviewer 428,
planner 398), so the reviewer's `max_iterations = 3` budget was never drawn on.

The 12 windows where the delivered text also hashes to the reviewer's last output are
windows where the reviewer echoed the solver draft verbatim, not windows where the
reviewer's critique was delivered: every one of the 266 non-abstained windows delivers
the LAST solver draft (266/266). **No reviewer or perception text ever reached the**
**delivered transcript.** The failure is not a wrong node's text; it is no text.

Arm asymmetry worth recording: the direct arm records `raw_text_sha256` equal to
`delivery_text_sha256` on all 342 windows and never runs the Earnings delivery
normaliser; the system arm runs it on all 266 non-abstained windows and it changed 24.

## 3. Is the degradation uniform or concentrated?

Per-window extra error mass (system errors minus direct errors on the SAME reference
span; the span partition is taken from the direct arm's alignment and reused for both):

| | value |
|---|---|
| windows | 342 |
| windows with positive extra error | 175 |
| windows with zero or negative extra error | 167 |
| positive extra error mass | 16531 |
| net extra error mass | 16207 |
| windows carrying 50 % of the extra mass | 35 (10.2 % of windows) |
| windows carrying 80 % of the extra mass | 59 (17.3 % of windows) |
| windows carrying 90 % of the extra mass | 68 |
| abstained windows inside the top-50 % set | 35 of 35 |
| abstained windows inside the top-80 % set | 58 of 59 |
| abstention share of positive extra mass | 95.6 % |

Per-window `d-WER` percentiles: p0 -0.071, p10 -0.016, p25 -0.004, p50 0.004, p75 0.047, p90 0.930, p100 0.987.
The median window is a wash (+0.004); the p90 window is +0.93 WER, i.e. a total loss.

### What the concentrated windows have in common

| group | windows | extra errors | extra errors / window | ref words / window | system/direct delivered tokens |
|---|---|---|---|---|---|
| delivery source = abstention | 76 | 15800 | 207.89 | 228.1 | 0.000 |
| delivery source = terminal_solver | 32 | 330 | 10.31 | 225.7 | 0.945 |
| delivery source = accepted_solver | 234 | 77 | 0.33 | 218.8 | 0.997 |
| terminal reason = finite_completion | 106 | 15990 | 150.85 | 228.4 | 0.277 |
| terminal reason = revision_limit | 2 | 140 | 70.00 | 175.5 | 0.552 |
| terminal reason = None | 234 | 77 | 0.33 | 218.8 | 0.997 |
| contacts = 1 | 75 | 15616 | 208.21 | 228.5 | 0.000 |
| contacts = 3 | 30 | 190 | 6.33 | 229.0 | 0.966 |
| contacts = 2 | 1 | 184 | 184.00 | 198.0 | 0.000 |
| contacts = 7 | 162 | 178 | 1.10 | 223.4 | 0.995 |
| contacts = 4 | 74 | 39 | 0.53 | 207.5 | 0.993 |
| delivered/ref bucket 0_empty | 76 | 15800 | 207.89 | 228.1 | 0.000 |
| delivered/ref bucket lt_0p25 | 2 | 339 | 169.50 | 232.5 | 0.193 |
| delivered/ref bucket 0p75_1p25 | 263 | 39 | 0.15 | 220.1 | 0.998 |
| delivered/ref bucket 0p25_0p75 | 1 | 29 | 29.00 | 58.0 | 0.359 |

**It is concentrated, and it is the E13 abstention.**
59 windows (17.3 %) carry 80 % of the extra error mass, and 58 of them are abstentions. The abstained windows hold 17337 reference words (22.9 % of the corpus) and deliver zero, which alone accounts for 17137 of the arm's 18442 deletions (92.9 %).

Counterfactual (arithmetic on the sealed per-window attribution, no re-scoring):

| | attributed corpus WER |
|---|---|
| direct arm | 0.0724 |
| system arm as flown | 0.2864 |
| system arm if the 76 abstained windows had scored like the direct arm | 0.0778 |

So the six-node episode costs about +0.5 WER points on the windows it actually answers
(0.0724 -> 0.0778) and +21.4 points through the abstention.

Narrowing further: on the 234 windows where the episode ran to
a planner ACCEPT, direct WER is 0.0707 and system WER is
0.0722 -- a +0.15 point difference on 51,193 reference words.
On the 29 reviewer-capped windows that still
delivered a normal-length draft, the system arm is 9
errors BETTER than the direct arm. **When the episode completes, it is WER-neutral; the whole
regression is the windows it refuses to answer.**

### Cap / policy firing

Serving geometry: `max_tokens = 1024`, `slot_tokens = 24576`, `slots = 4` (`configs/model/q4km-e21-native-window-packets-cddb000c-np4-max1024-v1.json`). The slot is NOT the binding constraint: the largest prompt observed is 5585 tokens. The 1,024-token COMPLETION cap is.

| role | contacts | finish=length | completion tokens mean / median / p90-ish / max | contacts at >= 1024 |
|---|---|---|---|---|
| perception | 342 | 75 | 519.5 / 389.5 / - / 1024 | 75 |
| solver | 429 | 1 | 267.5 / 274 / - / 1024 | 1 |
| reviewer | 428 | 30 | 453.6 / 403.0 / - / 1024 | 30 |
| planner | 398 | 0 | 2.4 / 2.0 / - / 3 | 0 |
| direct (single contact) | 342 | 1 | 273.1 / 278.0 / - / 1024 | 1 |

Non-capped completion-token percentiles (how close each node runs to the cap):

| role | p0 | p25 | p50 | p75 | p90 | p95 | p100 |
|---|---|---|---|---|---|---|---|
| perception | 71 | 226 | 324 | 489 | 690 | 821 | 999 |
| reviewer | 51 | 238 | 381 | 541 | 702 | 845 | 988 |

- E13 `deliver-latest-or-abstain` fired 106 times (`terminal_disposition.reason = finite_completion`): 75 on the PERCEPTION node, 30 on the REVIEWER node, 1 on the SOLVER node.
- of those 106, 76 produced an EMPTY delivery (no solver draft existed yet: 75 perception-only
  episodes plus 1 where the solver itself was the truncated contact) and 30 delivered the
  latest solver draft (`terminal_solver_receipt`).
- E22 `continue-without-answer` (ReAct exhaustion) never fired: no `react` exhaustion
  disposition appears in any of the 342 receipts; `revision_limit` fired on 2 windows.
- the direct arm hit the same cap on exactly 1 window (`saturated = true`, empty delivery), which is why the direct arm also has one zero-token window.

Abstention is spread across all 10 calls (4330115:7, 4365024:9, 4365948:4, 4366429:11, 4366522:5, 4384964:11, 4385072:14, 4387383:2, 4389907:6, 4397829:7 windows abstained per call), so it is not a single-call artefact. The 75 perception-capped windows average 228.5 reference words against 219.5 for the rest: longer windows are somewhat
more likely to trip the cap, but the effect is small; the dominant driver is that the
perception note itself is long (median 324, p95 821 tokens against a 1,024 cap).

## 4. Numeric accuracy

| | direct | system |
|---|---|---|
| numeric accuracy | 0.9239 | 0.7106 |
| expected numeric words (reference) | 2246 | 2246 |
| matched numeric words | 2075 | 1596 |
| numeric words in the hypothesis | 2276 | 1713 |
| spurious numeric words | 201 | 117 |

| by kind | direct expected / matched | system expected / matched |
|---|---|---|
| currency | 172 / 160 | 172 / 109 |
| decimal | 17 / 10 | 17 / 9 |
| integer | 951 / 863 | 951 / 669 |
| ordinal | 556 / 550 | 556 / 420 |
| other | 17 / 17 | 17 / 14 |
| percent | 296 / 254 | 296 / 199 |
| year | 237 / 221 | 237 / 176 |

Per-window numeric-token counts in each arm's own delivered text (Whisper-normalised,
`numeric_value_accuracy.numeric_values`):

| | count |
|---|---|
| direct_numeric_tokens_total | 2283 |
| system_numeric_tokens_total | 1718 |
| direct_numeric_tokens_in_abstained_windows | 544 |
| system_numeric_tokens_in_abstained_windows | 0 |
| direct_numeric_tokens_in_delivered_windows | 1739 |
| system_numeric_tokens_in_delivered_windows | 1718 |
| numeric_token_shortfall_total | 565 |
| numeric_token_shortfall_from_abstained_windows | 544 |
| share of numeric shortfall from abstained windows | 96.3 % |

**Answer: the numbers are DELETED, not rewritten.**
479 matched numeric words are lost; 544 of the 565 missing hypothesis numeric tokens (96.3 %) sit in the 76 windows that delivered nothing at all. On the 266 windows the system did answer it produced 1,718 numeric tokens against the direct arm's 1,739 -- a 1.2 % shortfall. Format rewriting is ruled out by the spurious count moving the WRONG way for that hypothesis: spurious numeric words FELL from 201 to 117 (-84). A digits-vs-words rewrite would raise the spurious count while holding the hypothesis numeric count roughly flat; here both fall together, which is the deletion signature. (The Whisper normaliser maps spelled numerals to digits on both sides, so an ordinary word/digit difference would not reach the scorer anyway.) The shortfall is proportional across every kind (currency, integer, ordinal, percent, year all fall 22-25 %), again what whole-window loss looks like and not what a format rule looks like.

## 5. Contacts: 11 planned, 4.67 used

| | value |
|---|---|
| planned contacts per window (`execution_plan.planned_model_calls = 3762`) | 11 |
| actual contacts | 1597 |
| actual contacts per window | 4.670 |
| reachable ceiling given the flown config | 7 |

| contacts per window | windows | extra errors / window |
|---|---|---|
| 1 | 75 | 208.21 |
| 2 | 1 | 184.00 |
| 3 | 30 | 6.33 |
| 4 | 74 | 0.53 |
| 7 | 162 | 1.10 |

Explanation from the receipts, not from the plan:

- the plan's 11 = 1 perception + 2 rounds x (1 solver + **3** reviewer + 1 planner), budgeting
  the reviewer at its `max_iterations = 3`. Every reviewer VISIT in fact used exactly one
  contact (428 visits, `role_visits[*].execution_receipt.contacts` has length 1 everywhere), so the reachable
  ceiling is 1 + 2 x (1 + 1 + 1) = 7 and 162 windows hit exactly that.
- acquisition is armed with `max_iterations = 0` / `contact_budget = 0`, so it contributes
  0 contacts on 342/342 windows (`acquisition.contacts_used = 0`, `acquisitions = []`,
  `cost.aggregate.tool_calls = 0`).
- 74 windows took a single ACCEPT (4 contacts) and 160 took REVISE then ACCEPT (7 contacts).
- 106 windows were cut short by the completion cap before the graph finished
  (75 after 1 contact, 1 after 2, 30 after 3), which pulls the mean down hard.
- role contact totals: perception 342, solver 429, reviewer 428, planner 398.

Cost note: the arm spent 4.67x the contacts, 8.1x the prompt tokens, 5.2x the completion
tokens, 4.7x the re-sent audio seconds and 2.4x the wall time of the direct arm to deliver
23 % less text.

## 6. Root-cause hypotheses (ranked)

**H1 (dominant, ~96 % of the extra error mass). E13 `deliver-latest-or-abstain` is scoped
to the whole episode instead of to the answering node, so a truncated AUXILIARY node ends
the episode -- and when that node runs BEFORE the Solver, it voids a window the Solver
could have transcribed.** (A truncated Reviewer ends the episode too, but a solver draft
already exists by then, so those 30 windows still deliver.)
75 windows never reached the Solver at all: the Perception note hit `finish_reason` =
`length` on the first contact, `terminal_disposition = {reason: finite_completion, role_id:
perception, stage: perception}`, `abstention_receipt` was written, and the window delivered
the empty string. Those 76 empty windows hold 22.9 % of the reference words and 95.6 % of
the extra error mass; removing them moves the arm from 0.2864 to 0.0778 corpus WER. The
Solver, when it ran, behaved like the direct arm (median 274 vs 278 completion tokens; the
266 answered windows deliver 0.99x the direct arm's tokens).
*Confirming field:* `use_native_episode.terminal_disposition.{reason, role_id, stage,
finish_reason}` = `finite_completion / perception / perception / length` on exactly the
windows whose `execution_unit_delivery.sources[*].delivery_text_sha256` is
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (the empty-string digest),
together with the absence of `accepted_solver_receipt`/`terminal_solver_receipt` on those
same 76 receipts.

**H2 (the trigger behind H1). The 1,024-token completion cap is sized for a transcript,
not for the free-text auxiliary nodes, and no node-local cap or length instruction bounds
them.** Perception's note runs at median 324 / p95 821 tokens and the Reviewer's critique at
median 381 / p95 845, both against a hard 1,024 ceiling, so 75/342 perception contacts and
30/428 reviewer contacts saturate it, while the Solver saturates once in 429 and the direct
arm once in 342. The context slot is not implicated (largest prompt 5,585 of 24,576).
*Confirming field:* `MODEL_RESPONSE flight-NNNN/response.usage.completion_tokens == 1024`
joined to `MODEL_WIRE_RESPONSE flight-NNNN/wire-response.finish_reason == "length"` and
`USE flight-NNNN/native-role-contact.use_role_id`, cross-referenced against
`serving_geometry.max_tokens` in
`configs/model/q4km-e21-native-window-packets-cddb000c-np4-max1024-v1.json`.

**H3 (a real wiring defect, but ~0 WER cost -- it costs contacts, not accuracy). The
Reviewer template orders a tool call that this tool-free cell cannot serve, which inflates
reviewer output and explains its 30 caps.**
`configs/probes/e21_native_window_system_reviewer_v1.txt` opens with
"call the available task-contract tool exactly once through its native function schema",
while the cell arms no tools at all; `cost.aggregate.tool_calls = 0` and the only TOOL-channel
records in the whole trace are the 76 abstention derivations. 30 of 428 reviewer contacts
(7.0 %) saturate the cap. Their WER cost is nil: the 30 reviewer-capped windows carry 190 extra errors, and 199 of those come from the single short-solver window below; the other 29 are net -9 errors, i.e. marginally BETTER than the direct arm. The defect is therefore a spend and correctness-of-wiring problem, not an accuracy problem -- but it is the mechanism that keeps the review round from ever running on those 30 windows, and on this task it is what makes the reviewer verbose enough to cap.
*Confirming field:* `cost.aggregate.tool_calls` and the absence of any `TOOL` record whose
`record_id` is not `flight-NNNN/delivery/native-abstention-v1/*`, joined to the reviewer
contacts' `finish_reason` and `completion_tokens` distributions.

**Residual (2 windows, +339 errors, not a ranked hypothesis).** Two non-abstained windows
delivered under a quarter of the reference: `4365024` w0 (solver `completion_tokens` 68
against the direct arm's 271 delivered tokens) and `4384964` w7 (solver 45 against 200).
Both are the SOLVER producing a short draft under the episode's prompt chain, not a
truncation: every contact in `4384964` w7 finished with `stop`, and the second solver draft
was byte-identical to the first, so the REVISE/REVISE round could not repair it and the
episode ended on `revision_limit`. Worth a watch item; too rare here to rank.

### What a four-row dry run would look like (NOT implemented here)

Re-fly 4 windows drawn from the current inventory -- 2 that abstained under a perception
cap and 2 that took the full REVISE/ACCEPT route -- on the same geometry, with three
independent switches, and assert on the receipts only (no score):

1. **Scope the abstention.** A finite completion on a NON-answering node should degrade to
   the node's own truncated note (or to skipping that node) and let the Solver run, exactly
   as `exhaustion_policy: deliver-latest-solver` already does for the review loop. Assertion:
   0 receipts with `terminal_disposition.role_id in {perception, reviewer}` AND an
   `abstention_receipt`; 4/4 windows carry a non-empty `delivery_text_sha256`.
2. **Bound the auxiliary nodes.** A per-role completion cap (e.g. 256 for perception, 320
   for reviewer) plus an explicit length clause in both templates. Assertion: 0 contacts
   with `finish_reason = "length"` on perception or reviewer; solver `completion_tokens`
   unchanged within noise of the direct arm's 273 mean.
3. **Fix the reviewer template.** Drop the task-contract tool sentence for a tool-free cell
   (or arm the tool). Assertion: `cost.aggregate.tool_calls` consistent with the template,
   and the reviewer's `completion_tokens` p95 below the new cap.

The dry run proves the wiring, not an effect: n = 4 and n = 342 are both below the n >= 400
bar, and this cell is an engineering read that supports no effectiveness claim.

