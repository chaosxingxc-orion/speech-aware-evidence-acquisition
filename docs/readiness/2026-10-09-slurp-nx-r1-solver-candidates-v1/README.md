# NX R1 Solver instruction-template candidates v1 (SLURP, Stage 3): five hand-written arms from aggregate tables

**Status: CANDIDATES ONLY.** Nothing is registered, re-pinned, flown or admitted. Author: Claude Opus 5.5 (candidate
author), 2026-10-09, branch `fable/nx-r1-candidates` (base master `3bd570711`). Every candidate is labelled
**`author: hand (Opus 5.5 from aggregate tables)`** (programme C0.5 / C3). The label lives here and not inside the
template files, because a phase template is sent to the model byte for byte
(`rails.phase_material.render_static_instruction`).

**Contacts: zero.** No model, server, tokenizer, scorer, GPU or network contact; no gold, utterance text, transcript,
filler or model output was read, printed or persisted. Inputs were aggregate tables only (owner directive 2026-10-09:
template-based learning from statistics, never per-sample review).

## 1. What the arms replace

| item | value |
| --- | --- |
| locked Solver template (delivering arm, sixth arm) | `configs/probes/slurp_native_role_solver_v2.txt` |
| its sha256 (git blob bytes = working bytes, LF) | `18bff5c557cac7ac14be6b08aa0a1a6ad54c1b9820199c3b6749b2271d756fbd` |
| its word count (`wc -w`) | 160 (length class +-40 %: 96 .. 224) |
| how it is pinned | `configs/baseline/slurp-native-stage3-comp1b-fold-a-baseline-v1.json` phase material, Solver `instruction_template: probes/slurp_native_role_solver_v2.txt` (same in the DEV-2000-ADDED, test-sample and module COMP-1b baselines); the shared task context is `probes/slurp_native_role_context_v3.txt` (`{tool_schemas}` fill = legal inventory) |
| output contract the parser expects | `reproduction/slurp_scoring.py` `parse_slu_response`: one JSON object with `scenario`, `action`, `entities[{type, filler}]` |
| ChatGPT-era donor (input to c4) | `configs/probes/system-text-policy/3fed5090255538a879aab48d0574ddee95ebfbe679c52667758991498dffe74a/solver.txt` (206 words; local K4 update 3: raw entity exact 50 / 100 vs control 47, A/A 46; F1 +1.23 [-2.06, +4.52]) |

The locked template has four blocks: **P1** intent resolution over the Perception candidates; **P2** the output
contract (final-answer authority plus the JSON shape line); **P3** entity rules; **P4** the revision clause, which
ends with a tool sentence. Every candidate is a complete replacement file with no placeholder (the locked file has
none; a `{tool_schemas}` token would be refused by the phase renderer), ASCII, LF, one trailing newline, and no word
"tool" (brief: do not reference tools). No candidate contains an example utterance or any slot value; conventions are
described, not exemplified.

## 2. Inputs and conversions used for every prediction

Failure classes at the Solver's first raw answer (s1), from `docs/results/2026-10-09-slurp-nx-exchange-rates-offline.md`
section 6 (Fold A 1,080 / DEV-2000-ADDED 1,000; E1 = value printed with its type in the row's exemplars, E3 = named by a
delivered slot card):

| class | Fold A total / E1 / E3 / none | DEV total / E1 / E3 / none |
| --- | --- | --- |
| MISSING | 188 / 103 / 14 / 70 | 187 / 94 / 14 / 79 |
| SPURIOUS | 264 / 100 / 27 / 132 | 245 / 86 / 23 / 127 |
| EMPTY-GOLD-FILL (rows of empty-gold rows) | 161 / 414 | 138 / 314 |
| FORMAT (s1 -> delivered after normaliser v3) | 40 -> 10 | 44 -> 10 |
| PARSE-FAIL (rows) | 1 | 1 |

