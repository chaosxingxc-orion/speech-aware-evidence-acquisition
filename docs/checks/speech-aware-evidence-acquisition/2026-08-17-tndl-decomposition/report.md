# T-NDL: number/date error mass, three-way decomposition

**Headline arm** `SAEA-P2-r1verify` (2,873 wrong mentions) · **control** `SAEA-P2-r0bias` (2,822) · 10 earnings21 calls.
**Provenance:** D5 archival replay of already-consumed traces. Zero model contact, no attempt dir touched, CPU only, no exposure row required.

## The three fractions

Of all 2,873 wrong entity mentions:

| Fraction | Mentions | Share |
|---|--:|--:|
| **FORMAT** (writing convention only) | 1,921 | **66.9%** |
| **PRE-PUBLISHED** (value is in the call's own ConEC materials) | 527 | **18.3%** |
| **NOVEL** | 425 | **14.8%** |

Restricted to the number/date classes (2,082 mentions):

| Fraction | Mentions | Share of numeric mass |
|---|--:|--:|
| **FORMAT** | 1,800 | **86.5%** |
| **PRE-PUBLISHED** | 178 | **8.5%** (chance floor **4.3%**) |
| **NOVEL** | 104 | **5.0%** |

r0bias agrees within ~1 point everywhere (85.9 / 9.3 / 4.9), so this is a corpus property, not one decode.

## Recomputed class share — the ~84.75% reconciled

| Grouping | r1verify | r0bias |
|---|--:|--:|
| Number/date proper (CARDINAL, DATE, YEAR, PERCENT, MONEY, ORDINAL, TIME, QUANTITY, ALPHANUMERIC, RANGE) | 2,082/2,873 = **72.47%** | **71.62%** |
| + CONTRACTION, ABBREVIATION (non-name mass) | 2,429/2,873 = **84.55%** | **84.34%** |
| + WEBSITE | 2,435/2,873 = **84.75%** | 84.55% |

**84.75% is the non-name mass with WEBSITE included, not the number/date share.** Number/date proper is **72.5%**; the extra 12 points are CONTRACTION/ABBREVIATION, which behave completely differently (only 15.3% FORMAT).

Two corrections, both cutting the same way:

1. **Multi-labelling inflates numbers.** `wer_tags` gives one numeric token up to three entity ids (YEAR *and* CARDINAL *and* DATE); a company name gets one ORG id. 593 of 2,954 distinct wrong tokens carry 2–3 labels. Over **distinct tokens**, numeric falls to 70.2%, non-name to **79.5%**, and NAME rises 15.4% → **20.5%**.
2. **Part of the residual is a reference defect.** Call 4365024 token 95 is literally `199` inside "Securities Litigation Reform Act of 199"; token 575 is `201`. The hypothesis said "nineteen ninety five" — correctly. Each defective token manufactures three wrong mentions; 49 mentions match just the three strings probed.

## Per-class table (r1verify)

| class | grp | wrong | FORMAT | PRE-PUB | NOVEL | fmt% | prepub% | novel% | decoy% |
|---|---|--:|--:|--:|--:|--:|--:|--:|--:|
| CARDINAL | NUM | 739 | 665 | 58 | 16 | 90.0% | 7.8% | 2.2% | 4.2% |
| DATE | NUM | 349 | 243 | 46 | 60 | 69.6% | 13.2% | 17.2% | 4.6% |
| PERCENT | NUM | 279 | 265 | 11 | 3 | 95.0% | 3.9% | 1.1% | 3.6% |
| YEAR | NUM | 277 | 238 | 37 | 2 | 85.9% | 13.4% | 0.7% | 9.4% |
| ALPHANUMERIC | NUM | 218 | 203 | 4 | 11 | 93.1% | 1.8% | 5.0% | 0.5% |
| CONTRACTION | CONV | 213 | 50 | 54 | 109 | 23.5% | 25.4% | 51.2% | 3.8% |
| ORG | NAME | 184 | 4 | 92 | 88 | 2.2% | 50.0% | 47.8% | 6.0% |
| MONEY | NUM | 175 | 150 | 18 | 7 | 85.7% | 10.3% | 4.0% | 3.4% |
| ABBREVIATION | CONV | 134 | 3 | 62 | 69 | 2.2% | 46.3% | 51.5% | 8.2% |
| PERSON | NAME | 95 | 6 | 61 | 28 | 6.3% | 64.2% | 29.5% | 2.1% |
| GPE | NAME | 71 | 9 | 56 | 6 | 12.7% | 78.9% | 8.5% | 39.4% |
| EVENT | NAME | 35 | 31 | 1 | 3 | 88.6% | 2.9% | 8.6% | 0.0% |
| PRODUCT | NAME | 34 | 16 | 13 | 5 | 47.1% | 38.2% | 14.7% | 0.0% |
| ORDINAL | NUM | 28 | 25 | 2 | 1 | 89.3% | 7.1% | 3.6% | 0.0% |
| FAC | NAME | 9 | 1 | 2 | 6 | 11.1% | 22.2% | 66.7% | 0.0% |
| TIME | NUM | 9 | 5 | 1 | 3 | 55.6% | 11.1% | 33.3% | 0.0% |
| QUANTITY | NUM | 7 | 6 | 0 | 1 | 85.7% | 0.0% | 14.3% | 0.0% |
| WEBSITE | NAME | 6 | 0 | 6 | 0 | 0.0% | 100.0% | 0.0% | 0.0% |
| LOC | NAME | 4 | 1 | 2 | 1 | 25.0% | 50.0% | 25.0% | 0.0% |
| NORP | NAME | 4 | 0 | 0 | 4 | 0.0% | 0.0% | 100.0% | 0.0% |
| WORK_OF_ART | NAME | 2 | 0 | 0 | 2 | 0.0% | 0.0% | 100.0% | 0.0% |
| RANGE | NUM | 1 | 0 | 1 | 0 | 0.0% | 100.0% | 0.0% | 0.0% |
| **NUMERIC** | | **2082** | **1800** | **178** | **104** | **86.5%** | **8.5%** | **5.0%** | 4.3% |
| **CONVENTION** | | **347** | **53** | **116** | **178** | **15.3%** | **33.4%** | **51.3%** | 5.5% |
| **NAME** | | **444** | **68** | **233** | **143** | **15.3%** | **52.5%** | **32.2%** | 9.2% |
| **ALL** | | **2873** | **1921** | **527** | **425** | **66.9%** | **18.3%** | **14.8%** | 5.2% |

`GPE` shows why the decoy control matters: 78.9% apparent coverage against a 39.4% decoy rate, because GPE mentions are short strings like "US".

## Method (two things worth knowing)

**Recovering the substitution.** The frozen `align()` exposes only a hit mask and, per `core/scorers.py`, "no way to name WHAT incorrect text a hypothesis substituted". `tndl_lib.align_trace` mirrors the frozen DP and its tie-break order and adds the ref→hyp map, vectorised via the prefix-minimum identity (algebraically identical, not approximate). **Proven, not asserted:** 300 randomised pairs reproduce `align()`'s mask, and per-sample/per-class counts reproduce *both* committed frozen-scorer artifacts exactly — 10/10 samples, 23/23 classes, both arms.

**Normalizer tiers.** Comparison runs on RAW text, since `normalize_text_v1` is frozen with no number expansion and itself destroys `$ . % , -`. Stdlib only (no `num2words`/`inflect` installed, installs banned). Number-word runs yield a *set* of readings ("twenty twenty" = 40 or 2020); matching slides over contiguous sub-spans. Tiers on numeric mass: strict **17.9%**, **window 86.5%** (headline), value 87.0%. `#pct` and ordinal markers are retained (19 vs 19% is a content error); currency markers are dropped because gold cuts `$6.5` from its `million`. The normalizer is *conservative* — possessives ("second quarter's 2020") stay in the surviving mass.

## ConEC coverage caveats

- **The ready-made biasing lists cannot reach numbers by construction.** ConEC's own README: `contexts/*.txt` are extracted from the PDFs "with stop words, **numerical values** and irrelevant pages removed". All number coverage must come from the PDFs.
- **PDF extraction was stdlib-only** — no `pdfminer`/`pypdf`/`PyMuPDF` installed, installs prohibited. `pdf_cmap.py` inflates streams with `zlib` and decodes subsetted CID fonts via the PDFs' own `/ToUnicode` CMaps. One deck (`4384964_1.pdf`) has no CMap; its constant glyph offset was found by search and accepted only because it passes the same English-looking gate (textiness 0.996, offset 29 → "2020 Third Quarter Results November 4, 2020 Safe Harbor Statement…"). **All 11 PDFs for the 10 calls extracted.** CMaps are merged across fonts, so this layer is used for substring *presence* only, never as a transcript.
- **Two of ten calls have no PDF at all** (`4366522`, `4385072`) — their pre-published fraction is a floor; `4385072` is the corpus low (18/257).
- **Licensing unresolved.** Paper is CC-BY-NC-4.0; the checked-out repo has **no dataset-level LICENSE** (only `README.md`, `earnings21/`, `earnings22/`). The README asserts public filings + SeekingAlpha lists, which supports *legality* of inference-time supply, but NC terms plus the missing licence mean **any deployment-tier claim on ConEC needs a licensing review**. This is discovery-tier and makes no deployment claim.
- Coverage is *string presence*, not retrievability — a real SUPPLY path must still find the span in a 200k-char deck. These are **upper bounds**.

## Is a span→gold KB worth building?

**For numbers/dates: no.** 1,800 of 2,082 numeric errors (86.5%) are already correct in the hypothesis, just written differently. The reachable residue is 178, of which the decoy floor eats 4.3 points — **net ~88 mentions, ~3.1% of total error mass**, and some of that is reference defects, not model errors. A number-targeted KB would spend its whole budget on ~3% of the mass, against a normalizer that reaches 86.5% of it with a few hundred lines of deterministic, model-free, zero-latency code.

**This is a scoring finding, not a capability finding.** The core is not missing these facts; it emits them in spoken form while the reference stores written form. So the ~84.75% is *not* 84.75% of addressable headroom.

**If a KB is admitted, scope it to names:**

| | numeric | name |
|---|--:|--:|
| share of error mass (mentions) | 72.5% | 15.4% |
| share of error mass (distinct tokens) | 70.2% | **20.5%** |
| FORMAT | 86.5% | 15.3% |
| PRE-PUBLISHED | 8.5% (decoy 4.3%) | **52.5%** (decoy 9.2%) |
| PRE-PUBLISHED, 5+ char keys | 33.9% (decoy 5.1%) | **54.2%** (decoy **0.0%**) |
| NOVEL floor | 5.0% | 32.2% |

ORG (184 wrong, 50.0% pre-published), PERSON (95, 64.2% at a 2.1% decoy rate) and PRODUCT (34, 38.2%) are reachable from materials known before the call starts — participant name lists especially: short, high-precision, legal by construction.

**Recommended sequencing:** (1) don't build a number/date KB — instead settle whether entity-WER should be scored under written/spoken normalization, since 66.9% of all wrong mentions would flip; (2) re-run N1 routing against the surviving ~952 genuinely-wrong mentions, not 2,873 — the 0.94% recall figure isn't interpretable until then; (3) if a KB is admitted, scope to names and pre-register the 32.2% NOVEL ceiling; (4) report distinct-token shares alongside mention shares and separate 72.5% (number/date) from 84.6% (non-name).
