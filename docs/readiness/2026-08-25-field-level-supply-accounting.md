# FIELD-LEVEL SUPPLY ACCOUNTING — what the injected supply is made of, and what each part costs
# (2026-08-25)

**Exposure row:** `SAEA-SN-MF-FIELD-LEVEL-SUPPLY-ACCOUNTING`, registered `834c36dd` BEFORE any
computation.
**Module:** `src/speech_aware_evidence_acquisition/analysis/field_level_supply_accounting.py`.
**Receipt:**
`docs/checks/speech-aware-evidence-acquisition/2026-08-25-field-level-supply-accounting/accounting-report.json`,
sha256 `ca973be873318deb6029f183045ac4074653dd1b5943c9113fb78d40766de4c6`.
**Spend exactly as registered:** 0 frozen-core contacts, 0 embedding-tool contacts, 0 tokenizer
contacts, 0 HTTP or socket requests, 0 audio seconds, 0.0 GPU hours, 0 new dependencies.
`analysis.dev100_reviewer_audit.arm_offline_guard()` was armed before the first input was opened and
recorded **0 outbound connection attempts against zero targets**. The resident np2 llama-server
(pid 38623, port 8090) was not contacted, probed, reconfigured or stopped. Wall 163.3 s. No knob
changed; no line under `rails/` touched; new code only under `analysis/`.

---

## 0. What this document is, and what it is not

The supplied `ValueBundle` content on both carriers is a **fixed composite string assembled at
KB-construction time and injected verbatim**. Nothing at use time selects which fields of it are
relevant. Two landed reads have measured what the supply *does*. Neither priced it. This document
prices it, field by field, and does nothing else.

> **ACCOUNTING ONLY.** This document does **not** propose or evaluate a field-selection policy and
> changes no rendering. It produces the accounting a later, **separately registered** design step
> would use. See the HARD STOP (§9).

---

## 1. CORRECTION — a premise of the registered row is superseded

The exposure row `SAEA-SN-MF-FIELD-LEVEL-SUPPLY-ACCOUNTING` (ledger commit `834c36dd`) is
append-only and is **left exactly as registered**. Its question (4) contains this sentence, which is
**superseded**:

> "**(4) DEAD WEIGHT:** each field group is classified EXTRACTION-oriented, MATCHING-oriented or
> FORM-oriented … and the fraction of the injected token budget that is extraction-oriented — i.e.
> currently paying for **a channel the landed read measured at ZERO effect** — is computed per
> carrier"

**Successor:** `docs/readiness/2026-08-25-extraction-conditioned-on-dispatch.md` (commit
`6c6ec719`, receipt sha256
`7662fbc381e6994f3c71422154a0facfc86c0e99b656cf91670577036a337525`). The earlier
matching-versus-extraction read conditioned on **matching** but never on whether the trajectory
**received supply**. A retained trajectory stops at contact 0 and is handed no evidence at all. Its
SLURP unexposed "both matched" cell holds 273 samples of which only **3 were dispatched** (98.90 %
unsupplied); its A2T "both matched" cell holds 60 of which **0 were dispatched**. Where the supply
*is* delivered it works: SLURP dispatched (n = 163) official `slu_f1` **+13.7570 pts**, CI90
[+8.8840, +18.6695], macro `slot_f1_exact_mean` **+9.4391 pts**, CI90 [+4.3558, +14.5194];
Audio2Tool dispatched (n = 15) slot micro-F1 **+12.1212 pts**. Where it was not delivered A2T is
**−3.0250 pts** with a CI90 excluding zero, on trajectories that received nothing.

**Consequence for this document.** Question (4) is answered as **cost per channel against
delivery**, never as dead weight. **No extraction-oriented field is written off anywhere below.**
The correction to `2026-08-25-matching-vs-extraction-read.md` itself is already carried by its own
successor (§11 of `6c6ec719`) and is not duplicated here.

---

## 2. FIELD ENUMERATION — read off the builders, not assumed

### 2.1 Audio2Tool — twelve field groups

Source: `rails/knowledge_build_a2t.py` (sha256
`b0aae99763423bba673cbb72c1c702fdd5d42c55cd46fc46222c74b79ffe88d2`), the `content_text` f-string in
`build_a2t_key_value_layer`, plus the optionally appended prior representation.

