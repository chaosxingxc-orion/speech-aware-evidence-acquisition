# What the ConEC "context materials" actually are (2026-08-09)

Checked directly because the B-2a build reported an unexpected file shape, and
the answer changes how R4's result must be read. Read-only inspection of all
44 files in `datasets/conec/earnings21/contexts/`.

## Finding

> **Correction (2026-08-10).** "Word-frequency list" is wrong. Every count
> field is **1** in every file checked (4365024: 0 of 715 lines above 1;
> 4366429: 0 of 811; 4385072: 0 of 272; 4397829: 0 of 1,057). These are
> **deduplicated token sequences in document order**, and the trailing number
> carries no information at all. Document order is genuinely preserved and
> readable — 4397829 opens `january bed bath beyond mark tritton president ceo
> gustavo arnal cfo treasurer rafeh masood john hartmann`, which is the
> participant roster with function words stripped. That matters: adjacent
> tokens often *are* the two halves of a real entity, so reconstruction from
> adjacency is better founded than the original framing below suggested — but
> only in roster and headline regions. Boilerplate regions (4330115 opens with
> `investor kit news release print rss feeds receive email alerts view
> contacts printerfriendly version`) yield almost nothing. See
> `docs/arms/b2a-bias-lists.arms` for how this bounds the B-2a reading.

They are **unigram word lists**, not prose documents:

```
holleder 1 / parkway 1 / rochester 1 / new 1 / york 1 / contact 1 / kim 1 /
rudd 1 / executive 1 / assistant 1 / investors 1 / media 1 / melanie 1 ...
```

- one lowercase token per line with a trailing count
- **0 of 44 files contain any line longer than 8 words** — there is no prose
- 745–947 lines typical (median file 7.4 KB); uncapped distinct candidates per
  call: min 102, median 677, max 2,149

**Provenance is document-derived, not transcript-derived** — the content reads
as press-release material ("contact kim rudd executive assistant investors
media" is a contact block; "cementos argos reports first quarter financial
results" is a headline). So the leakage boundary is intact: this is
pre-existing real-world context, unlike the E-21 `oracle_list`, which its own
README says comes from the reference transcripts.

## Consequences

1. **R4's `matched` arm is contextual-biasing by word list, not document
   injection.** Every description of it as "slides / press releases" was
   imprecise; what reaches the prompt is a bag of words distilled from those.
   The mechanism under test is "does a bag of relevant words improve
   transcription", which is the Siskos/ConEC family — but the paper-style
   phrasing overstated the richness of what we supply.
2. **Multi-word entities are fragmented.** `GOLDMAN SACHS` arrives as
   `goldman` and `sachs`, lowercased, on separate lines. Biasing toward
   multi-word proper nouns — exactly the hard case in this domain — is
   therefore weakened by the format itself. If the matched arm shows no gain,
   **format is a live alternative explanation to "context does not help"**,
   and the R4 write-up must say so rather than concluding the mechanism failed.
3. **B-2a's `conec-bias-list` arm is largely redundant with R4 `matched`** —
   the only difference is the 100-entry cap versus the full ~677. Keeping it
   as designed would spend a probe re-testing a dose point.

## B-2a redesigned again (second revision)

The materials being word lists makes the interesting open question **form**,
not source:

| arm | content | question |
|---|---|---|
| none | — | baseline |
| unigram bag (as shipped) | the raw ConEC list, capped | = R4 matched, dose-capped |
| **reconstructed phrases** | the same tokens re-assembled into multi-word entity candidates (roster/headline order preserved from the source file) | **does FORM matter at equal content?** |
| distractor-only | the 769 non-corpus names | negative control |

The phrase-reconstruction arm is the one with no published answer, and it is
cheap because the source and the scorer are already in place. Note the
reconstruction must come from the ConEC file's own line order (which preserves
document order), never from the reference transcript.

## Blocking gap found during the build — CLOSED (2026-08-09)

`core.driver.run_experiment` bound evidence identity by hashing the carrier's
**raw ConEC per-sample file** and checking it against D1
(`verify_evidence_content_identity`). Any evidence source that **transforms**
that content — the capped bias list, the reconstructed phrases, or the
carrier-independent distractor list — failed that check on a gated run.

The rail was correct (what enters the prompt must be identity-verified); it
was simply designed for verbatim evidence. The fix mirrors the pattern this
repo already uses for derived audio (`core/model/slices.py`'s
`SliceRecord`/`SliceRegistry`, which chains a derived slice to its parent via
`parent_sha256` + offsets, re-verified at registration and again at send):
a new `core.base.DerivedEvidenceRecord`
(`{sample_id, source_relpath, source_sha256, transform_name,
transform_version, params_hash, derived_sha256, carrier_bound}`) chains
**verified source bytes + a registered, pinned, versioned transform + the
run's own declared params → the derived content actually sent**, and
`core.evidence_derivation.DerivedEvidenceRegistry` re-derives every one of
those links independently (never merely re-hashing the record's own
numbers), refusing with a message naming exactly which link broke: SOURCE
(tampered/substituted source bytes), the transform itself (unregistered name
or a registered name at the wrong pinned version — condition 5 makes an
unregistered/unversioned transform impossible to reach at all), PARAMS (the
record's claimed params disagree with what this run's config actually
declares), DERIVED CONTENT (re-invoking the pinned transform does not
reproduce the claimed hash), or SENT CONTENT (the bytes about to reach the
prompt were tampered after derivation). `core.driver.run_experiment` runs
this check for every sample before a run proceeds, BEFORE the (unchanged) D1
evidence-identity rail, which now checks the SOURCE bytes a `carrier_bound`
record chains to rather than the transformed output.

`conec-contexts` carries a genuine record too, using the `identity`
transform (`core.evidence_derivation.TRANSFORMS`) — content is unchanged,
byte-identical to before this rail existed, and the pre-existing driver test
asserting on it stayed green throughout. `conec-bias-list`'s record is
`carrier_bound=True` (its source is the same per-sample ConEC context file
`conec-contexts` reads, still D1-verified). `distractor-only-bias-list` gets
the honest carrier-independent treatment: it derives from the shared
`bias_lists/` corpus, not a per-sample carrier file, so its record is
`carrier_bound=False` and chains to a combined, self-verified hash of the two
shipped files rather than fabricating a D1 binding it cannot back up.

B-2a arms 2–4 can now run against the frozen core (subject to the usual
exposure-ledger/execution-plan discipline — this change is model-free
engineering, not an authorization to touch the model). R4 was, and remains,
unaffected (it injects the raw file verbatim).
