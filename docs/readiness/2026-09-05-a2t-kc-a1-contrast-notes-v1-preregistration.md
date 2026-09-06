# KC-A1: deterministic contrast notes on the MF-1 targets, with KC-A1c as its same-length control, v1 preregistration (DRAFTED)

Status: DRAFTED 2026-09-05, prepared model-free in a worktree with zero model contacts. It is NOT registered:
section 3 carries one open owner decision (the form cap), and section 8 lists what the flight agent must do
between the owner GO and the first contact. No exposure row exists yet, and no cell of
`configs/experiment/a2t-kc-a1-contrast-notes-4000-v1.json` may fly before both are closed.

Program: `docs/readiness/2026-09-05-three-dimension-experiment-program.md` section 4a (KC-A1, KC-A1c) and its
section 5 form caps. Gate: `docs/readiness/2026-09-05-a2t-query-cue-audit-v1.md` (MF-1, PASSED at 235 of the
sealed 4,000-row misses against a threshold of 100). Predecessor lesson:
`docs/readiness/2026-09-05-a2t-org1-domain-grouped-registry-v1-verdict.md` (HARMFUL, -3.23 pp).

## 1. Question and hypothesis

MF-1 established three facts that make KC-A1 worth flying and bound what it can be expected to do:

1. **The cue exists in the speech.** Every one of the 22 TARGET pairs separates at 0.86 to 1.00 accuracy under a
   bag-of-words classifier on construction queries with uniform class priors, and each side's queries align with
   its own registry description at least 20 points more than with its twin's. Speakers say the thing that
   distinguishes the tools; the compact registry does not.
2. **The addressable mass is 235 rows** (278 by the component definition) inside five disjoint targets covering
   23 tools, out of 1,544 baseline misses.
3. **147 of those 235 rows are the lighting cluster, which ORG-1 already halved without gaining a point.** Under
   the grouped registry those directions fell from 147 to 76 and the flight still lost 3.23 pp, because the
   misses became same-domain ones and because a prompt-form cost of roughly three points rode along with +87
   text tokens and 465 lines against 155.

H1 (content): a per-tool contrast note that names what separates a target's tools -- built only from the
registry's own `domain`, `category`, argument names and `argument_constraints` columns -- recovers part of the
235-row mass, and the rows it recovers are concentrated on TARGET-pair misses.

H2 (form, the control): the same number of added characters carrying the registry's `category` word and nothing
else does not recover them. KC-A1 minus baseline is content plus form; KC-A1c minus baseline is form; KC-A1 minus
KC-A1c is content.

The expected value is explicitly not "recover 235 rows": MF-1's separability is a lower bound on what a lexical
discriminator exists for and says nothing about whether 23 short notes can transfer it to a frozen core reading
152 tools.

## 2. The manipulation

Both arms render through the registered `evolved-artifact-v1` fill over a hash-pinned artifact under `configs/`,
so the shape of the sealed official-protocol cell is preserved byte for byte: 152 lines of
`- {signature}: {description}`, plain `tool_name` sort, no headers, ASCII only, the published system sentence and
the `## Available Tools:` wrapper unchanged, the same user turn, greedy decoding, `max_tokens` 256, raw audio
through the bf16 mmproj, build `04ccc72a`, Q4_K_M. ONLY the description column of 23 rows differs.