| # | field group | builder line | orientation | placeholder literal |
|---|---|---|---|---|
| 1 | `A2T-EXEMPLAR-UTTERANCE` | `Invocation exemplar: "{row.text}"` | MATCHING | — |
| 2 | `A2T-CALL-RENDER` | `-> tool call: {row.call_render}.` | FORM | — |
| 3 | `A2T-TOOL-IDENTITY` | `Tool '{tool}' (domain={domain}, category={category});` | MATCHING | — |
| 4 | `A2T-REGISTRY-SIGNATURE` | `registry signature {signature or 'unavailable'};` | FORM *(mixed)* | `unavailable` |
| 5 | `A2T-DESCRIPTION` | `{description or 'no registry description'}` | MATCHING | `no registry description` |
| 6 | `A2T-ARG-DEFAULTS` | `Argument defaults: {defaults or 'none'}.` | EXTRACTION | `none` |
| 7 | `A2T-ARG-CONSTRAINTS` | `Argument constraints: {constraints or 'none'}.` | EXTRACTION | `none` |
| 8 | `A2T-OWN-PATTERN` | `This exemplar's argument pattern: {own_pattern}.` | FORM | `no arguments` |
| 9 | `A2T-OTHER-PATTERNS` | `Other argument patterns for this tool: {other_text}.` | FORM | `no other argument pattern observed for this tool` |
| 10 | `A2T-POOL-VALUES` | `Argument values observed for this tool in the construction pool: {filler_text}.` | EXTRACTION | `no argument values observed` |
| 11 | `A2T-EXTRA-CALLS` *(optional)* | `Further calls in this exemplar: {names}.` | FORM | — (omitted) |
| 12 | `A2T-PRIOR-TABLE` *(optional)* | `{prior_representation[tool]}` | EXTRACTION | `no argument patterns observed` |

### 2.2 SLURP — five field groups, enumerated independently

Source: `rails/knowledge_build.py` (sha256
`94f3b7ef84ad5bcf393871f7c5e3cafca99a9b47ec87a802eb90226f3a47cd48`), the `content_text` f-string in
`build_key_value_layer`, plus the optionally appended prior representation. **SLURP's field shape is
not A2T's**, and in particular SLURP has **no form-oriented group at all** — the builder never
renders an answer form.

| # | field group | builder line | orientation | placeholder literal |
|---|---|---|---|---|
| 1 | `SLURP-EXEMPLAR-SENTENCE` | `Exemplar sentence: "{row.content}"` | MATCHING | — |
| 2 | `SLURP-INTENT-LABEL` | `-> intent {intent} (scenario={scenario}, action={action}).` | MATCHING | — |
| 3 | `SLURP-SLOT-PAIRS` | `Slot type=filler pairs: {slot_text}.` | EXTRACTION | `no slot entities` |
| 4 | `SLURP-NORMALIZATION` | `{normalization_text}.` | EXTRACTION | `no additional surface-form variants observed for this utterance's entity types` |
| 5 | `SLURP-PRIOR-TABLE` *(optional)* | `{prior_representation_by_intent[intent]}` | EXTRACTION | `no entity types observed` |

### 2.3 Orientation, justified from each field's own content

- **MATCHING** — content that can help pick the right tool/intent and carries neither answer syntax
  nor argument values: the exemplar utterance/sentence (the lexical bridge, and the very material
  the content facet embeds as the retrieval key), the tool identity/taxonomy, the registry prose
  description, and on SLURP the intent label itself.
- **FORM** — content that demonstrates the *shape* of a legal answer: the rendered tool call, the
  callable signature, this exemplar's argument pattern, the menu of other argument patterns, and the
  statement that an answer may contain further calls. Their argument **values** belong to another
  utterance and are not transferable; what survives transfer is the form.
- **EXTRACTION** — content whose whole purpose is to fill slots/arguments: defaults, constraints,
  the observed-value inventory, the exemplar's own slot pairs, the surface-form variant inventory,
  and the numeric prior tables (distributions over argument keys / entity types **conditioned on a
  target that is already assumed**, so they cannot discriminate between targets).

**The one mixed group.** `A2T-REGISTRY-SIGNATURE` is classified FORM because a callable declaration
is primarily a form statement, but everything it adds beyond the tool name — already carried by
`A2T-TOOL-IDENTITY` — is the argument list, which is extraction material. It is therefore reported
in a **BROAD** extraction band as well, and every A2T extraction figure below is given both ways.

---

## 3. GATES — nothing below was read until these passed

### 3.1 The parse-fidelity gate — **PASS, 100 %**

Every value is segmented on anchors read off the builder; every anchor is asserted to occur
**exactly once**; the exemplar, the registry block and the prior table are recovered by **exact
identity** against the snapshot's own facet representations rather than parsed; and the segments are
reassembled and asserted **byte-equal** to the original content.

| carrier | snapshot values | segmented | reassembled byte-equal | failures |
|---|---|---|---|---|
| Audio2Tool (`ec2f9ec4…9fb2`) | 12,601 | **12,601** | **12,601** | **0** |
| SLURP (`e27b2745…1b57`) | 11,514 | **11,514** | **11,514** | **0** |

