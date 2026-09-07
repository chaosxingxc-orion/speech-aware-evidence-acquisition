# The Earnings-22 pre-meeting brief — what its source can actually reach

**THE CEILING IS 0.0229 CORPUS-WER POINTS, AND THAT IS THE WHOLE FINDING.** Across the 1,500
Earnings-22 short-form DEV clips, the five metadata facts the corpus publishes about a call — ticker,
country, UN region, dialect family, language family — touch **47 of 26,251 reference words (0.179 %)**.
The sealed comparator already gets **41 of those 47 right (87.23 %)**; its whole error mass on them is
**5 substitutions and 1 deletion**. A brief that fixed every one of them would move corpus WER by
0.0229 points — against a measured same-request null of **[−0.2356, +0.0692]** on this exact runtime
and roster. **The brief's direct channel is an order of magnitude below the noise floor of the
instrument that would have to see it.**

And the 47 words are not what they look like. **Not one of them belongs to a term that is specific to
the call whose metadata names it** (call-specific share **0.00 %**). Twenty-three of the 47 are the
literal word *other* — the value of the `Major Dialect Family` column for four of the ten calls, a
taxonomy label rather than a fact about the meeting, which also occurs 149 times in the other calls'
references. Two are *cost*, which is Costco's ticker and also ordinary earnings vocabulary (38
occurrences in calls that are not Costco's). **Eight of the ten tickers never appear as a spoken word
at all**, and **no UN region name appears anywhere in 26,251 reference words**.

Row `SAEA-E22-MF-BRIEF-SOURCE-AUDIT-V1` (`model-free-check`), registered before the first sealed byte
was read. **Zero contacts of every kind** — model, tokenizer, embedder, retriever, network, GPU, audio
decode — no media byte opened, the resident serving session neither started, stopped nor attached, and
the offline guard recorded **zero outbound connection attempts**. Receipts:
`docs/checks/speech-aware-evidence-acquisition/2026-09-07-e22-brief-source-audit/`
(`summary.json` sha256 `a5e08f47…`, `per-call-table.csv` `9a7637ee…`, `MANIFEST.sha256`). Module
`analysis/e22_brief_source_audit.py`, runner `scripts/e22_brief_source_audit.py`, tests
`tests/unit/test_e22_brief_source_audit.py`. Two back-to-back writes reproduce the same digests.

**Population: DEV ONLY.** `E22-ESB-DEV1500-TAIL2S-UTTERANCES`, split identity
`8dc9d6a04c408226e0575254ba4cbad605417c293fc5e55f40e6c8cf50f51207`, 1,500 clips at 150 per call over
all ten dev subset10 calls. **The six calibration-exposed ESB test calls were not opened**
(`test_split_read: false`); the reference loader is pinned to the DEV10 receipt alone. The 109
confirmatory calls are not named, loaded or read.

**No external source was consulted.** Owner ruling, 2026-09-07: Earnings-22 must not collect any
external information, or the result stops being comparable with the academic references. The
company-name brief variant is dropped, no ticker → legal-name lookup table is built or registered, and
the audit's only corpus input is the benchmark's own `metadata.csv`
(sha256 `52dbda11f4abbabf1b59dedae315d5873d6ccfe75104d1bce3d8ab24341f28e1`, 125 rows, 10,057 bytes).

---

## 1. The identity anchor, before anything else

| | value |
|---|---:|
| comparator | `SAEA-E22-DEV-ESB-TAIL2S-V1`, attempt `attempt-20260907T090708Z-df36cc` |
| scorer | `asr-wer-esb-whisper` (vendored Whisper `EnglishTextNormalizer`, whitespace tokenization) |
| corpus WER recomputed from its own sealed per-sample rows | **9.4054 %** |
| published by the 2026-09-07 encoding verdict §1.2 | **9.4054 %** |
| reference words | 26,251 |

`build_receipt` refuses to compute a single further number unless this reproduces. It did.

## 2. The pairing arithmetic