| item | value |
|---|---|
| target spec | `configs/knowledge/a2t-kc-a1/targets-v1.json`, sha256 `e3e8c859e6fd13fbe631ea3e0f8522654bf5459b957b716281543ed23e060378` (re-derived by the builder into the receipt's `target_spec.sha256`) |
| builder | `scripts/build_a2t_contrast_notes.py`, construction rule `rails.proposer.contrast_note_records` |
| artifact receipt | `docs/checks/speech-aware-evidence-acquisition/2026-09-05-a2t-kc-a1-contrast-notes-4000-v1/artifact-receipt.json` |
| KC-A1 artifact | `configs/knowledge/a2t-kc-a1/contrast-notes-v1.json`, sha256 `dcf84c2a5a371b658e234d0f42c1f03a7c36c5a2c090790d44e383999647cd21` |
| KC-A1c artifact | `configs/knowledge/a2t-kc-a1/category-only-v1.json`, sha256 `664b826a9f33ae592076a420d1e6f1e2ed9e93f429c37f610114fd444c838994` |
| KC-A1 fragment | `configs/baseline/a2t-kc-a1-contrast-notes.json`, config hash `c737726722f88b3f18f6964d9753b89ad2ec44dfb79921c26b5f92cddd7cb56a` |
| KC-A1c fragment | `configs/baseline/a2t-kc-a1c-category-only.json`, config hash `71db5e99af107df69bb3f3f61242e46a79bfe5a628a76c92613608ab9eff49dd` |
| KC-A1 rendered block | 152 lines, 16,331 characters, sha256 `7a97cf549dccbc3bf7e97fa97b8f2293ec5c3e4c393f788f1ec159d6091ea0f6` |
| KC-A1c rendered block | 152 lines, 16,331 characters, sha256 `dbd141cb9b3da0dfb181a9ffa2a9e17946db49a3ec51997878e4c00dd689092a` |
| compact baseline block | 152 lines, 15,854 characters, sha256 `752dd381a02028dc7345a6ac826109bdcc879d82547a9029a43d559d0de8a605` |

Two construction rules are executable, not prose (`rails.proposer.contrast_note_records`, refusing the build
otherwise):

* **A note may say nothing the registry does not already say.** Every alphanumeric word of a note is either in the
  spec's closed 33-word function list or occurs, case-insensitively, in the registry columns of the tools of its
  OWN target. No invented device knowledge, no evaluation text.
* **The control is length-matched, never truncated.** KC-A1c's note is `"; " + category`, extended with the
  neutral filler `" tool"` while it fits and then padded with at most four trailing spaces to EXACTLY the
  treatment note's character count. A category word longer than its note is refused rather than cut, which is why
  every note is at least as long as its own category.

### 2.1 The 23 notes, their controls, and what each costs

`note` is the appended text; `chars` its length; `control` KC-A1c's length-matched text at the same count;
`line` the resulting description length (the 200-character cap is never approached -- the longest is 97).

| tool | note | chars | control (same length) | line |
|---|---|---:|---|---:|
| `getLightState` | `; returns only` | 14 | `; status tool` + 1 sp | 73 |
| `resetFilterStatus` | `; filter, not a light` | 21 | `; maintenance tool` + 3 sp | 79 |
| `setAmbientLighting` | `; smart_car cabin only` | 22 | `; media_cabin tool` + 4 sp | 85 |
| `setBrightness` | `; level only` | 12 | `; lighting` + 2 sp | 68 |
| `setColor` | `; smart_home hsb only` | 21 | `; lighting tool tool` + 1 sp | 92 |
| `setColorTemperature` | `; kelvin only, no color` | 23 | `; lighting tool tool` + 3 sp | 86 |
| `setGroupLightState` | `; a group, not one light` | 24 | `; lighting tool tool` + 4 sp | 79 |
| `setLighting` | `; one light, not a group` | 24 | `; core_control tool tool` | 97 |
| `activateRoutine` | `; routine, not a scene` | 22 | `; automation tool tool` | 65 |
| `activateScene` | `; scene, not a routine` | 22 | `; automation tool tool` | 66 |
| `setApplianceMode` | `; one appliance only` | 20 | `; appliances tool` + 3 sp | 81 |
| `setSecurityMode` | `; arming state only` | 19 | `; core_control tool` | 64 |
| `startCleaning` | `; cleaning only` | 15 | `; appliances` + 3 sp | 92 |
| `getBiometricData` | `; any type, hrv or stress` | 25 | `; health_activity tool` + 3 sp | 92 |
| `getHRV` | `; hrv period only` | 17 | `; health_activity` | 84 |
| `setHapticStrength` | `; vibration, not biometric` | 26 | `; system_connectivity tool` | 77 |
| `setRomanceMode` | `; smart_car only` | 16 | `; novelty tool` + 2 sp | 82 |
| `calibrateCameras` | `; smart_car cameras only` | 24 | `; maintenance tool tool` + 1 sp | 68 |
| `rebootDevice` | `; reboot only, not firmware` | 27 | `; maintenance tool tool` + 4 sp | 62 |
| `streamCamera` | `; live stream only` | 18 | `; core_control` + 4 sp | 68 |
| `updateFirmware` | `; firmware only, not reboot` | 27 | `; maintenance tool tool` + 4 sp | 80 |
| `castContent` | `; from a url only` | 17 | `; media tool tool` | 67 |
| `playMedia` | `; by query, not a url` | 21 | `; media tool tool` + 4 sp | 70 |

Per target, with the mass MF-1 attributes to it:

| target | tools | added chars | estimated added tokens | MF-1 strict mass | ORG-1 residual |
|---|---:|---:|---:|---:|---:|
| lighting | 8 | 161 | 40 | 147 | 76 |
| activateRoutine | 5 | 98 | 25 | 44 | 44 |
| calibrateCameras | 4 | 96 | 24 | 16 | 21 |
| getBiometricData | 4 | 84 | 21 | 23 | 22 |
| castContent | 2 | 38 | 10 | 5 | 4 |
| **all five** | **23** | **477** | **120** | **235** | **167** |

## 3. The form cap -- one OPEN owner decision, and the reason it is open

The program's section 5 caps a candidate rendering at **+40 tokens over the compact block**, and the MF-1 verdict
asks for that cap to be enforced "from round 0". The five-target artifact is **+477 characters, an estimated +120
tokens** -- three times the cap, and above ORG-1's measured +87. Reducing it further is not a matter of wording:
+40 tokens is about 160 characters, i.e. seven characters per targeted tool, which is shorter than the words the
released descriptions already contain. An inline note over 23 tools either exceeds the cap or carries nothing.

Three resolutions, and what each costs. The receipt prices all three; nothing else in this document depends on
which one the owner takes.

| option | what flies | measured cost | addressable mass covered |
|---|---|---|---|
| **A. ratify +120 for KC-A1** | the artifacts as committed | +477 chars, est. +120 tokens; KC-A1c prices the form exactly | 235 of 235 rows |
| **B. lighting only** | rebuild with `scripts/build_a2t_contrast_notes.py --targets lighting` | +161 chars, est. **+40 tokens -- inside the cap** | 147 of 235 rows (63 %) |
| **C. rewrite instead of append** | not built: notes would REPLACE description words rather than extend them | about +0 tokens | 235, but the arm is no longer an append and KC-A1c can no longer be length-matched by padding |

The implementer's recommendation is **A**, with **B** as the fallback if the owner wants the cap honoured
literally: the whole point of KC-A1c is to price the form, so a form cost that is measured and controlled is
different in kind from ORG-1's, which was confounded with a 3x line-count change and never controlled. Option C
is recorded because it is the only design that satisfies the cap and the content requirement at once, and because
it is what the evolution loop's proposer rewrites will do; it is a different cell, not an edit to this one.

**Token counts here are estimates, not measurements.** The exact count needs the pinned GGUF tokenizer behind the
resident server's `/tokenize` route, which no model-free step may start. The estimator is this repository's own
ORG-1 measurement (+347 rendered characters = +87 text tokens, i.e. 3.989 characters per token). The prompt fit
before takeoff measures the true value, and the decision above is void if the measured number is materially
different from 120.

## 4. Population and pairing

The union 4,000 roster, unchanged and NOT redrawn: `A2T-ORG1-UNION-4000`, the set-union of the three sealed
official-population rosters (tier 1 500, tiers 2/5/8 1,500, tiers 3/4/6/7 2,000), receipt
`docs/checks/speech-aware-evidence-acquisition/2026-09-05-a2t-org1-domain-grouped-roster/flight-roster-receipt.json`
(sha256 `e5a81b71e1253ff866262991f79d132b89f4bfb47e7c8a0c0cf0aa04857b8736`), split identity hash
`c0c1e7ccc0a9d923e51e86be11c4aedb760a2b91c8ab166305a6877c64496ad4`, flight split identity hash
`ed8946ddf99f9e898af1c8cb94932c538165cd591c2cff3021321749e52103d6`, D1 media supplement
`docs/receipts/artifacts/d1-a2t-org1-union-4000.json`. Strata: tier (500 each over all eight) and domain
(smart_home 2,792, wearables 857, smart_car 351). Split role `discovery`; every row was already exposed on
2026-09-04 and again under ORG-1 on 2026-09-05.

Pairing: every row is paired with its OWN sealed official-protocol output (pooled baseline 61.40 %, equal-domain
68.11 %). Nothing is re-flown on the baseline side, because greedy decoding is not bitwise reproducible across
batch shapes on this runtime. When KC-A1c flies, it is additionally paired row for row against KC-A1.

## 5. Budget (ExecutionPlan), per cell

Two run ids, two exposure rows: `SAEA-A2T-KC-A1-CONTRAST-NOTES-V1` (cell `KC-A1-contrast-raw`) and
`SAEA-A2T-KC-A1C-CATEGORY-ONLY-V1` (cell `KC-A1c-category-raw`).

| field | planned per cell | registered ceiling per cell | basis |
|---|---:|---:|---|
| model calls | 4,008 | 4,200 | 4,000 rows x 1 contact + 8 canaries |
| speech audio seconds | 23,419 | 24,600 | 23,418.083083 s for one pass, rounded up |
| GPU hours | 0.75 | 1.0 | ORG-1 flew this roster and geometry at 0.78-0.83 s per call at two slots, about 0.81 h |
| paid API spend | 0 | 0 | |

Serving geometry `-c 49152 -np 2` (24,576 tokens per slot), the geometry the tier-1, tiers-3/4/6/7 and ORG-1
cells flew; the registry block grows by about 120 tokens, which leaves the 8,192-token reserve intact against the
roster's four 654-second rows (8,515 speech tokens). The prompt fit re-derives it.

## 6. Analysis and decision (fixed before takeoff)

Analysis: `scripts/a2t_org1_domain_grouped_analysis.py`, generalized to N arms rather than forked
(`--arm cell_id=run_id[:attempt]`, repeatable; `--rule kc-a1`). Every arm is paired against the same sealed
baseline rows, read once; each arm after the first is additionally paired against the first. Statistics are the
program's: `analysis.paired.paired_contrast`, 10,000 replicates stratified by tier, seed 20260903, CI90, exact
sign test, saves/harms/ties; natural-mixture and equal-domain weightings; per tier with the published column
beside every tier; per domain and per tier x domain.

Primary: pooled official tool accuracy (`a2t-toolcall-official`), KC-A1 minus the sealed official-protocol
baseline, over 4,000 rows.

- **ADMITTED**: the pooled CI90 lower bound is above 0, both weightings agree in sign, AND at least half of the
  corrected rows carried a baseline miss whose gold and predicted tool both sit inside one MF-1 target
  (`target_pair_share_of_the_gain >= 0.5`, computed from the audit receipt, never asserted). KC-A1c then flies.
- **NULL**: the CI90 includes 0, or the weightings disagree, or the target-pair share is below 0.5. Program
  section 4a routes a NULL with separability >= 0.80 to EVO-A1 from the official baseline; KC-A1c does not fly.
- **HARMFUL**: the CI90 upper bound is below 0. KC-A1 is dropped with its form/content attribution recorded.

**The control clause.** An ADMITTED KC-A1 is credited as a CONTENT effect only if KC-A1c does not reach a
comparable delta, preregistered as: the KC-A1-minus-KC-A1c contrast on the same 4,000 rows has a CI90 lower bound
above 0. If it does not, the gain is attributed to prompt FORM and the finding is that 477 characters of any text
in those 23 lines move the metric -- which would be a result about this frozen core's prompt sensitivity, not
about knowledge.

Reported beside the decision, every time: the per-stratum table with the paper column; the five targets' own miss
mass before and after; the named confusion-pair table before and after; the miss-class table; exact match,
parameter F1 (macro and micro), `a2t-toolcall-v2` and parse rate as paired deltas; realized calls, tokens and
latency. The paper column is a ceiling reference and no gate is set relative to it.

## 7. What this preregistration does not authorize

No test contact; no fresh roster (`A2T-FRESH-800` stays reserved for rung 3); no rollouts; no second contact; no
retrieval; no change to the direct baseline; no Q8_0; no edit to an artifact after its fragment was emitted (the
fill re-hashes the bytes and refuses); no superiority, generality or Stage-3 claim. At most one recovery
re-registration per run id. KC-A1c flies only on an ADMITTED KC-A1.

## 8. What the flight agent must do between the owner GO and the first contact

1. **Close section 3**: record the owner's choice of A, B or C verbatim. Option B requires rebuilding the two
   artifacts with `--targets lighting` and re-emitting both fragments; the experiment fragment's cells are
   otherwise unchanged.
2. **Decontamination row.** Register a model-free exposure row and, under it, re-run
   `rails.proposer.validate_candidate_artifact` for both artifacts with `evaluation_query_texts` = the 4,000
   evaluation rows' query text. The builder passes an EMPTY sequence on purpose: reading that text needs a ledger
   row, and every note word is already constrained to the registry columns of its own target. A 6-gram shared
   with an evaluation query that the registry does not carry refuses the artifact.
3. **Prompt fit** on the resident server (zero generated tokens), for both arms, recording the measured text
   token count of each rendered system message and re-deriving `-np` against the roster's longest wav. Section 3
   is void if the measured added-token count is materially different from the estimated 120.
4. **Wire check** on a clean committed tree (the prep receipts under `wire-check-prep/` prove the wiring but not
   the flight's own run ids), then the exposure rows for both run ids, then the flight.
5. **One experiment in flight.** KC-A1 first, alone; KC-A1c only after KC-A1's verdict is written and only if it
   is ADMITTED.

## 9. Deviations and limits carried from the parents

1. **Quantization and runtime**: Q4_K_M on llama.cpp `04ccc72a` instead of the release's bf16 checkpoint.
   Identical on both sides of every pairing, so it cannot bias a delta.
2. **The baseline is sealed bytes, not a re-flight**, and 1,500 of the 4,000 baseline rows flew at `-np 3` while
   the rest flew at `-np 2`. ORG-1 showed both halves move together; the same split applies here.
3. **The four 654-second rows** are the release's synthesis defect and are kept, because the sealed outputs they
   are paired against were produced on exactly those rows.
4. **Lexical ceiling.** MF-1's separability is a lower bound on the cue available to the frozen core and an upper
   bound only on lexical discriminators; a note cannot transfer a cue the transcript never carried.
5. **The floor.** 32 rows of label noise and 186 rows on pairs whose second tool the corpus almost never uses as
   gold are outside any note's reach, as MF-1 recorded.