The gate is run over the **whole snapshot**, not only over the supplied subset, so it is a stronger
statement than the accounting needs.

### 3.2 The dispatch cross-check — **PASS**

| | value |
|---|---|
| SLURP two-contact trajectories | 340 |
| SLURP trajectories with non-empty supply | **340** |
| SLURP committed report `two_contact_trajectories_dispatched` | **340** |
| A2T dispatched | 15 |
| A2T trajectories with non-empty supply | **15** |

"Received supply" and "was dispatched" are the same set on both carriers, proved rather than assumed.

### 3.3 The form-classification gate — reproduces the landed diagnosis exactly

Recomputed through the frozen `analysis.a2t_gold_absence_diagnosis._form_class`
(`reproduction.toolcall_scoring.parse_tool_calls_text`): contact-0 forms **{empty 11, unparsed 3,
well-formed-non-empty 1}**, BLEND final forms **{well-formed-non-empty 12, empty 3}**, **form
repaired = 11**. Identical to `docs/readiness/2026-08-25-a2t-gold-absence-diagnosis.md` §6.

---

## 4. THE TOKEN MODEL — which estimator, and its calibration error

**No tokenizer was contacted.** The campaign's prompt-fit receipts were measured through the
resident llama-server's `/props` + `/apply-template` + `/tokenize` routes (see
`scripts/dev500_confirmatory_prompt_fit.py`), which is an HTTP contact this row may not take, and
this repository holds no offline copy of that tokenizer. The campaign's own **established offline
estimator** is used and named.

### 4.1 The registered estimator — UNIFORM

`analysis.dev100_supply_budget_projection.flown_value_token_rate`: the paired within-sample
regression of `prompt_tokens(evidence-decode) − prompt_tokens(direct-decode)` on the supplied value
block's own character count, over the sealed stores. It was called **unmodified on the DEV-1000
BLEND flight itself** (340 paired contacts). Verified on the landed `MODEL_REQUEST` payloads: the
evidence request's `history` carries **only** the control instruction (no assistant turn), so the
delta is exactly the instruction plus the supplied value block and the intercept is a genuine
constant.

| carrier | paired contacts | tokens/char | chars/token | intercept (tok) | r² | max abs residual (tok) | 5-fold holdout MAE (tok) |
|---|---|---|---|---|---|---|---|
| SLURP DEV-1000 BLEND | 340 | 0.427626 | 2.3385 | −30.48 | 0.974456 | 159.57 | 32.49 |
| Audio2Tool G1 attempt 4 | 11 | 0.287245 | 3.4814 | +10.72 | 0.995348 | 59.15 | 25.41 |

On Audio2Tool the function could **not** be called unmodified: attempt 4 carries only the fifteen
evidence contacts, while their Pass-A **direct** partners landed in attempts 1 and 2. The same
estimator was therefore executed across the three sealed attempt traces using the module's own trace
primitive, pairing a trajectory **only** when its direct contact's response re-hashes to the sealed
attempt-4 `direct_response_sha256`. **11 of 15 pair**; the four that do not
(`tier4_implicit:001513`, `tier5_needle:000061`, `tier7_multiturn:000214`, `tier7_multiturn:001516`)
are named in the receipt rather than filled in. This is stated rather than hidden.

Cross-check retained: `analysis.a2t_admission_scale_sweep.token_calibration`, which derives
**3.2884 chars/token** from the landed `prompt-fit-np2.json` receipt (tokenizer-measured at a
registered contact) — within 5.6 % of the A2T paired regression's 3.4814.

### 4.2 The refinement — DENSE/PROSE, and why it is published beside the registered model

`dev100_supply_budget_projection.token_model` already records that the dense numeric prior tables
tokenize at about **1.93 chars/token** against roughly twice that for exemplar prose. The same
paired regression with **two predictors** — prior-table characters separated from everything else —
measures that split directly and fits far better:

| carrier | prose chars/token | dense (prior table) chars/token | intercept (tok) | r² | max abs residual | holdout MAE |
|---|---|---|---|---|---|---|
| SLURP | **5.919** | **1.689** | −5.44 | **0.997153** | 47.28 | **11.08** |
| Audio2Tool | **6.000** | **1.430** | −64.21 | **0.997665** | 40.24 | 35.99 (n = 11) |

The two carriers agree on the prose rate to within 1.4 % from completely separate flights, and the
dense rate lands beside the independently measured 1.93 chars/token. Both models are published and
**every headline below is given under both**.

### 4.3 A third model, measured and REFUSED

