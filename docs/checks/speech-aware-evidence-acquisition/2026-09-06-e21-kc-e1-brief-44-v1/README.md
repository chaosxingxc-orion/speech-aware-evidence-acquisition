# KC-E1 / KU-E1c — prompt fit and wire check

The two preflight gates of `docs/readiness/2026-09-06-e21-kc-e1-pre-meeting-brief-v2-preregistration.md`
§8 items 2 and 3, for the Earnings-21 pre-meeting-brief cells `E21-kc-e1-brief-whole-prompt` (KC-E1)
and `E21-ku-e1c-brief-placebo` (KU-E1c). Experiment fragment
`configs/experiment/e21-kc-e1-brief-44-v1.json`. Exposure row
`SAEA-E21-KC-E1-PROMPT-FIT-V1`. Study commit **`baa36d9f`**, clean tree.

**Neither cell is authorized to fly by anything here.** The flight needs its own row
`SAEA-E21-KC-E1-BRIEF-44-V1` and the owner's own GO. What is settled is that the cell CAN fly, and
in what shape.

---

## The headline

**The whole brief does not fit the slot, and not narrowly.** Rendered through the pinned GGUF chat
template for every one of the 1,593 windows, KC-E1's uncapped text envelope reaches **6,072 flight
tokens** on call `4368670`. Adding 1,170 speech tokens (`13 × ceil(90 s)`), the 1,024-token
completion ceiling and 2 special tokens gives a worst request of **8,268 against a 6,144-token
slot** — a factor of 2.7 short of the Earnings family's `slot_tokens >= 2 × worst_required` margin
rule, and **2,124 tokens over the strict fit**. The whole-brief cell could not have been served at
all.

**`brief_max_entries_per_class` is now 12, in BOTH fragments**, and the boundary is measured from
both sides:

| cap | KC-E1 worst required | needs (×2 rule) | strict fit | margin rule |
|---:|---:|---:|---|---|
| 0 (whole brief) | 8,268 | 16,536 | **FAILS** by 2,124 | **FAILS** |
| **12 (chosen)** | **3,051** | **6,102** | passes | **PASSES**, margin 3,093, factor 2.014 |
| 16 | 3,152 | 6,304 | passes | FAILS by 160 |

12 is the LARGEST value on the preregistered grid that fits. The preregistration asks for "the
smallest `brief_max_entries_per_class` that fits"; read literally that is degenerate, because the fit
is monotone in the cap and 1 always fits. The intent is the smallest INTERVENTION — the least of the
brief thrown away — and that is what was chosen. `prompt-fit.json` carries the reasoning as a field,
not only here.

## What the cells cost, on the flight tokenizer

All 1,593 windows of both cells, rendered and measured; the text envelope is per-CALL constant and
the receipt refuses to proceed if it varies within a call.

| | KC-E1 min / median / max | KU-E1c min / median / max |
|---|---:|---:|
| **request text tokens, cap 12** | **454 / 673 / 855** | 412 / 518 / 599 |
| request text tokens, whole brief | 669 / 2,377 / 6,072 | 506 / 1,289 / 2,810 |
| **brief's own tokens per call, cap 12** | **275 / 451.5 / 676** | 228 / 310.5 / 415 |
| brief's own tokens per call, whole brief | 490 / 2,102.5 / 5,893 | 322 / 1,026 / 2,626 |
| brief's whitespace tokens per call, cap 12 | 167 / 249.5 / 351 | identical, by construction |
| brief's whitespace tokens per call, whole brief | 263 / 965 / 2,565 | identical, by construction |

The direct baseline's constant envelope is **62** tokens
(`../2026-09-04-e21-full44-direct-baseline-v1/window-fit/window-fit.json`), so the capped brief adds
a median **611** tokens to every window's prompt. The fixed per-request overhead — instruction, the
two `[evidence <id>] ` prefixes and the template scaffolding — is exactly **179** tokens for KC-E1 and
**184** for KU-E1c on every one of the 44 calls; the 5-token difference is the longer `-placebo`
transform names in the evidence ids.

