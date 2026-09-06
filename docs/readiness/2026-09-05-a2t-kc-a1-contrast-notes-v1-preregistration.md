# KC-A1: deterministic contrast notes on the MF-1 lighting target, with KC-A1c as its same-length control, v1 preregistration (STOPPED AT THE PROMPT FIT)

Status: DRAFTED 2026-09-05 model-free in a worktree with zero model contacts; section 3 closed 2026-09-06 by the
owner-coordinator on option B (lighting only), the two artifacts rebuilt on that decision in the main checkout,
and section 8 worked from there through the decontamination gate (PASS) to the prompt fit --
**where the cell STOPPED. The measured cost of the option-B artifact is +44 text tokens, over the binding +40
form cap it was chosen to honour, so section 3's own void clause fires and NO cell of
`configs/experiment/a2t-kc-a1-contrast-notes-4000-v1.json` has flown.** Section 3.2 records the measurement and
what it voids. Everything below section 3.2 stands as registered and is what a successor artifact re-enters at;
nothing in it was read against data.

The manipulation this document registers is the LIGHTING cluster's eight tools, not the twenty-three of the
drafted version; every table below has been re-derived from the rebuilt bytes, and the five-target notes are
retained unflown in `configs/knowledge/a2t-kc-a1/targets-v1.json`.

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
addressable mass, and the rows it recovers are concentrated on TARGET-pair misses. Under the owner's option B
(section 3) the mass this cell can address is the lighting target's own **147 rows**, not the five targets'
235; the other four targets' 88 rows are inside the metric as unmanipulated rows and are reported as such.

H2 (form, the control): the same number of added characters carrying the registry's `category` word and nothing
else does not recover them. KC-A1 minus baseline is content plus form; KC-A1c minus baseline is form; KC-A1 minus
KC-A1c is content.

The expected value is explicitly not "recover 147 rows": MF-1's separability is a lower bound on what a lexical
discriminator exists for and says nothing about whether 8 short notes can transfer it to a frozen core reading
152 tools.

## 2. The manipulation

Both arms render through the registered `evolved-artifact-v1` fill over a hash-pinned artifact under `configs/`,
so the shape of the sealed official-protocol cell is preserved byte for byte: 152 lines of
`- {signature}: {description}`, plain `tool_name` sort, no headers, ASCII only, the published system sentence and
the `## Available Tools:` wrapper unchanged, the same user turn, greedy decoding, `max_tokens` 256, raw audio
through the bf16 mmproj, build `04ccc72a`, Q4_K_M. ONLY the description column of the lighting target's 8 rows
differs.

| item | value |
|---|---|
| target spec (the stopped cell's) | `configs/knowledge/a2t-kc-a1/targets-lighting-v1.json`, sha256 `445dffc83388828faaa398e1ff81c7d45ecb422d01df850a6418a869175bfab8` (re-derived by the builder into the receipt's `target_spec.sha256`) |
| target spec (parent, retained) | `configs/knowledge/a2t-kc-a1/targets-v1.json`, sha256 `e3e8c859e6fd13fbe631ea3e0f8522654bf5459b957b716281543ed23e060378`; the flown spec's `targets` array is this file's `lighting` entry with no character changed |
| builder | `scripts/build_a2t_contrast_notes.py --targets-spec configs/knowledge/a2t-kc-a1/targets-lighting-v1.json --write`, construction rule `rails.proposer.contrast_note_records` |
| artifact receipt | `docs/checks/speech-aware-evidence-acquisition/2026-09-05-a2t-kc-a1-contrast-notes-4000-v1/artifact-receipt.json`, sha256 `a8f2170a1b89bcbd31477dd4640f94afb51cb5a24590e4133c0d1789f749b439` |
| KC-A1 artifact | `configs/knowledge/a2t-kc-a1/contrast-notes-v1.json`, sha256 `b99da99e43c813050e6df9a11bf1910e6168c744f363dae6c1b7f64df0a1763f` |
| KC-A1c artifact | `configs/knowledge/a2t-kc-a1/category-only-v1.json`, sha256 `2f34c2cf8bc5585257756b44975e36c6244d7c3e362beac1d5b01956a6736e33` |
| KC-A1 fragment | `configs/baseline/a2t-kc-a1-contrast-notes.json`, composed config hash `444e3439edfc37a37fc21be29f9b0caf2de0cf29fc06ac7eb43ef0fefd98bf15` |
| KC-A1c fragment | `configs/baseline/a2t-kc-a1c-category-only.json`, composed config hash `0766a6edae73adcd905e663cd460b60abee5456e7b94bcecc91f67f8394b160b` |
| KC-A1 rendered block | 152 lines, 16,015 characters, sha256 `ce1e521345270b9149bf45d6916fdd9a64e17293d0bae3e5ea63bf0b51f1a8fe` |
| KC-A1c rendered block | 152 lines, 16,015 characters, sha256 `ac71cef2be2f5c1750425330eaf131ac9c516a843cc782f0fd8041c1548c5545` |
| compact baseline block | 152 lines, 15,854 characters, sha256 `752dd381a02028dc7345a6ac826109bdcc879d82547a9029a43d559d0de8a605` |