**1,500 clips, 10 call clusters, 150 clips per call, exactly.** That is the number a KC-E2 interval
would rest on, and it is fixed before the cell flies rather than discovered in a verdict. The clip →
call map is committed as `docs/receipts/artifacts/e22-dev1500-clip-call-map.json` (sha256
`c68aa0de…`), derived from the frozen roster receipt and re-checked against its own `ids_sha256` /
`map_sha256` on every read.

**Why that file is not a `saea-d1-evidence-supplement-v1`**, since the KC-E2 brief asked for one and
the gate cannot accept one — two structural refusals, neither incidental:

1. `contracts.gate.FrozenCoreGate.__post_init__` allows **at most one supplement per gate**, media or
   evidence, never both. This cell's dataset fragment **must** carry the `d1_media_supplement` that
   brings the `@ts2` clips into D1's closure at all; an evidence supplement would displace it.
2. `gate_evidence_identity._d1_evidence_supplement_manifest` requires the supplement's `ids_sha256` to
   **equal the carrier's own default evidence layer's sample universe**. `earnings22-original`
   declares no evidence layer at all (`data.carriers.EARNINGS22_ORIGINAL.evidence is None`), and a
   1,500-clip id set could not equal a 125-call one even if it did.

The brief's evidence records therefore carry `carrier_bound=False` and the composed config pins the
metadata table's bytes directly — the honesty `distractor-only-bias-list` and `derived-candidates`
already state for the same structural reason. D1 records this table's 125 ids through a `_csv_layer`
and no per-file manifest, so there is no per-sample evidence identity to check against and this source
does not pretend there is.

## 3. What the brief can say, per call

| call | ticker | country | UN region | dialect family | language family |
|---|---|---|---|---|---|
| 4453225 | APNHF | South Africa | Sub-Saharan Africa | Other | English |
| 4469088 | SPPJY | South Africa | Sub-Saharan Africa | Other | English |
| 4470684 | IVTJF | UK | Europe and Northern America | British Isles | English |
| 4474506 | COST | United States | Europe and Northern America | North American | English |
| 4479944 | HDB | India | Central and Southern Asia | Other | Asian |
| 4481952 | CAHPF | Australia | Oceania | Oceanic | English |
| 4482383 | PBTHF | Australia | Oceania | Oceanic | English |
| 4482613 | VEDL | India | Central and Southern Asia | Other | Asian |
| 4483937 | RNSHF | UK | Europe and Northern America | British Isles | English |
| 4485192 | EPC | United States | Europe and Northern America | North American | English |

Five distinct dialect families, four UN regions, six countries, ten tickers. **No company name**: the
table carries none, and the owner ruling forbids importing one.

## 4. The reference-side potential, per field

Coverage is a contiguous n-gram match of the call's own term against the Whisper-normalized reference
words, longest term first, non-overlapping; recall counts a covered word exactly when the frozen
aligner marks it a hit.

| field | reference words covered | recall | S | D | ceiling (corpus-WER points) |
|---|---:|---:|---:|---:|---:|
| Ticker symbol | 2 | 100.00 % | 0 | 0 | 0.0000 |
| Country | 20 | 75.00 % | 5 | 0 | 0.0190 |
| UN region | **0** | — | 0 | 0 | 0.0000 |
| Major dialect family | 23 | 100.00 % | 0 | 0 | 0.0000 |
| Language family and area | 2 | 50.00 % | 0 | 1 | 0.0038 |
| **all five** | **47** | **87.23 %** | **5** | **1** | **0.0229** |

**The only field with any error mass is `Country`**, and its entire mass is five substitutions —
concentrated in one call (4470684, recall 0.400 on five covered words) plus one call at 0.750.