**Whitespace tokens understated the real envelope by 2.37×.** The E5 provenance receipt reported the
brief at 263 to 2,565 whitespace tokens and said in writing that it would not guess the tokenizer's
count. That caution was correct to the digit: 2,565 whitespace tokens render as 5,893 model tokens.

**One discrepancy, reported rather than corrected.** This measurement reproduces the E5 receipt's
whitespace **min (263) and max (2,565)** exactly, but its median measures **965.0** where that
receipt's summary block records **969**. 969 is the 23rd of the 44 sorted values; the median of an
even-length list is the mean of the 22nd and 23rd (961 and 969). A four-token difference with no
consequence for any fit, left in place because that receipt is sealed under its own
`MANIFEST.sha256`.

## The twin is whitespace-matched, not token-matched

This is the finding the flight must carry rather than assume.

`core.class_lists.placebo_of` holds the placebo's **whitespace** token count equal to the arm's
**line by line**, and that is asserted here by measurement over all 44 calls at every cap:
`calls_with_a_line_mismatch: []` in all three passes.

On the FLIGHT tokenizer they are not equal. At cap 12 the placebo is **42 to 256 tokens shorter**
than the arm (median **161**); uncapped the gap is 163 to 3,262 (median 1,154). Placeholder nouns
(`item`, `entry`, `term`, …) cost fewer tokens than proper nouns and bracketed normalized forms. The
cap shrinks the gap sevenfold; it does not close it.

**A verdict that reads the KC-E1-versus-KU-E1c contrast as a pure content effect must say that the
arm also carried a median 161 more prompt tokens per window.**

## What the cap costs — `cap-impact.json`, model-free

The fit says the cap is legal. This says what it removes, over the real 44 calls, class by class.

| class | half | entries before | after | kept | calls truncated |
|---|---|---:|---:|---:|---:|
| Participants and roles | roster | 426 | 386 | 90.6 % | 13 / 44 |
| Organizations named in the roster | roster | 275 | 271 | 98.5 % | 2 / 44 |
| Divisions and segments named in the roster | roster | 4 | 4 | 100 % | 0 / 44 |
| Company and ticker candidates | document | 126 | 126 | 100 % | 0 / 44 |
| Product and segment candidates | document | 66 | 66 | 100 % | 0 / 44 |
| Other terms from the call's documents | document | 34,129 | 528 | 1.5 % | 44 / 44 |
| **roster half** | | **705** | **661** | **93.8 %** | |
| **document half** | | **34,321** | **720** | **2.1 %** | |

**The roster half survives nearly intact and the cell is still "the pre-meeting brief".** The
preregistration's §7 warning — "do not fly with the roster half disabled … dropping it changes the
cell from the pre-meeting brief to a keyword list" — is respected: what the slot removed is the
document half's residual-term class, which the preregistration and `core.class_lists`' own module
docstring already describe as a cue-scanned recall aid rather than an entity inventory. The one class
that pays a visible price is `Participants and roles`, which loses 40 of 426 entries on 13 calls; the
largest roster in the set has 19 participants against the cap of 12.

## Method, and its two honest limits

TEXT is measured through the resident server's own non-generative routes — `POST /apply-template`
renders the exact wire messages through the pinned GGUF chat template
(`chat_template_sha256 45777d2e…`), `POST /tokenize` counts the rendered prompt around the single
opaque media marker `GET /props` reports. **Zero tokens were generated**: 1 `/props`, 6,460
`/apply-template` and 16,088 `/tokenize` calls, no completion endpoint touched.

The wire messages are not rebuilt: they come from the REAL
`core.model.transport.LlamaServerTransport`, resolved through the REAL `TRANSPORTS` registry entry
from the REAL composed config, driven with a REAL `core.policies.build_arm_payload` payload carrying
the REAL `conec-class-lists` items, with only the HTTP sender replaced by a capture.

SPEECH is the mmproj encoder's one-second window rule `n_tokens = 13 × ceil(audio_seconds)` — the
rule the E21 window-fit receipt certified this exact geometry with, and which reproduced all 342
sealed `COST` records of `SAEA-E-005B-N10-zero` without exception.

