# KC-A1: deterministic contrast notes on the MF-1 lighting target, with KC-A1c as its token-matched form twin, v1 preregistration

Status: DRAFTED 2026-09-05 model-free in a worktree with zero model contacts; section 3 closed 2026-09-06 by the
owner-coordinator on option B (lighting only), the two artifacts rebuilt on that decision in the main checkout,
and section 8 worked from there through the decontamination gate (PASS) to the prompt fit -- **where the first
attempt stopped, at +44 measured text tokens against a then-binding +40 cap (section 3.2).** The owner ruling of
2026-09-06 (section 3.3) reopened the cell: the cap is advisory, the eight notes fly unaltered at +44, and the
control is rebuilt TOKEN-matched rather than character-matched. Sections 3.3 and 6 carry the ruling; everything
else stands as registered and nothing in it was read against data.

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

H2 (form, the control): the same number of added TOKENS carrying the registry's `category` word and nothing
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
| target spec (the flown cell's) | `configs/knowledge/a2t-kc-a1/targets-lighting-v1.json`, sha256 `854cf7ea40023cb089f70091c0a09c80ec751a542a60f6f3e6b523b1d44c6e63` (re-derived by the builder into the receipt's `target_spec.sha256`) |
| target spec (parent, retained) | `configs/knowledge/a2t-kc-a1/targets-v1.json`, sha256 `6552fb78161c0fc88a6f9955f7fcdc514c666836bdaf6ec143a2baf4566c9d4a`; the flown spec's `targets` array is this file's `lighting` entry with no character changed |
| builder | `scripts/build_a2t_contrast_notes.py --targets-spec configs/knowledge/a2t-kc-a1/targets-lighting-v1.json --tokenizer-url http://127.0.0.1:8080 --write`, construction rule `rails.proposer.contrast_note_records` (the tokenizer url is mandatory for `--write`) |
| artifact receipt | `docs/checks/speech-aware-evidence-acquisition/2026-09-05-a2t-kc-a1-contrast-notes-4000-v1/artifact-receipt.json`, sha256 `19fe39a243e240350122061efcb51c325551b42779ac74c66e7caea267b0d14b` |
| KC-A1 artifact | `configs/knowledge/a2t-kc-a1/contrast-notes-v1.json`, sha256 `b99da99e43c813050e6df9a11bf1910e6168c744f363dae6c1b7f64df0a1763f` |
| KC-A1c artifact | `configs/knowledge/a2t-kc-a1/category-only-v1.json`, sha256 `ef99c956b274717975a84e7276554b04c9c1656646f692a9a17d66b46ce075f6` |
| KC-A1 fragment | `configs/baseline/a2t-kc-a1-contrast-notes.json`, composed config hash `738312c1b1f965d0ed803339e5f7140c23cac5f5f5b8d992810a5c055e0bcd64` |
| KC-A1c fragment | `configs/baseline/a2t-kc-a1c-category-only.json`, composed config hash `5d6509ecd82d80d75b64dcececf5603260fcf64b63f6064f1e79a2c1d8726f8a` |
| KC-A1 rendered block | 152 lines, 16,015 characters, 3,541 measured tokens, sha256 `ce1e521345270b9149bf45d6916fdd9a64e17293d0bae3e5ea63bf0b51f1a8fe` |
| KC-A1c rendered block | 152 lines, 16,067 characters, 3,541 measured tokens, sha256 `7736bdb2f4a3625f015dd0a75b701c9c285aa49b3b19b4a75a1d2ce225eea64f` |
| compact baseline block | 152 lines, 15,854 characters, 3,497 measured tokens, sha256 `752dd381a02028dc7345a6ac826109bdcc879d82547a9029a43d559d0de8a605` |

The composed config hash is over model + dataset + baseline + experiment together, which is why it differs from
the drafted version's figure even where the baseline fragment's own keys are unchanged: the experiment fragment
was re-registered on option B in the same change, again when the first prompt fit's measurement was written into
it, and again on the 2026-09-06 owner ruling. THESE are the compositions that fly; the earlier ones never did.