Exchange rates (same note, sections 0 and 4; pp of pooled official SLU-F1, Fold A / DEV): +1 raw-exact Solver row
0.0563 / 0.0567; +1 recovered MISSING 0.0621 / 0.0572; -1 SPURIOUS 0.0290 / 0.0282; one false-fill row emptied
0.0333 / 0.0322 (1.149 / 1.143 spurious per such row); one wrong entity repaired 0.0911 / 0.0854. The 1.5 pp bar is
about 27 raw-exact rows per 1,080.

Measured conversions on file, and where each is used:

| conversion | value | source | used for |
| --- | ---: | --- | --- |
| M1 delivered-filler conversion (value put in the Solver's view -> delivered) | 0.2471 | `docs/results/2026-09-28-slurp-w5-slot-exemplar-offline-estimate.md` (line 51) | c1 (value already in view), c5 (format) |
| Solver-contract emission shift (COMP-1 vs its A/A: 90 net of 414 zero-gold rows moved by a contract change, beyond the 21-33-row decode noise) | 0.217 | `docs/results/2026-09-29-slurp-supply-abstention-headroom-offline.md` section 4 | c2, c3 (the only measured size of a Solver-instruction effect on emission; applied in the suppressing direction) |
| E5-1 cross-fit precision of a missing-slot proposer | 0.25 | `docs/results/2026-09-30-slurp-e5-transcript-consistency-oracle-read.md` (lines 170, 210) | c1 pessimistic bound (precision of new emissions) |
| CONV probe P(correct given newly delivered) | 45.71 % | `docs/results/2026-09-27-slurp-conv-probe-read.md` | not used: it is an intent conversion for a gold intent newly placed on the shortlist; no R1 arm changes what is placed in view |
| harm ratios | F10 0.591 exact items lost per FP removed; N1 gate 3 per 28 = 0.11 | headroom note `2026-09-29-slurp-supply-abstention-headroom-offline.md` sections 3.3, 4 | c2, c3 harm netting |

**Fold B proxy.** No sealed Fold B tables exist; Fold B is the 1,080-row TRAIN sibling of Fold A, so the Fold A
counts are the Fold B prediction and the DEV counts are the sensitivity. Row figures are **raw-exact row
equivalents** = predicted pp / node rate 0.0563 (entity-level predictions do not need an assumption about how many
target rows carry a second error). The exchange rates were measured on the COMP-1b graph; on the review-off base the
Solver-to-delivery transfer is expected to be at least as tight (exchange note section 8).

## 3. The candidates

### r1-c1 -- value-in-supply extraction (`configs/probes/nx/solver/r1/r1-c1.txt`)

- **author:** hand (Opus 5.5 from aggregate tables).
- **Target:** MISSING whose value is in the supply: E1 103 + E3 14 = **117 (Fold A)**, E1 94 + E3 14 = **108 (DEV)**.
  Harm guard: SPURIOUS-E1 (copied pairs) 100 / 86.
- **Mechanism hypothesis:** the model uses the exemplars as intent evidence but not as a slot checklist; telling it to
  read them as conventions (which types this intent carries, span limits, spelling) and to walk the speech in spoken
  order against each suggested type recovers in-view values, while the heard-only clause keeps unheard exemplar
  values out.
- **Conversion:** M1 0.2471 -- the measured rate at which a value in the Solver's view becomes a delivered filler.
  These items already survived one exposure, so this is an upper analogue.
- **Prediction (Fold B via Fold A):** 117 x 0.2471 = 28.9 recovered entities x 0.0621 = **+1.80 pp**, **~32 raw-exact
  row equivalents**. DEV sensitivity: 26.7 x 0.0572 = **+1.53 pp** (~27 rows).
- **Harm netting:** break-even precision of the new emissions is 0.318 (Fold A; 0.0290 / (0.0621 + 0.0290)), 0.330
  (DEV). At the E5-1 precision 0.25 (three spurious per recovery) the arm is **-0.72 pp**. Equivalently, 62 extra
  SPURIOUS entities cancel the gross gain. Declared: +1.80 gross, range [-0.72, +1.80].
- **Words:** 223 (+39.4 %).
- **Diff vs locked:** P1 and P2 unchanged. P3: the "Do not invent a missing value ..." sentence removed (its content
  moves into the new block). **Added** block "conventions + spoken-order walk + heard-only rule" between P3 and P4.
  P4: two sentences merged; the tool sentence replaced by "Add nothing outside the task JSON."
- **sha256:** `715e6bb1248f6e99828b08ac0b1e190e59306fe97d6ec05a5f2a52f9303daf58`

### r1-c2 -- copy suppression with a heard-span requirement (`r1-c2.txt`)

- **author:** hand (Opus 5.5 from aggregate tables).
- **Target:** SPURIOUS pairs printed in the row's exemplars (E1): **100 (Fold A) / 86 (DEV)**. The same MISSING-E1
  mass (103 / 94) is protected by "keep a heard value no example shows".
- **Mechanism hypothesis:** spurious entities are exemplar slots transferred to an utterance that does not carry them;
  treating every printed value as unheard until confirmed, and requiring each filler to be one contiguous spoken
  stretch, suppresses the copy without discouraging heard values.
- **Conversion:** 0.217, the measured size of a Solver-contract effect on emission (reverse direction).
- **Prediction:** 100 x 0.217 = 21.7 SPURIOUS removed x 0.0290 = **+0.63 pp** (~11 row equivalents); DEV 18.7 x
  0.0282 = **+0.53 pp**. Harm at the F10 ratio (0.591 exact lost per FP): 12.8 x 0.0621 = -0.80, net **-0.17**; the
  break-even ratio is 0.467 exact lost per FP. Declared: +0.63 gross, range [-0.17, +0.63]. **Below 1.5 alone**; its
  role in the round is the harm-side twin of c1 (if c1 wins, c2 tells whether its copy guard is the active part).
- **Words:** 219 (+36.9 %).
- **Diff vs locked:** P1, P2 unchanged. P3 reduced to the label sentence, "all and only", and the empty-array rule
  (removed: "preserving their spoken surface forms", "Do not invent ...", "Knowledge associations ..."). **Added**
  block "anti-copy + contiguous heard span + keep heard values". P4 as in c1.
- **sha256:** `45bb164de465f71eb8adb11c2121a95164cace1b36b5ad2c7c5204bea35ac8cf`

### r1-c3 -- explicit empty-entity decision (decision 199) (`r1-c3.txt`)

- **author:** hand (Opus 5.5 from aggregate tables).
- **Target:** EMPTY-GOLD-FILL: **161 of 414 empty-gold rows (Fold A)**, **138 of 314 (DEV)**.
- **Mechanism hypothesis:** the model treats "no entities" as a fallback and fills operation words; stating that the
  empty list is a legal first-class decision that is the Solver's own (decision 199: an empty entity list is legal; nothing is added by
  the system), separating operation words from values, and naming the supplied N1 signal (most exemplars of the
  selected intent read `none`) as a prior lets the model abstain on operation-only commands. The model decides; no
  system rule empties anything, and no tool is involved (decision 206).