**Limit 1 — no call audio was sent.** The media in a rendered prompt collapses to one opaque marker,
so a deterministic 0.1-second silent WAV (`sha256 2976da01…`) stands in for every window's slice.
Sending the real slices would have delivered 39.3 hours of call audio to the core for a measurement
that reads none of it; their token cost enters through the window rule instead, per window, from
their recorded durations.

**Limit 2 — the 8,192-token generic slot reserve is unreachable here and was not applied.** Other
cells of this study are read against a rule requiring 8,192 tokens of margin inside the slot. At a
6,144-token slot that exceeds the WHOLE slot, so no request of any size could meet it. The rule in
force is the one that certified this geometry: `slot_tokens >= 2 × worst_required`, at which the
sealed direct baseline sat at factor 2.721. Both readings are recorded in `prompt-fit.json`.

## The wire check — `wire-check.json`

`saea-driver smoke --dry-run` for BOTH cells on this clean committed tree, over the four shortest
`kb-construction` calls (`4384683`, `4386541`, `4387332`, `4392809`; 5,322.108 s, 61 windows each).
CONSTRUCTION only, because an evaluation call's brief is the thing under test and a dry run must not
rehearse it. **Zero model contacts, zero servers, zero sockets**; the only fakes are
`core.driver.smoke._dry_run_transport` and `core.driver.smoke._NoOpGate`.

**Request half**, read out of the sealed trace per contact: the payload key set equals
`fixed-legal-context`'s D2-frozen field set exactly; `supplied_evidence` carries exactly two items,
roster then document; `evidence_provenance` carries both relpaths, each naming its own call; every
rendered half re-hashes to its transform's output at cap 12 and the provenance records cap 12; the
OBS tiling cut the roster receipt's own window count on every call with every window naming this
run's own slice; the four stitch records cover all 61 contacted request ids exactly once; 61 `COST`
records for 61 contacts; and the `ORG` / `SUPPLY` channels independently report two evidence items
and the evidence source's own ids.

**Evidence-rail half.** A dry run's `_NoOpGate` never touches the D1 evidence rail, so it was driven
separately with a REAL `FrozenCoreGate` from each cell's own composed config:
`verify_evidence_identity` and `verify_evidence_content_identity` both PASS, and both relpaths of all
four calls route to `e21_participant_names` and `e21_contexts` respectively. That routing is the
property precondition 1's accumulate-not-assign driver fix made observable, and it is checked
explicitly.

**Seal half.** `verify_bundle` PASS; the sealed manifest's own `study_commit` equals the commit this
check verified clean, with empty `study_repo_dirt` and status `COMPLETED`; four sealed output rows;
all five declared scorers produced aggregates over the complete manifest.

**One factor on the wire.** The two cells are identical in arm, cap, contact count, windows per call
and declared scorers, and differ in `evidence_source` and the evidence ids — asserted from the two
sealed traces rather than from prose.

**Where the rendered-prompt proof lives, and why it is not here.**
`LlamaServerTransport` re-runs the full I5 session liveness, pinned-binary and socket-ownership check
on every send, so the REAL transport can only be driven beside a REAL resident server. A
contact-free check that rebuilt the messages itself would be proving its own second spelling. The
eight wire-shape propositions therefore live in `prompt-fit.json` and were asserted on all **6,460**
rendered requests — including the load-bearing one, an EQUALITY: the system message equals the two
`[evidence …]` blocks joined to the instruction, built from the evidence items the source itself
returned. That pins block order, the prefix, the separator and the instruction's position in a single
assertion.

**One pre-existing condition surfaced and left alone.** `fixed-legal-context` predates the 2026-08-15
legality doctrine's either-field rule, so every run of it — this dry run and the flight alike —
records provenance tier `UNVERIFIED` in the manifest's `legality` block with a GRANDFATHERED
declaration warning. That is a property of the arm, not of this cell. The flight receipt should carry
the warning rather than be surprised by it.

## 2026-09-07 — the twin became a TOKEN twin — `placebo-token-match/`