The composed config hash is over model + dataset + baseline + experiment together, which is why it differs from
the drafted version's figure even where the baseline fragment's own keys are unchanged: the experiment fragment
was re-registered on option B in the same change, and again when the prompt fit's measurement was written into
it. NEITHER COMPOSITION EVER FLEW -- these are the hashes of a composition that was stopped at section 3.2, and
no manifest anywhere carries them.

Two construction rules are executable, not prose (`rails.proposer.contrast_note_records`, refusing the build
otherwise):

* **A note may say nothing the registry does not already say.** Every alphanumeric word of a note is either in the
  spec's closed 33-word function list or occurs, case-insensitively, in the registry columns of the tools of its
  OWN target. No invented device knowledge, no evaluation text.
* **The control is length-matched, never truncated.** KC-A1c's note is `"; " + category`, extended with the
  neutral filler `" tool"` while it fits and then padded with at most four trailing spaces to EXACTLY the
  treatment note's character count. A category word longer than its note is refused rather than cut, which is why
  every note is at least as long as its own category.

### 2.1 The 8 notes the stopped cell carries, their controls, and what each costs

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
| **8 tools, the cell's own** | | **161** | | |

### 2.1b The 15 notes the cell leaves out

Written, priced and retained in `configs/knowledge/a2t-kc-a1/targets-v1.json`, absent from both flown
artifacts, and reachable later per cluster or through the evolution loop. They are listed so the option-B
decision is auditable against what it declined rather than against a description of it.

| tool | note | chars | control (same length) | line |
|---|---|---:|---|---:|
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
| **15 tools, left out** | | **316** | | |

Per target, with the mass MF-1 attributes to it:

| target | in the cell | tools | added chars | estimated added tokens | MF-1 strict mass | ORG-1 residual |
|---|---|---:|---:|---:|---:|---:|
| lighting | **yes** | 8 | 161 | **40 estimated, 44 MEASURED** | 147 | 76 |
| activateRoutine | no | 5 | 98 | 25 | 44 | 44 |
| calibrateCameras | no | 4 | 96 | 24 | 16 | 21 |
| getBiometricData | no | 4 | 84 | 21 | 23 | 22 |
| castContent | no | 2 | 38 | 10 | 5 | 4 |
| all five (the rejected artifact) | no | 23 | 477 | 120 | 235 | 167 |

The cell's artifact is therefore **+161 characters, 147 addressable rows, and an ESTIMATED +40 tokens that the
prompt fit measured at +44** (section 3.2). The builder's own gate cleared both arms at the un-relaxed
`TOKEN_HEADROOM` with `token_headroom_slack_granted = 0` -- but it was counting with the estimator, and under
the tokenizer it names as the authority the treatment arm does not clear it.

## 3. The form cap -- CLOSED 2026-09-06 on option B

**The owner-coordinator's decision, verbatim:**

> Option B: KC-A1 targets the LIGHTING cluster only (147 of the 235 addressable rows), so the rendered registry
> block stays within the +40-token form cap (section 5 of the program; the five-target inline notes were priced
> at about +120 tokens and are rejected on that cap). The remaining MF-1 targets (activateRoutine,
> getBiometricData, calibrateCameras, castContent) are NOT flown here; they return per cluster later or inside
> the evolution loop. KC-A1c (the length-matched category-only control) keeps the same lighting-only tool set.