- **Conversion:** 0.217 (contract emission shift, reverse direction).
- **Prediction:** 161 x 0.217 = 34.9 rows emptied x 0.0333 = **+1.16 pp gross**, 34.9 raw-exact rows directly
  (empty-gold rows become exact). DEV: 29.9 x 0.0322 = **+0.96**. Harm: 40.1 FP removed; at the F10 ratio 23.7 exact
  lost x 0.0621 = -1.47, net **-0.31**; at the N1-gate ratio (0.11) 4.4 lost, net **+0.89** (DEV +0.74). Declared:
  central +0.89 if the model follows the N1 prior, range [-0.31, +1.16]. **Below 1.5 alone.** Secondary reads:
  false-fill rows (target down) and gold rows delivered empty (guard: COMP-1b 53 / A2 40).
- **Words:** 222 (+38.8 %).
- **Diff vs locked:** P1, P2 unchanged. P3: the final "If no entity is expressed, return an empty entities array"
  sentence removed (moved into the new block). **Added** block "empty-entity decision rule + N1 prior". P4 as in c1.
- **sha256:** `89b81e97c0c8d5377eff2892fac548ac83fd6a24f61ceb25396a57196bb262dc`

### r1-c4 -- the ChatGPT donor ported onto the locked template (`r1-c4.txt`)