Two construction rules are executable, not prose (`rails.proposer.contrast_note_records`, refusing the build
otherwise):

* **A note may say nothing the registry does not already say.** Every alphanumeric word of a note is either in the
  spec's closed 33-word function list or occurs, case-insensitively, in the registry columns of the tools of its
  OWN target. No invented device knowledge, no evaluation text.
* **The control is TOKEN-matched, never truncated** (2026-09-06 owner ruling; the character match it replaces is
  recorded in section 3.2 as the defect that voided it). KC-A1c's note is `"; " + category`, grown by whole
  `" tool"` tokens until the rendered description cell measures EXACTLY the treatment cell's token count on the
  flight tokenizer, and a control that cannot land on that count exactly is refused rather than approximated. A
  category that already costs more tokens than its note is refused rather than cut.

### 2.1 The 8 notes the cell flies, their token-matched controls, and what each costs

`note` is the appended text; `+tok` the tokens it adds to that line on the flight tokenizer; `control` KC-A1c's
text at the SAME token count; `line` the resulting description length (the 200-character cap is never approached
-- the longest is 97 on KC-A1 and 107 on KC-A1c). Every figure is measured, not estimated.

| tool | note | chars | +tok | control (same tokens) | +tok |
|---|---|---:|---:|---|---:|
| `getLightState` | `; returns only` | 14 | 2 | `; status tool` | 2 |
| `resetFilterStatus` | `; filter, not a light` | 21 | 5 | `; maintenance tool tool tool tool` | 5 |
| `setAmbientLighting` | `; smart_car cabin only` | 22 | 4 | `; media_cabin tool` | 4 |
| `setBrightness` | `; level only` | 12 | 2 | `; lighting tool` | 2 |
| `setColor` | `; smart_home hsb only` | 21 | 5 | `; lighting tool tool tool tool` | 5 |
| `setColorTemperature` | `; kelvin only, no color` | 23 | 6 | `; lighting tool tool tool tool tool` | 6 |
| `setGroupLightState` | `; a group, not one light` | 24 | 6 | `; lighting tool tool tool tool tool` | 6 |
| `setLighting` | `; one light, not a group` | 24 | 6 | `; core_control tool tool tool tool` | 6 |
| **8 tools, the cell's own** | | **161** | **36** | **213 chars** | **36** |

The per-line sum (36) is smaller than the whole-block delta (44) for both arms alike: a line measured on its own
loses the merge its final token makes with the following newline inside the block, which costs one token per
changed line. The arms move together at both levels, which is what the control has to do.

### 2.1b The 15 notes the cell leaves out

Their controls below are the RETIRED character-matched ones, priced before the 2026-09-06 ruling and never built
on a tokenizer; a later per-cluster cell rebuilds them token-matched. Written, priced and retained in `configs/knowledge/a2t-kc-a1/targets-v1.json`, absent from both flown
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

### 3.3 The owner ruling that closes section 3 (2026-09-06)

**Verbatim:**