What it changed, and nothing else did: `configs/knowledge/a2t-kc-a1/targets-lighting-v1.json` was added as the
committed flown spec (the parent's `lighting` entry copied without one character altered, plus the decision
recorded in an `owner_decision` block); `scripts/build_a2t_contrast_notes.py` grew one `--targets-spec` argument
so a subset is a committed file rather than a command-line filter, with `--targets` left as the pricing filter it
was; both artifacts, both baseline fragments and the artifact receipt were regenerated from that spec; the
experiment fragment's `artifacts` block was re-registered on the new bytes. The estimated form cost falls from
+477 characters / +120 tokens to **+161 characters / +40 tokens**, the addressable mass from 235 to 147 rows,
and the manipulated line count from 23 to 8. Section 4's population, section 5's budget, section 6's analysis and
decision rule, section 7's prohibitions and section 9's deviations are untouched by the decision.

Two consequences worth stating before the flight rather than after it:

1. **The cell is now aimed exactly where ORG-1 already failed.** All 147 rows are lighting directions the grouped
   registry halved (147 to 76) while losing 3.23 pp overall. KC-A1 is the test of whether the same neighbourhood
   responds to distinguishing CONTENT at a quarter of ORG-1's prompt cost. That makes it a sharper test, not an
   easier one.
2. **The four unflown targets become a within-run negative control.** Their 88 rows sit in the same 4,000 and
   receive no note, so the per-target miss-mass table separates "the notes moved their own cluster" from "the
   prompt moved everything"; section 6's report includes all five targets for exactly that reason.

### 3.2 The measurement, and what it voids

The prompt fit (`SAEA-A2T-KC-A1-CONTRAST-NOTES-PROMPT-FIT-V1`, 2026-09-06, zero generated tokens) measured the
rendered system message of both arms on the pinned GGUF tokenizer behind the resident server, at the same
`-c 49152 -np 2` geometry and under the same chat template hash
(`45777d2e798aae1d1ce6844e69edcb23fc0c710009554711c78efab9044da2c8`) the sealed compact and grouped fits carry.

| rendering | system chars | text tokens | over compact | chars per added token |
|---|---:|---:|---:|---:|
| compact official protocol (sealed, three 2026-09-04 fits) | 16,143 | **3,581** | — | — |
| **KC-A1** contrast notes | 16,304 | **3,625** | **+44** | 3.659 |
| **KC-A1c** category-only control | 16,304 | **3,611** | **+30** | 5.367 |
| ORG-1 grouped registry (sealed, for scale) | 16,490 | 3,668 | +87 | 3.989 |

**KC-A1 is 4 tokens over the +40 cap, so the cell stops here.** Option B was taken precisely to honour that cap;
it was priced at an estimated +40 using ORG-1's measured 3.989 characters per token, and the tokenizer says these
notes cost 3.659. The estimator was not wrong by accident: it was calibrated on ORG-1's grouped block, whose
added bytes are `## DOMAIN` headers, newlines and `### ` prefixes, and short appended English phrases such as
`; kelvin only, no color` tokenize denser than that. Section 3's stated void condition -- "the decision above is
void if the measured added-token count is materially different from the +40 option B was priced at" -- is
therefore met in the only sense that matters: the number that decided between A and B has changed sign relative
to the cap.

Two further facts the measurement establishes, both of which a successor design has to answer:

1. **The control is length-matched but NOT token-matched.** The two arms are character-identical line for line
   (16,304 characters each, the same eight lines differing from the published message at the same eight indices)
   and are **14 tokens apart**, because KC-A1c's padding is repeated ` tool` and trailing spaces at 5.367 chars
   per added token. A control that costs 30 tokens does not price a treatment that costs 44; it prices 68 % of
   it. KC-A1c as built would have under-attributed the form component of any KC-A1 delta, which is the one job
   the control exists to do. Length-matching is the wrong invariant on this carrier -- **token-matching is** --
   and `rails.proposer.contrast_note_records` pads to a character count, not a token count.
2. **The machine gate agreed with the cap all along; it was reading the wrong counter.**
   `validate_candidate_artifact` passed both arms only because `scripts/build_a2t_contrast_notes.py` injects the
   character-ratio estimator as its `token_counter`. That parameter is injected exactly so "the authority is the
   serving geometry's own tokenizer", as the function's own docstring says. Under that authority the same
   artifact is REFUSED. The gate did not fail; the caller fed it an estimate.