The prompt fit's own result 4 was that KU-E1c is a **whitespace** twin and not a **token** twin: at
cap 12 the placebo rendered 42 to 256 flight tokens shorter than KC-E1 per window, median 161,
because placeholder nouns cost fewer tokens than proper nouns and bracketed normalized forms. The
owner ruling of 2026-09-06 locks a control to its treatment on the flight tokenizer, so that gap had
to close before either cell could fly. Exposure row `SAEA-E21-KU-E1C-TOKEN-MATCH-V1`, study commit
**`a947481e`**, clean tree, one server session of 18 s at zero generated tokens.

Each twin LINE now grows by whole repeats of one neutral one-token filler, `" item"`, until the
twin's rendered PREFIX through that line measures exactly what the brief's does — the mechanism
`rails.proposer._token_matched_control` already uses for the KC-A1 control, through the same
`token_counter` seam. Prefixes rather than isolated lines, so whole-block equality is a consequence:
the prefix at the last index is the whole block.

| | before (prompt fit) | after |
|---|---|---|
| per-line whitespace tokens | equal on all 44 calls | no longer equal, and deliberately so |
| brief tokens per call, cap 12 | arm 275 / 451.5 / 676, twin 228 / 310.5 / 415 | **equal on all 44 calls**, 275 / 451.5 / 676 |
| whole request text, per window | twin −256 / −161.0 / −42 against the arm | twin **+7**, constant on all 1,593 windows |
| worst request | 3,051 against a 6,144-token slot | 3,058, margin 3,086, factor 2.009 |

**The +7 is the evidence-block header, not the brief.** The arm's two blocks name the
`conec-class-lists-roster` / `-document` transforms and the twin's name their `-placebo-tm` ones; a
twin that named the arm's transforms would be indistinguishable from it in a sealed trace, so the
two ids must differ and a differing id costs tokens. A constant 7-token surplus replaces a median
161-token deficit. A verdict should report it rather than claim a perfect match.

**The flight needs no tokenizer.** The measurement is a hash-pinned artifact,
`configs/knowledge/e21-brief-placebo-v2/pad-plan-v1.json` (sha256 `e3b494d0…d49c`, 148,435 bytes),
pinned by relpath and digest in KU-E1c's own fragment under the one new key `evidence_pad_plan`. The
evidence source `conec-class-lists-placebo-token-matched` replays the per-line repeats, and
`DerivedEvidenceRegistry` re-derives the padded twin from the same ConEC bytes with the exact
repeats inside `params_hash`. Both caps are pinned — the whole brief and the flown 12 — and the
receipt re-renders every call through the rewritten fragment to prove the source replays the bytes
that were measured.

**One factor, restated.** The cells now differ in two composed keys, `evidence_source` and
`evidence_pad_plan`. KC-E1's own baseline fragment is byte-identical to the one the fit measured,
checked with `git diff` against the fit's study commit; its COMPOSED hash reads `3ac6d436…` rather
than the `65825553…` the fit published, because the shared experiment fragment's `mandatory_slices`
note was rewritten at `fa357a24` — an edit that moves both cells' composed hashes and neither cell's
protocol.

## The wire check, re-run against the token-matched twin — `wire-check-token-matched/`

`saea-driver smoke --dry-run` for BOTH cells on the clean committed tree at **`85b64030`**, over the
same four shortest kb-construction calls, 61 contacts each, run id `SAEA-E21-KU-E1C-TOKEN-MATCH-V1`. **Zero model
contacts, zero servers, zero sockets, zero GPU seconds**; the only fakes are the two the committed
dry-run path substitutes, `core.driver.smoke._dry_run_transport` and `_NoOpGate`.

The load-bearing line for this repair is `every_half_rehashes_to_its_transform_output`: **the
derivation registry re-derives the PADDED twin from the same ConEC bytes and the same declared
params**, so the pad plan is not a side channel — it is inside `params_hash` and inside the chain the
gate re-proves. `payload_key_set_equals_the_arm_allowlist` also holds, which is the other question
the new config key raises: `evidence_pad_plan` governs the render and never reaches the wire.