> OWNER RULING 2026-09-06: the +40 token cap is NOT a gate; the invariant the program locks is the FINAL SCORE
> against a form-matched control, not a token count.
>
> 1. Artifact: fly the ORIGINAL eight-note lighting artifact exactly as measured at +44 tokens in attempt 1.
>    Drop NO note. If you already added the greedy budget to `scripts/build_a2t_contrast_notes.py`, keep the
>    tokenizer-backed counter and make the budget optional (`--token-budget` report-only for this cell); do not
>    delete working code.
> 2. Control KC-A1c: TOKEN-matched to the treatment per line on the server `/tokenize` (the character-matched
>    +30 control is void). Whole-block token equality (+44 = +44) asserted by measurement in the receipt.
> 3. Both cells fly, sequentially, under the one experiment id: KC-A1 first, then KC-A1c REGARDLESS of KC-A1's
>    verdict (the control is the attribution instrument; the "A1c only if admitted" clause is withdrawn). Each
>    cell has its own exposure row, wire check and scoring; one verdict document reads both: total effect
>    = A1 - baseline, form effect = A1c - baseline, content effect = A1 - A1c, each with CI90, saves/harms, per
>    tier with the paper column, per domain, both weightings.
> 4. Documents, before the wire check: close preregistration section 3 with this ruling verbatim ("the cap is
>    advisory; the form-matched control measures form cost; both cells fly"), amend section 6 with the three-way
>    decomposition, and replace the program's section-5 "+40 tokens over compact" wording -- the token delta is
>    REPORTED (measured on the flight tokenizer, min/median/p95/max per arm when it varies per row); every
>    content artifact carries a token- and structure-matched control ("form twin"); the prompt-fit reserve check
>    is the only hard bound; for the evolution loop the +40 stays as a SEARCH budget relative to the incumbent (a
>    validator constraint that keeps the proposer from inflating descriptions), not a claim gate, and the loop's
>    placebo family is the form twin of the incumbent.

**What it changed in this repository, and nothing else did.** The eight notes, the target list and the treatment
artifact are byte-identical to what section 3.2 measured (`configs/knowledge/a2t-kc-a1/contrast-notes-v1.json`,
sha256 `b99da99e...`, the bytes the decontamination gate passed), so the manipulation MF-1 priced is the
manipulation that flies. `rails.proposer.contrast_note_records` gained an injected `token_counter`: with one, the
category-only control is grown by whole ` tool` tokens until the rendered description cell measures EXACTLY the
treatment cell's token count, and a control that cannot land on that count is refused rather than approximated.
`scripts/build_a2t_contrast_notes.py` gained `--tokenizer-url` (mandatory for `--write`; the chars-per-token
estimator may no longer register an artifact), a report-only `--token-budget`, and an assertion of whole-block
token equality between the arms before it writes anything. Only the control artifact changed
(`category-only-v1.json`, sha256 `ef99c956...`), with its baseline fragment and the experiment fragment's
`artifacts` block re-registered on the new bytes.

**What `SAEA-A2T-KC-A1-TOKEN-MATCH-V1` measured on the same pinned tokenizer, template
`45777d2e...`, at the same `-c 49152 -np 2` geometry:**

| rendering | system chars | text tokens | over compact | block tokens | block over compact |
|---|---:|---:|---:|---:|---:|
| compact official protocol (sealed, three 2026-09-04 fits) | 16,143 | **3,581** | — | 3,497 | — |
| **KC-A1** contrast notes (unchanged bytes) | 16,304 | **3,625** | **+44** | 3,541 | +44 |
| **KC-A1c** category-only form twin (rebuilt) | 16,356 | **3,625** | **+44** | 3,541 | +44 |

Token symmetry is exact: the arms differ by 0 tokens and by 52 characters, which is the point -- the byte counts
are free to differ precisely because the token counts do not. Per line, every one of the eight changed lines
costs the same added tokens in both arms (2, 5, 4, 2, 5, 6, 6, 6 for `getLightState`, `resetFilterStatus`,
`setAmbientLighting`, `setBrightness`, `setColor`, `setColorTemperature`, `setGroupLightState`, `setLighting`).
`-np` is re-derived and stays 2 (worst request 12,398 tokens on `tier1_direct:003943`, worst served-slot margin
12,178 against the 8,192-token reserve, all 4,000 fit). The declared deviation of section 8.3 is closed the same
way as before: `--expect-official-system-message` is not passed and
`.../prompt-fit-v2/system-message-derivation.json` proves the property offline, PASS on both arms.

Two rules carry forward beyond this cell, and both are now in program section 5: **measure on the flight
tokenizer before registering an artifact**, and **match a control on tokens, not on characters**.

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
  (`target_pair_share_of_the_gain >= 0.5`, computed from the audit receipt, never asserted).
- **NULL**: the CI90 includes 0, or the weightings disagree, or the target-pair share is below 0.5. Program
  section 4a routes a NULL with separability >= 0.80 to EVO-A1 from the official baseline.
- **HARMFUL**: the CI90 upper bound is below 0. KC-A1 is dropped with its form/content attribution recorded.

**The three-way decomposition (amended 2026-09-06 by the owner ruling of section 3.3).** KC-A1c flies after
KC-A1 **regardless of KC-A1's verdict**: the control is the attribution instrument, and it is needed most when
the treatment is null or harmful, which is exactly the case ORG-1 could not resolve. The earlier clause "KC-A1c
then flies" / "KC-A1c does not fly" is withdrawn. One verdict document reads both arms and reports three
contrasts over the same 4,000 rows, each with CI90, saves/harms/ties, the exact sign test, per tier with the
paper column beside every tier, per domain, and under natural-mixture AND equal-domain weighting:

| contrast | definition | what it measures |
|---|---|---|
| **total effect** | KC-A1 minus the sealed official-protocol baseline | content plus form |
| **form effect** | KC-A1c minus the same sealed baseline | 44 tokens of contrast-free text in the same 8 lines |
| **content effect** | KC-A1 minus KC-A1c, paired row for row | what the contrast says, at zero form difference |

KC-A1 is credited as a CONTENT effect only when the content contrast has a CI90 lower bound above 0. If it does
not, the movement is attributed to prompt FORM, and the finding is that 44 tokens of any text in those 8 lines
move the metric -- a result about this frozen core's prompt sensitivity, not about knowledge. Because the two
arms are token-matched (section 3.3, exact), the form effect is priced by a flown arm rather than assumed from a
cap, which is what the 2026-09-06 ruling replaced the cap with.

Reported beside the decision, every time: the per-stratum table with the paper column; the five targets' own miss
mass before and after; the named confusion-pair table before and after; the miss-class table; exact match,
parameter F1 (macro and micro), `a2t-toolcall-v2` and parse rate as paired deltas; realized calls, tokens and
latency. The paper column is a ceiling reference and no gate is set relative to it.

## 7. What this preregistration does not authorize

No test contact; no fresh roster (`A2T-FRESH-800` stays reserved for rung 3); no rollouts; no second contact; no
retrieval; no change to the direct baseline; no Q8_0; no edit to an artifact after its fragment was emitted (the
fill re-hashes the bytes and refuses); no superiority, generality or Stage-3 claim. At most one recovery
re-registration per run id. KC-A1c flies after KC-A1 regardless of its verdict (section 3.3, 2026-09-06
owner ruling); the earlier "only on an ADMITTED KC-A1" clause is withdrawn.

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
3. **Prompt fit** -- **DONE 2026-09-06 twice.** The first pass STOPPED the cell and the second, after the
   owner ruling, cleared it: `SAEA-A2T-KC-A1-TOKEN-MATCH-V1` measured both arms at 3,625 text tokens, +44 each,
   token symmetry exact, receipts under `.../prompt-fit-v2/` (derivation PASS). The first pass is recorded as
   it stood: `SAEA-A2T-KC-A1-CONTRAST-NOTES-PROMPT-FIT-V1`,
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
5. **One experiment in flight.** KC-A1 first, alone and sealed; then KC-A1c, once KC-A1 is scored -- and
   regardless of what KC-A1's verdict says, per the 2026-09-06 owner ruling of section 3.3. One verdict
   document reads both arms and reports section 6's three-way decomposition.

Items 1 to 3 were re-done on 2026-09-06 under the owner ruling and under one measurement row,
`SAEA-A2T-KC-A1-TOKEN-MATCH-V1`: the control was rebuilt token-matched on the flight tokenizer (the treatment
bytes are unchanged and keep their decontamination PASS), both arms were re-measured at +44 tokens each, and
the derivation proof was regenerated. The rebuilt CONTROL bytes take their own decontamination row before the
wire check. Items 4 and 5 follow from there.

## 8.1 What a successor artifact has to clear -- ANSWERED 2026-09-06

Written when the cell was stopped, before the owner ruled. Items 1 and 2 were adopted and are now executable
(`--tokenizer-url` mandatory for `--write`; `contrast_note_records` token-matches an injected counter); item 3
was not needed, because the ruling made the cap advisory rather than demanding a design that fits it. Option C
stays on the table as a different cell. The text is kept as written.

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