- **author:** hand (Opus 5.5 from aggregate tables), porting the ChatGPT-era donor `3fed5090...` (K4 update 3, c4).
- **Target:** the donor's two mechanisms: intent resolution by eliminating contradictory candidates (Solver-own intent
  residual 9 / 12 rows, exchange note section 5) and role-and-filler-gated extraction with "exemplars cannot provide a
  filler" (MISSING and SPURIOUS together, 188 + 264 / 187 + 245).
- **Mechanism hypothesis:** resolving intent first by contradiction elimination, then requiring both a spoken filler and
  a legal role per entity, lowers both spurious copies and missed roles absent from the intent's associations.
- **Revision paragraph: NOT included, and not needed.** The NX base is review-off (programme section F2:
  `phase-native-module-v1-c2`, Planner iterations 0, max_revisions 0), so the Solver is never revisited; and in the E1
  node-template column every non-delivering arm is rendered only at the first Solver contact. The donor was authored on
  review-off and has no revision paragraph; adding one would change the donor, not port it. The donor's
  tool sentence is dropped (brief: no tool reference) and its contract line is replaced by the locked P2.
- **Conversion:** none on file matches this mechanism. The only measurement is the K4 n = 100 read: +3 raw-exact rows
  over control (50 vs 47), +1.82 pp face value per 1,080 at the node rate, with the control-A/A spread 1 row and the
  CI including 0. It was the best of four arms, so a winner's-curse correction of about 2 rows applies (the expected
  maximum of three null arms at that spread). **Declared central +0.6 pp (~11 row equivalents), author prior, not a
  measured conversion; range [0, +1.82].** Intent guard risk: c4 is the only arm that rewrites P1, so it can move intent
  on the 70 / 90 rank-2+ rows; the round's intent guard (rows differing <= 0.65 pp, about 7 rows) binds hardest here.
- **Words:** 211 (+31.9 %).
- **Diff vs locked:** P1 **replaced** by the donor's elimination paragraph. P2 unchanged. P3 = locked label sentence +
  the donor's role paragraph. **Added** the donor's retention paragraph + "Add no explanation outside the task JSON."
  P4 (revision clause) **removed**.
- **sha256:** `d375f16d5e7d988c5d7482c905a486b94f8be058b8d8483ff3a64c2985d09e05`

### r1-c5 -- contract tightening + TRAIN-side filler conventions (`r1-c5.txt`)

- **author:** hand (Opus 5.5 from aggregate tables).
- **Target:** FORMAT **40 (Fold A) / 44 (DEV)** at s1 (10 / 10 after normaliser v3), PARSE-FAIL 1 / 1, and label
  spelling (WRONG-TYPE 54 / 67 is not claimed). On the review-off base the tool-call parse defect of R0.3 does not occur
  (no tool is rendered), so the contract half is insurance against any future rendering, not a measured target.
- **Mechanism hypothesis:** a strict one-object reply (opens with `{`, closes with `}`, no tag, markup, fence or prose
  around it, exact key set) plus the corpus's written filler conventions moves surface errors out of the raw answer.
- **Conventions and their sources (no convention derived from gold by the author):**
  - lower case, apostrophes and internal hyphens kept, other punctuation dropped, numbers as spoken words:
    `docs/results/2026-09-17-slurp-a1-use-projection-audit-v1.md` lines 26-29 (projection P2, the convention normaliser
    v3 applies) and lines 78-82 (published SLURP systems emit lowercase spoken text);
  - date keeps the spoken calendar expression, no numeric date, no invented year; time as spoken words with am / pm as
    words, never digits or a colon: `knowledge/slurp/semantic/slot-audit-v1/snapshot.json` `conventions`
    (rule `saea-spoken-form-v1`, TRAIN construction profile, 9,354 construction utterances; file sha256
    `0cc3f96c98addad37fb564483f051dbe1a11145ac554a85918312c388573406c`). The snapshot's attested time forms were
    deliberately not copied (no slot values in templates).