One rate **per field group** was fitted and is **refused**: the group character counts are collinear
(a value's label length is fixed by the same task target that fixes its prior table), which drives
coefficients negative — SLURP `SLURP-INTENT-LABEL` = **−0.0850** tok/char; A2T five negative
coefficients including `A2T-DESCRIPTION` = **−0.4355**. A negative tokens-per-character is not a
quantity. The coefficients are published in the receipt as the reason.

### 4.4 Estimate versus measurement — the closure

The whole-supply token cost per contact is **measured**, not estimated, from the sealed `COST`
channel:

| carrier | paired contacts | measured Δprompt_tokens min / median / mean / max | measured total |
|---|---|---|---|
| SLURP | 340 | 204 / 733 / 712.61 / 1,452 | **242,286** |
| Audio2Tool | 11 | 455 / 679 / 788.64 / 1,622 | **8,675** |

| carrier | model | estimated supply-block tokens on the same contacts | difference |
|---|---|---|---|
| SLURP | DENSE/PROSE | 244,135.1 | **−0.76 %** |
| SLURP | UNIFORM | 252,649.8 | −4.28 % |
| Audio2Tool | UNIFORM | 8,557.0 | **+1.36 %** |
| Audio2Tool | DENSE/PROSE | 9,381.3 | −8.14 % |

On SLURP (n = 340) the DENSE/PROSE model closes to **0.76 %** of a real tokenizer measurement. On
Audio2Tool (n = 11) the UNIFORM model closes better in total while DENSE/PROSE fits better
per-contact; the A2T figures below are therefore reported as a **band across the two models**, never
as a point estimate.

### 4.5 The one non-value overhead, priced once

Every evidence contact also carries the fixed control instruction (168 characters, sha256
`ac8a0deb…da28`), verified against the sealed `MODEL_REQUEST` payloads. It is **not** part of the
value block and is excluded from every share below.

---

## 5. TOKEN ACCOUNTING — what was actually supplied

### 5.1 Audio2Tool — A2T-G1-104, attempt 4

> **SECONDARY READING on an EXPOSED population.** Free to read, never a campaign claim.

15 contacts received supply; **47 values**, mean 3.13 values/contact; **39,861 characters**;
per-contact characters min 1,619 / median 2,330 / mean 2,657.4 / max 5,715. Estimated whole-block
cost **838.6 tok/contact** (DENSE/PROSE) or **763.3 tok/contact** (UNIFORM).

| field group | orientation | present in | chars | char share | tokens (D/P) | **token share (D/P)** | tok/contact (D/P) | token share (UNIF) |
|---|---|---|---|---|---|---|---|---|
| `A2T-EXEMPLAR-UTTERANCE` | MATCHING | 47/47 | 2,180 | 5.47 % | 363.3 | 2.89 % | 24.22 | 5.47 % |
| `A2T-CALL-RENDER` | FORM | 47/47 | 2,487 | 6.24 % | 414.5 | 3.30 % | 27.63 | 6.24 % |
| `A2T-TOOL-IDENTITY` | MATCHING | 47/47 | 3,219 | 8.08 % | 536.5 | 4.27 % | 35.77 | 8.08 % |
| `A2T-REGISTRY-SIGNATURE` | FORM (mixed) | 47/47 | 2,563 | 6.43 % | 427.2 | 3.40 % | 28.48 | 6.43 % |
| `A2T-DESCRIPTION` | MATCHING | 47/47 | 2,539 | 6.37 % | 423.2 | 3.36 % | 28.21 | 6.37 % |
| `A2T-ARG-DEFAULTS` | EXTRACTION | 47/47 | 1,809 | 4.54 % | 301.5 | 2.40 % | 20.10 | 4.54 % |
| `A2T-ARG-CONSTRAINTS` | EXTRACTION | 47/47 | 1,748 | 4.39 % | 291.3 | 2.32 % | 19.42 | 4.39 % |
| `A2T-OWN-PATTERN` | FORM | 47/47 | 2,493 | 6.25 % | 415.5 | 3.30 % | 27.70 | 6.25 % |
| `A2T-OTHER-PATTERNS` | FORM | 47/47 | 3,196 | 8.02 % | 532.7 | 4.23 % | 35.51 | 8.02 % |
| `A2T-POOL-VALUES` | EXTRACTION | 47/47 | 6,081 | 15.26 % | 1,013.5 | 8.06 % | 67.57 | 15.26 % |
| `A2T-EXTRA-CALLS` | FORM | **8/47** | 403 | 1.01 % | 67.2 | 0.53 % | 4.48 | 1.01 % |
| **`A2T-PRIOR-TABLE`** | EXTRACTION | 47/47 | **11,143** | **27.95 %** | **7,792.5** | **61.95 %** | **519.50** | 27.95 % |
| **total** | | | **39,861** | 100 % | **12,579.0** | 100 % | **838.60** | 100 % |

### 5.2 SLURP — DEV-1000 BLEND, both halves

> **SECONDARY READING on the LOCKED baseline's own population** for the NEW500 half and for the
> pooled row. Descriptive only; it **must not** be used to revise, re-tune or restate the DEV-1000
> LOCK. The nested DEV-500 half is prior-exposed and carries the exposed-tier caveat.

| population | contacts with supply | values | mean values/contact | block chars | chars/contact min · median · mean · max | block tokens (D/P) | tok/contact (D/P) |
|---|---|---|---|---|---|---|---|
| **DEV-1000-NEW500 (UNEXPOSED)** | 163 / 500 | 464 | 2.8466 | 288,870 | 702 · 1,777 · 1,772.2 · 3,169 | 119,642.6 | **734.00** |
| DEV-500 (PRIOR-EXPOSED) | 177 / 500 | 504 | 2.8475 | 301,950 | 746 · 1,777 · 1,705.9 · 3,474 | 124,492.5 | 703.35 |
| DEV-1000 (both halves) | 340 / 1000 | 968 | 2.8471 | 590,820 | 702 · 1,777 · 1,737.7 · 3,474 | 244,135.1 | 718.04 |

**DEV-1000-NEW500 (UNEXPOSED) — SECONDARY READING**

| field group | orientation | present in | chars | char share | tokens (D/P) | **token share (D/P)** | tok/contact (D/P) | token share (UNIF) |
|---|---|---|---|---|---|---|---|---|
| `SLURP-EXEMPLAR-SENTENCE` | MATCHING | 464/464 | 23,875 | 8.27 % | 4,033.6 | 3.37 % | 24.75 | 8.27 % |
| `SLURP-INTENT-LABEL` | MATCHING | 464/464 | 27,930 | 9.67 % | 4,718.7 | 3.94 % | 28.95 | 9.67 % |
| `SLURP-SLOT-PAIRS` | EXTRACTION | 464/464 | 20,988 | 7.27 % | 3,545.8 | 2.96 % | 21.75 | 7.27 % |
| `SLURP-NORMALIZATION` | EXTRACTION | 464/464 | 48,666 | 16.85 % | 8,221.9 | 6.87 % | 50.44 | 16.85 % |
| **`SLURP-PRIOR-TABLE`** | EXTRACTION | 464/464 | **167,411** | **57.95 %** | **99,122.6** | **82.85 %** | **608.11** | 57.95 % |
| **total** | | | **288,870** | 100 % | **119,642.6** | 100 % | **734.00** | 100 % |

The DEV-500 half is within 0.5 pp of the NEW500 half on every share (receipt
`token_tables.slurp["DEV-500 (PRIOR-EXPOSED)"]`), so nothing here is a property of one half.

**The single dominant fact on both carriers: the numeric prior table is 28.0 % (A2T) / 58.0 %
(SLURP) of the injected characters and, because it tokenizes 3.5–4.2× denser than prose, 62.0 %
(A2T) / 82.9 % (SLURP) of the injected tokens.**

---

## 6. NON-TRIVIALITY — how often a field is a literal placeholder

A field group counts as a placeholder when its payload is exactly the filler the builder emits for
empty source material (§2 tables). Framing literals are included in the character/token cost,
because they are injected whether or not the field carries content.

### 6.1 Audio2Tool (47 supplied values)

| field group | placeholder occurrences | fraction | placeholder chars | placeholder tokens (D/P) |
|---|---|---|---|---|
| `A2T-ARG-DEFAULTS` | 14 | **29.79 %** | 350 | 58.3 |
| `A2T-ARG-CONSTRAINTS` | 16 | **34.04 %** | 448 | 74.7 |
| `A2T-OWN-PATTERN` | 16 | **34.04 %** | 768 | 128.0 |
| `A2T-OTHER-PATTERNS` | 11 | **23.40 %** | 979 | 163.2 |
| `A2T-POOL-VALUES` | 11 | **23.40 %** | 1,034 | 172.3 |
| `A2T-REGISTRY-SIGNATURE` / `A2T-DESCRIPTION` / `A2T-PRIOR-TABLE` | 0 | 0 % | 0 | 0.0 |
| **total** | | | **3,579** | **596.5** (4.74 % of the block; 1,028.0 = 8.98 % under UNIFORM) |

### 6.2 SLURP

| population | field group | placeholder occurrences | fraction | placeholder tokens (D/P) |
|---|---|---|---|---|
| **NEW500 (UNEXPOSED)** | `SLURP-SLOT-PAIRS` | 284 / 464 | **61.21 %** | 2,015.2 |
| **NEW500 (UNEXPOSED)** | `SLURP-NORMALIZATION` | 284 / 464 | **61.21 %** | 3,838.5 |
| NEW500 total | | | | **5,853.6** (4.89 % of the block) |
| DEV-500 | `SLURP-SLOT-PAIRS` / `SLURP-NORMALIZATION` | 343 / 504 | **68.06 %** | 2,433.8 / 4,635.9 |
| DEV-500 total | | | | **7,069.7** (5.68 %) |
| DEV-1000 both | both groups | 627 / 968 | **64.77 %** | 12,923.4 (5.29 %) |

Neither prior table is ever a placeholder on either carrier. On SLURP the two placeholder groups
fire on **exactly the same values** — a value with no entities also has no surface-form variants —
so roughly **two thirds of every supplied SLURP value carries no slot content whatsoever**, and
still pays the framing cost for two slot fields.

---

## 7. COST PER CHANNEL, AGAINST DELIVERY

> Reframed from the registered "dead weight" per §1. **Nothing here is written off.** The
> extraction channel works where it is delivered; the decision-relevant quantity is what each
> channel costs and how often that cost is actually incurred.

### 7.1 Delivery

| carrier / population | population | received supply | delivery rate |
|---|---|---|---|
| Audio2Tool A2T-G1-104 | 104 | **15** | **14.42 %** |
| SLURP DEV-1000-NEW500 (UNEXPOSED) | 500 | **163** | **32.60 %** |
| SLURP DEV-500 (PRIOR-EXPOSED) | 500 | 177 | 35.40 % |
| SLURP DEV-1000 (both) | 1,000 | 340 | 34.00 % |

### 7.2 Audio2Tool — A2T-G1-104 (EXPOSED, SECONDARY)

| channel | chars | char share | **token share** | tokens / delivered contact | tokens across the flight | tokens amortized over all 104 |
|---|---|---|---|---|---|---|
| **EXTRACTION (strict)** | 20,781 | 52.13 % | **74.72 %** (D/P) · 52.13 % (UNIF) | **626.59** (D/P) · 397.95 (UNIF) | **9,398.9** (D/P) · 5,969.2 (UNIF) | 90.37 · 57.40 |
| EXTRACTION (broad, incl. signature) | 23,344 | 58.56 % | **78.11 %** · 58.56 % | 655.07 · 447.03 | 9,826.0 · 6,705.4 | 94.48 · 64.48 |
| MATCHING | 7,938 | 19.91 % | 10.52 % · 19.91 % | 88.20 · 152.01 | 1,323.0 · 2,280.1 | 12.72 · 21.92 |
| FORM | 11,142 | 27.95 % | 14.76 % · 27.95 % | 123.80 · 213.37 | 1,857.1 · 3,200.5 | 17.86 · 30.77 |

Bands close exactly: strict + matching + form = 20,781 + 7,938 + 11,142 = 39,861 characters = the
whole block (the signature sits in FORM and is only *additionally* reported in the broad band).

**Headline (A2T): the extraction-oriented channel is 52.1 %–74.7 % of the injected token budget —
between 398 and 627 tokens per delivered contact, and 5,969–9,399 tokens across the whole 15-contact
flight.**

### 7.3 SLURP — DEV-1000

| population | channel | chars | **token share** | tokens / delivered contact | tokens across the flight | amortized per population sample |
|---|---|---|---|---|---|---|
| **NEW500 (UNEXPOSED, SECONDARY)** | **EXTRACTION** | 237,065 | **92.68 %** (D/P) · 82.07 % (UNIF) | **680.31** · 621.93 | **110,890.4** · 101,375.1 | 221.78 · 202.75 |
| **NEW500 (UNEXPOSED, SECONDARY)** | MATCHING | 51,805 | 7.32 % · 17.93 % | 53.69 · 135.91 | 8,752.3 · 22,153.1 | 17.50 · 44.31 |
| NEW500 | FORM | **0** | **0 %** | 0 | 0 | 0 |
| DEV-500 (PRIOR-EXPOSED) | EXTRACTION | 247,273 | 92.58 % · 81.89 % | 651.16 · 597.40 | 115,255.0 · 105,740.3 | 230.51 · 211.48 |
| DEV-1000 (both) | EXTRACTION | 484,338 | 92.63 % · 81.98 % | 665.13 · 609.16 | 226,145.4 · 207,115.3 | 226.15 · 207.12 |

**Headline (SLURP): the extraction-oriented channel is 82.0 %–92.7 % of the injected token budget —
between 622 and 680 tokens per delivered contact on the unexposed half, and 101,375–110,890 tokens
across its 163 delivered contacts. SLURP carries no form-oriented channel at all.**

### 7.4 Two disclosures that bound these numbers

1. **Lower bound.** The list-like extraction groups (`A2T-ARG-DEFAULTS`, `A2T-ARG-CONSTRAINTS`,
   `A2T-POOL-VALUES`) are priced at the **prose** rate, which under-prices comma-separated value
   lists. Their true token share is higher, so the extraction figures are a **lower** bound.
2. **Conservative bound on the prior table.** The prior-table group opens with an identifying header
   naming the target it is keyed by — *matching-redundant framing*, not new matching content. Its
   share of the group is **44.95 %** (A2T) and **24.95 %** (SLURP NEW500). If the header is
   reassigned away from EXTRACTION anyway, the strict extraction token share becomes:

   | carrier / population | as reported (D/P) | header reassigned (D/P) | as reported (UNIF) | header reassigned (UNIF) |
   |---|---|---|---|---|
   | Audio2Tool | 74.72 % | **46.87 %** | 52.13 % | 39.57 % |
   | SLURP NEW500 (UNEXPOSED) | 92.68 % | **72.02 %** | 82.07 % | 67.61 % |

   Even under the most conservative combination the extraction channel is **39.6 %–46.9 %** of the
   A2T budget and **67.6 %–72.0 %** of the SLURP budget.

---

## 8. WHICH FIELDS COULD CARRY THE FORM-REPAIR CHANNEL

> **DISPATCHED TRAJECTORIES ONLY (n = 15).** Retained trajectories received no evidence at all, so
> any arm-to-arm difference among them is decode variance — measured at 10.11 % divergent response
> text on the A2T retained set and 14.84 % / 16.72 % on the two SLURP retained sets
> (`2026-08-25-extraction-conditioned-on-dispatch.md` §9). **Nothing in this section touches a
> retained trajectory.**
>
> **This is a MECHANISM READING AT SMALL n and never an effect size.** n = 11 repaired, n = 3
> eligible-but-not-repaired, on an EXPOSED population.

**Candidate groups**, on content: `A2T-CALL-RENDER` (a literal well-formed call), `A2T-OWN-PATTERN`
and `A2T-OTHER-PATTERNS` (the two the mission names), `A2T-REGISTRY-SIGNATURE` (the callable
declaration) and `A2T-EXTRA-CALLS` (a legal answer may hold more than one call).

### 8.1 Presence cannot discriminate — the four main candidates are universal

| field group | repaired (n = 11): trajectories receiving it | occurrences / supplied values | not repaired (n = 3): trajectories | occurrences / supplied values |
|---|---|---|---|---|
| `A2T-CALL-RENDER` | **11 / 11** | 1.000 | **3 / 3** | 1.000 |
| `A2T-REGISTRY-SIGNATURE` | **11 / 11** | 1.000 | **3 / 3** | 1.000 |
| `A2T-OWN-PATTERN` | **11 / 11** | 1.000 (non-placeholder 0.667) | **3 / 3** | 1.000 (non-placeholder 0.667) |
| `A2T-OTHER-PATTERNS` | **11 / 11** | 1.000 (non-placeholder 0.778) | **3 / 3** | 1.000 (non-placeholder 0.667) |
| `A2T-EXTRA-CALLS` | 3 / 11 | 0.222 | **0 / 3** | 0 |

The builder emits the four main candidates on **every** value, so their presence is identical on
both sides of the outcome split and cannot be what distinguishes the two groups.

### 8.2 The decisive fact — the supply is held BYTE-IDENTICAL across the split

**11 of the 15 dispatched trajectories received the identical three-value supply**
`value:tier4_implicit:001275` + `value:tier7_multiturn:002853` + `value:tier7_multiturn:003760`
(2,330 characters) — the constant-retrieval-key cluster the gold-absence diagnosis identified. All
11 were `empty` at contact 0.

| within that identical-supply cluster (n = 11) | count | sample ids |
|---|---|---|
| form repaired | **8** | `tier4_implicit:000655`, `:000900`, `:001148`, `:001409`, `:001513`, `:003312`, `tier7_multiturn:000214`, `:001516` |
| **not** repaired | **3** | `tier1_direct:000167`, `tier1_direct:001631`, `tier4_implicit:001389` |

**Every field group — including all five form candidates — is byte-identical across that 8-versus-3
split.** No field of a constant can explain a difference in outcome. The 8/11 = 72.7 % repair rate
inside the cluster is a per-trajectory response difference under a fixed intervention (the speech
queries differ), not a field difference.

### 8.3 The one candidate that does differ is perfectly confounded, at n = 3

`A2T-EXTRA-CALLS` reaches 3 of the 11 repaired and 0 of the 3 not-repaired. Those exact three —
`tier2_parametric:004826`, `tier3_multi_intent:000879`, `tier5_needle:000061` — are **also** the only
three eligible trajectories that were `unparsed` (not `empty`) at contact 0, and the only three that
received a supply other than the constant cluster's. Contact-0 form class, supply set and
`A2T-EXTRA-CALLS` presence are **perfectly collinear at n = 3**. Nothing can be attributed to any
one of them. (The twelfth well-formed final answer, `tier1_direct:004159`, was already well-formed
at contact 0 and received 2 values / 1,619 characters; it never changed form.)

### 8.4 What the accounting can say about the form channel

- The form channel is carried by fields that are **always present** and that cost **123.80 tokens
  per delivered contact (DENSE/PROSE) or 213.37 (UNIFORM)** — **14.76 % / 27.95 %** of the injected
  block. `A2T-CALL-RENDER` alone costs 27.63 / 47.63 tokens per contact.
- The landed diagnosis measured this wide channel's conversion at **1 of 11 = 9.1 %**, against
  **2 of 4 = 50 %** for gold-bearing supply. This document adds the price beside that rate; it does
  not re-measure it.
- **Which specific field carries the repair is NOT identified by this evidence and cannot be, from
  the landed flight**, because the candidate fields are universal and, on 11 of the 14 eligible
  trajectories, byte-identical. Identifying it would require an ablation — a new flight, a new
  registration, and it is not proposed here.

---

## 9. HARD STOP — what this document does NOT do and does NOT authorize

- **It is ACCOUNTING ONLY.** It does **not** propose or evaluate a field-selection policy, does not
  recommend dropping, shortening, reordering or conditioning any field group, and does not change
  how anything is rendered. A field-selection design step is a **separate, separately registered
  row** and must carry its own falsifier, its own two-sided gate and its own dispatch-preservation
  clause; nothing here licenses it to skip those.
- **No field is written off.** The registered "dead weight" premise is superseded (§1): the
  extraction channel is effective where it is delivered. The extraction-oriented share is a **cost**
  figure, not a waste figure, and must never be quoted as the latter.
- **It does NOT revise, re-tune or restate the DEV-1000 LOCK.** Every SLURP unexposed-500 number
  here is a SECONDARY reading on the locked baseline's own population and is descriptive. The lock
  stands exactly as landed at `d9fef537`.
- **No knob change, no re-tune, no re-flight, no new arm, no threshold move**, no change to
  `configs/`, `rails/` or `core/`.
- **No claim.** No generality, superiority or cross-carrier transfer claim; no conclusion about the
  method's capability beyond these two already-read populations.
- **No test contact, no FINAL60 contact, no new population, no G2 opening.** The A2T numbers are a
  secondary reading on an EXPOSED n = 104 below the campaign plan's own power floor; the form-channel
  subgroups (n = 11 / n = 3) are MECHANISM readings and can never be cited as effect sizes.
- **No Stage-3 activity of any kind**, no manuscript, no paper-scale profile, no promotion.
- **Nothing here puts gold on a runtime path.** No gold label was read by this row at all; the
  accounting is over injected text and sealed prompt-token counts only.

---

## 10. What could not be verified, and is therefore omitted

1. **A real tokenization of any single field group.** Every per-group token figure is an estimate
   from a measured character-to-token model, published under two models with their calibration
   error, holdout error and closure against the measured totals (§4). A true per-group tokenization
   would need a `/tokenize` contact this row may not take.
2. **A per-field-group token rate.** Fitted, measured and **refused** for collinearity (§4.3); the
   negative coefficients are published rather than suppressed.
3. **Four of the fifteen A2T evidence contacts have no recoverable paired direct contact**
   (`tier4_implicit:001513`, `tier5_needle:000061`, `tier7_multiturn:000214`, `tier7_multiturn:001516`):
   their Pass-A direct partners do not appear with a matching response digest in any sealed attempt
   trace. The A2T token rate is fitted on the other 11 and the four are named rather than imputed.
4. **Which field carries the form repair** — not identifiable from the landed flight (§8.4).
5. **The regression intercepts are not the control instruction's token cost.** SLURP's is −30.48
   (UNIFORM) / −5.44 (DENSE/PROSE) and A2T's is +10.72 / −64.21, while the 168-character instruction
   should cost roughly 28 tokens at the prose rate. The two contacts therefore differ by some small
   fixed structural amount this row did not identify. It is reported rather than explained; it does
   not affect the marginal rates, which are what the per-field split uses, and the closure in §4.4
   bounds its total effect at 0.76 % on SLURP.