| call | clips | reference words | brief-term words | hits | recall |
|---|---:|---:|---:|---:|---:|
| 4453225 | 150 | 2,662 | 10 | 10 | 1.000 |
| 4469088 | 150 | 1,946 | 6 | 6 | 1.000 |
| 4470684 | 150 | 2,581 | 5 | 2 | **0.400** |
| 4474506 | 150 | 2,993 | 2 | 2 | 1.000 |
| 4479944 | 150 | 2,773 | 10 | 10 | 1.000 |
| 4481952 | 150 | 2,166 | 2 | 2 | 1.000 |
| 4482383 | 150 | 3,015 | 1 | 1 | 1.000 |
| 4482613 | 150 | 2,386 | 5 | 5 | 1.000 |
| 4483937 | 150 | 2,567 | 2 | **0** | **0.000** |
| 4485192 | 150 | 3,162 | 4 | 3 | 0.750 |

**Six of the ten calls contribute two brief-term words or fewer.** A paired contrast whose per-cluster
denominators are 1, 2, 2, 2, 4, 5, 5, 6, 10, 10 has no interval worth quoting, whatever the estimator.

## 5. The homograph diagnostic — every term is shared vocabulary

For each term, how many of its occurrences fall in the calls whose own metadata names it, and how many
in calls whose metadata does not. A term with occurrences only in the former is a call fact; a term
that turns up everywhere is ordinary earnings vocabulary the brief happens to name.

| field | term (normalized) | own-call words | other-call words | reading |
|---|---|---:|---:|---|
| Major dialect family | `other` | 23 | 149 | shared vocabulary |
| Country | `uk` | 7 | 7 | shared vocabulary |
| Country | `south africa` | 6 | 30 | shared vocabulary |
| Country | `australia` | 3 | 3 | shared vocabulary |
| Country | `india` | 2 | 8 | shared vocabulary |
| Country | `united states` | 2 | 6 | shared vocabulary |
| Ticker symbol | `cost` | 2 | 38 | shared vocabulary |
| Language family and area | `english` | 2 | 14 | shared vocabulary |

**Call-specific share: 0.00 % (0 of 47 words).** Every single term the brief supplies is a word the
corpus also uses in calls the term does not describe. Nine of the fifteen distinct field values never
appear in any reference at all — every UN region, eight of the ten tickers, and three of the five
dialect families.

`brief-term-recall-v1` counts these words rather than excluding them, deliberately: both arms are
scored on the same reference words with the same terms, so the shared half **dilutes** an effect and
**biases neither arm**. But a verdict that quoted the pooled 87.23 % without this table would be
quoting a number that is 49 % the word *other*.

## 6. What this means for KC-E2, stated before the cell exists

This audit does not decide whether KC-E2 flies; it fixes what the cell could possibly show. Four
things follow, and the preregistration carries all four:

1. **The term channel cannot carry a claim.** 47 reference words over 10 clusters, 6 of them wrong.
   No bootstrap over 10 call clusters produces a usable interval on that denominator, and the
   preregistered `brief-term recall CI90 LB > 0` gate is, on this roster, a gate on six words.
2. **The corpus-WER channel is below the instrument's floor.** The maximum possible movement is
   0.0229 points; the same-request null on this runtime and roster is [−0.2356, +0.0692], and the
   2026-09-07 encoding preregistration already binds that "a preregistered effect smaller than about
   0.25 points on 1,500 rows cannot be distinguished from this null by one flight".
3. **The one hypothesis the audit cannot price is diffuse.** Telling the core that a speaker is
   Indian-accented or South African might improve recognition of words the brief never names. That
   effect would land on corpus WER, not on brief-term recall — and it would still have to clear the
   same 0.25-point null. The audit measures the direct channel exactly and says plainly that it
   cannot measure the indirect one.
4. **The negative result is itself worth keeping.** "This corpus's own metadata is not a usable
   knowledge source for its own transcription task" is a finding about the SOURCE, not about the
   mechanism: the KC-E1 Earnings-21 brief draws on ConEC participant rosters and press releases, a
   fundamentally richer layer, and nothing here weakens or strengthens that cell.

**What this document is not.** It is not a verdict, not an authorization and not a refusal. It is the
measurement that was supposed to exist before a GPU hour was spent, and it exists now.