- **Conversion:** M1 0.2471 on the delivered residual.
- **Prediction:** delivered FORMAT residual 10 x 0.2471 = 2.5 repairs x 0.0911 = +0.23 pp, plus at most one parse row
  (+0.06): **+0.28 pp (~5 row equivalents)**; DEV +0.27. **Below 1.5 alone.** **Metric caveat:** at s1, 40 x 0.2471 =
  9.9 FORMAT items could turn into raw-exact rows that normaliser v3 already repairs at delivery, so c5's gain on the
  raw node metric would overstate its delivered value by up to ~10 rows; read c5 (and every arm, for consistency) on
  the post-normaliser exact-set as well as the raw one.
- **Words:** 222 (+38.8 %).
- **Diff vs locked:** P1 unchanged. P2 **strengthened** (one object, braces, nothing around it, exact entity keys).
  P3 **rewritten** (label spelling rule; "preserving their spoken surface forms" moved into the conventions block;
  "Knowledge associations ..." sentence removed for length). **Added** the conventions block. P4: tool / explanation
  sentence removed (covered by P2).
- **sha256:** `3b4cb0f10c06f99b1a2ac9b1b833c93a309ffc26a70a0dad45d73126196be190`

## 4. Round summary (declared before any flight, decision 192 form)

| arm | target class (Fold A / DEV) | conversion | predicted pp Fold B (DEV) | row equivalents | range | words |
| --- | --- | --- | ---: | ---: | --- | ---: |
| locked v2 (delivering) | -- | -- | 0 | 0 | -- | 160 |
| r1-c1 | MISSING in supply 117 / 108 | M1 0.2471 | **+1.80** (+1.53) | ~32 | [-0.72, +1.80] | 223 |
| r1-c2 | SPURIOUS-E1 100 / 86 | contract 0.217 | +0.63 (+0.53) | ~11 | [-0.17, +0.63] | 219 |
| r1-c3 | EMPTY-GOLD-FILL 161 / 138 rows | contract 0.217, N1 harm | +0.89 (+0.74) | ~35 rows gross | [-0.31, +1.16] | 222 |
| r1-c4 | donor (intent elimination + role gate) | K4 n=100, shrunk | +0.6 (author prior) | ~11 | [0, +1.82] | 211 |
| r1-c5 | FORMAT 40 / 44, parse 1 / 1 | M1 0.2471 | +0.28 (+0.27) | ~5 | [0, +0.28] | 222 |

**Round declared effect: +1.80 pp (DEV proxy +1.53), carried by r1-c1 alone**, at the M1 conversion and only if c1's
new emissions are correct at least 32 % of the time (the SPURIOUS-E1 guard). No other arm reaches 1.5 pp by itself.
The round therefore meets the programme's >= 1.5 pp requirement on both proxy pools only through c1, and only at an
upper-analogue conversion; if c1 reads below its harm break-even, R1 round 2 should compose c1's extraction block with
c2's copy rule or c3's empty rule rather than re-tune c1 alone.

## 5. Notes for the cell author (E1 / E2)

- All paths fit the phase-material path rule (`core.instructions._TEMPLATE_RELPATH_PATTERN`, subdirectories allowed);
  the node-context-policy pattern (`^probes/[A-Za-z0-9_.\-]+\.txt$`, no subdirectories) does not apply to role
  templates, but if E1 routes arm templates through that validator these files must be flattened.
- The arms change only the Solver instruction bytes; the task context `slurp_native_role_context_v3.txt`, the supply,
  decoding, `max_tokens` 512 and the absence of `response_format` stay as locked.
- E2 secondaries to tabulate per arm, matching the declared targets: SPURIOUS-E1 and MISSING-E1/E3 counts (c1, c2),
  false-fill rows and gold rows delivered empty (c3), intent rows differing (c4), raw vs post-normaliser exact-set
  (c5), parse validity (all).