What did NOT happen, and is not authorized by anything here: no wire check was run, no flight exposure row was
registered, no smoke and no flight were flown, KC-A1c was not reached, and no note was trimmed to fit the cap. A
note shortened to hit a token budget is no longer the artifact MF-1 priced, and trimming under measurement
pressure is how a preregistration becomes a post-hoc fit.

The decontamination gate that precedes this one PASSED and stands on its own bytes
(`SAEA-A2T-MF-KC-A1-DECONTAMINATION-V1`, zero shared 6-grams over 77,899 evaluation 6-grams), so a successor
artifact re-enters at section 8.3 rather than at 8.2 unless its note TEXT changes -- and any change to the note
text re-opens 8.2.

### 3.1 The decision as it stood before it was taken (retained for audit)

The program's section 5 caps a candidate rendering at **+40 tokens over the compact block**, and the MF-1 verdict
asks for that cap to be enforced "from round 0". The five-target artifact is **+477 characters, an estimated +120
tokens** -- three times the cap, and above ORG-1's measured +87. Reducing it further is not a matter of wording:
+40 tokens is about 160 characters, i.e. seven characters per targeted tool, which is shorter than the words the
released descriptions already contain. An inline note over 23 tools either exceeds the cap or carries nothing.

Three resolutions, and what each costs. The artifact receipt prices A and B from bytes that exist -- its
`per_target` block is the arithmetic for any subset -- while C is an estimate for a design nothing has built.
Nothing else in this document depends on which one the owner takes.

| option | what flies | measured cost | addressable mass covered |
|---|---|---|---|
| **A. ratify +120 for KC-A1** | the artifacts as committed | +477 chars, est. +120 tokens; KC-A1c prices the form exactly | 235 of 235 rows |
| **B. lighting only** | rebuild with `scripts/build_a2t_contrast_notes.py --targets lighting` | +161 chars, est. **+40 tokens -- inside the cap** | 147 of 235 rows (63 %) |
| **C. rewrite instead of append** | not built: notes would REPLACE description words rather than extend them | about +0 tokens | 235, but the arm is no longer an append and KC-A1c can no longer be length-matched by padding |

The implementer's recommendation was **A**, with **B** as the fallback if the owner wanted the cap honoured
literally: the whole point of KC-A1c is to price the form, so a form cost that is measured and controlled is
different in kind from ORG-1's, which was confounded with a 3x line-count change and never controlled. Option C
is recorded because it is the only design that satisfies the cap and the content requirement at once, and because
it is what the evolution loop's proposer rewrites will do; it is a different cell, not an edit to this one.
**The owner took B**, and the recommendation is left standing above as it was written so the record shows what
was declined.

**Token counts in this section are estimates, not measurements.** The exact count needs the pinned GGUF tokenizer
behind the resident server's `/tokenize` route, which no model-free step may start. The estimator is this
repository's own ORG-1 measurement (+347 rendered characters = +87 text tokens, i.e. 3.989 characters per token).
The prompt fit before takeoff measures the true value, and the decision above is void if the measured added-token
count is materially different from the **+40** option B was priced at.

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
cells flew; the registry block grows by about 40 tokens, which leaves the 8,192-token reserve intact against the
roster's four 654-second rows (8,515 speech tokens) with more margin than ORG-1 had. The prompt fit re-derives it.

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
above 0. If it does not, the gain is attributed to prompt FORM and the finding is that 161 characters of any text
in those 8 lines move the metric -- which would be a result about this frozen core's prompt sensitivity, not
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

1. **Close section 3** -- **DONE 2026-09-06**: the owner's choice is recorded verbatim in section 3, both
   artifacts were rebuilt from the committed lighting-only spec, both fragments were re-emitted through
   `rails.evolution.write_candidate_fragments`, the artifact receipt was regenerated, and the experiment
   fragment's `artifacts` block was re-registered on the new bytes. The cells themselves are unchanged.