Everything the first wire check proved still holds for both cells: two evidence items roster-then-
document; both relpaths in `evidence_provenance`, each naming its own call; a REAL `FrozenCoreGate`
routing all four calls' two relpaths to `e21_participant_names` and `e21_contexts` with
`verify_evidence_identity` and `verify_evidence_content_identity` PASS; the OBS tiling cutting the
roster receipt's own window count; `verify_bundle` PASS over four sealed rows with all five declared
scorers producing aggregates; and the one-factor comparison — same arm, cap, contact count, windows
per call and scorers, different `evidence_source` and different evidence ids
(`conec-class-lists-roster-placebo-tm/…` now, against the arm's `conec-class-lists-roster/…`).

The pre-existing `fixed-legal-context` GRANDFATHERED legality warning is unchanged and still not this
cell's to fix.

## Files

| file | what it holds |
|---|---|
| `prompt-fit/prompt-fit.json` | schema `saea-e21-kc-e1-prompt-fit-v1`. Three passes (whole brief, cap 12, cap 16), each cell's token distributions, per-call brief token counts, the max sample and its rendered-envelope sha256, the fit under all three readings, the cap sweep, the twin's per-line assertion and flight-token delta, the eight wire-shape propositions over 6,460 requests, and the decision |
| `prompt-fit/per-window-rows.json` | schema `saea-e21-kc-e1-prompt-fit-window-rows-v1`. Every one of the 6,460 rendered requests: window id, duration, speech tokens, text tokens, required tokens. Its sha256 is recorded inside `prompt-fit.json` |
| `prompt-fit/cap-impact.json` | schema `saea-e21-kc-e1-cap-impact-v1`. What the cap discards, class by class and call by call. Zero contacts of every kind — six pure class extractors over the same two ConEC files the evidence source reads |
| `wire-check/wire-check.json` | schema `saea-e21-kc-e1-wire-check-v1`. Both cells' dry runs, the three halves above, the sealed artifact hashes, and the one-factor comparison. Run against the WHITESPACE twin, before the token match |
| `placebo-token-match/placebo-token-match.json` | schema `saea-e21-ku-e1c-token-match-v1`. Both caps, per call and per half: the pad plan, both arms' prefix counts and totals, the per-window request-text distributions after padding, and the header residual |
| `wire-check-token-matched/wire-check.json` | schema `saea-e21-kc-e1-wire-check-v1`. The same check re-run against the TOKEN-matched twin, run id `SAEA-E21-KU-E1C-TOKEN-MATCH-V1` |
| `flight/` | **the KC-E1 flight itself** (2026-09-07, exposure row `SAEA-E21-KC-E1-BRIEF-44-V1`, attempt `attempt-20260907T171238Z-f02eef`, study commit `bfab2b16`): the receipt, the one whole-manifest `core.scoring_batch` read with its 44 per-sample rows per metric, and that directory's own `README.md`. It reports the cell's four metrics; it decides nothing |
| `flight-placebo/` | **the KU-E1c flight itself** (2026-09-07, exposure row `SAEA-E21-KU-E1C-PLACEBO-44-V1`, attempt `attempt-20260907T200859Z-251383`, study commit `60fca960`): the receipt, the one whole-manifest `core.scoring_batch` read with its per-sample rows per metric, and that directory's own `README.md`. It reports the form twin's four metrics; it decides nothing, and the pairing against `flight/` is a separate act |
| `MANIFEST.sha256` | SHA-256 of every file in this directory |

Produced by `scripts/e21_kc_e1_prompt_fit.py` (with `--cap-impact-only` for the third file),
`scripts/e21_kc_e1_wire_check.py` and `scripts/build_e21_brief_placebo_token_match.py`. Sealed run artifacts live under
`$SPEECHRL_DATA_DIR/runs/` and never enter Git.

## Boundaries

Discovery data only. No reference transcript, timestamp file, `wer_tags` sidecar or bias list was
opened to build a brief — the two ConEC context files per call are the only sources the renderer can
name, and `tests/unit/test_class_lists.py::test_the_renderer_opens_no_reference_path` proves it. The
wire check's scorers open references scoring-side after the seal, over a canned fake response, so
every score in that bundle is meaningless by construction and is labelled as such in its own ledger
cells. Earnings-22 is not contacted; no confirmatory or held-out surface is named, loaded or scored.
No superiority claim, no generalization claim, no Stage-3 activity.