2. **Decontamination row** -- **DONE 2026-09-06, PASS.** `SAEA-A2T-MF-KC-A1-DECONTAMINATION-V1`, zero contacts:
   the 4,000 rows' invocation text (9,930 strings, 77,899 distinct word 6-grams) against both artifacts. KC-A1
   contributes 74 candidate 6-grams and KC-A1c 65; the intersection is 0 in both directions, so the
   registry-exemption clause was never used. Receipt `.../decontamination/decontamination.json`, sha256
   `e5e5c7f660d0d52d80c87d113518e98480224257441620d4a0bbfe813e57a9c0`. The original instruction follows.

   Register a model-free exposure row and, under it, re-run
   `rails.proposer.validate_candidate_artifact` for both artifacts with `evaluation_query_texts` = the 4,000
   evaluation rows' query text. The builder passes an EMPTY sequence on purpose: reading that text needs a ledger
   row, and every note word is already constrained to the registry columns of its own target. A 6-gram shared
   with an evaluation query that the registry does not carry refuses the artifact.
3. **Prompt fit** -- **DONE 2026-09-06, and it STOPPED the cell.** `SAEA-A2T-KC-A1-CONTRAST-NOTES-PROMPT-FIT-V1`,
   zero generated tokens: KC-A1 +44 tokens, KC-A1c +30, against a binding +40. Section 3.2 is the record.
   `-np` was re-derived anyway and stays 2 (worst request 12,398 tokens, worst margin 12,178 against the
   8,192-token reserve, all 4,000 fit). One declared deviation, closed in the same receipt set:
   `--expect-official-system-message` cannot be passed by a cell that changes description cells on purpose, so
   the property is proved offline in `.../prompt-fit/system-message-derivation.json` (sha256
   `ed9ef42af2bc00a8fb044e0b17e0a3765cb36b744e026b2dca98d584e578b045`) -- each arm's measured
   `system_text_sha256` reproduced by two independent paths, exactly eight lines differing from the published
   message. The original instruction follows.

   Prompt fit on the resident server (zero generated tokens), for both arms, recording the measured text
   token count of each rendered system message and re-deriving `-np` against the roster's longest wav. Section 3
   is void if the measured added-token count is materially different from what the flown option was priced at.
4. **Wire check** on a clean committed tree in the MAIN checkout, then the exposure rows for both run ids, then
   the flight. The prep receipts under `wire-check-prep/` already prove the request half of both cells -- four
   payloads per cell, payload keys equal to `ARM_VISIBLE_FIELDS`, an integer `id_slot`, zero contacts, zero
   servers, the attempt aborted -- but two things they cannot prove. They carry the prep run ids and a 4-row
   split identity hash rather than the flight's, and their seal/manifest/score half is REFUSED because
   `core.bundle.git_commit` cannot read git status inside a WSL-side worktree (its `.git` file names a
   Windows-style gitdir path). Neither is a defect of the cells; both resolve in the main checkout, which is
   where ORG-1's own wire check ran.
5. **One experiment in flight.** KC-A1 first, alone; KC-A1c only after KC-A1's verdict is written and only if it
   is ADMITTED.

Items 4 and 5 were NOT reached: the cell stopped at item 3. No wire check was run in the main checkout, no flight
exposure row exists for either run id, and both `SAEA-A2T-KC-A1-CONTRAST-NOTES-V1` and
`SAEA-A2T-KC-A1C-CATEGORY-ONLY-V1` remain unregistered and unflown.

## 8.1 What a successor artifact has to clear

Recorded here so the next attempt is not re-derived from scratch, and explicitly NOT authorized by this document
-- the form cap is the owner's, and the option that replaces B is the owner's too.

1. **The budget is 40 tokens, and the measurement is the only authority.** The lighting notes as written cost 44.
   Any successor is measured on the pinned tokenizer BEFORE it is registered, not estimated: the chars-per-token
   estimator is now known to be wrong by 8 % in the unsafe direction on this family, and its calibration source
   (ORG-1's grouped block) does not resemble short appended phrases.
2. **The control has to be token-matched, not character-matched.** `rails.proposer.contrast_note_records` pads to
   a character count; on this tokenizer that leaves the control 14 tokens cheaper than its treatment. A control
   that does not cost what the treatment costs cannot price the treatment's form, which is the whole reason
   KC-A1c exists after ORG-1.
3. **Option C is the only design on the table that satisfies both.** Section 3's option C -- notes that REPLACE
   description words rather than extend them -- costs about +0 tokens and is what the evolution loop's proposer
   rewrites already do. It is a different cell with a different construction rule, and it cannot be
   length-matched by padding, so it needs its own control design.

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
