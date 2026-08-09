# What the ConEC "context materials" actually are (2026-08-09)

Checked directly because the B-2a build reported an unexpected file shape, and
the answer changes how R4's result must be read. Read-only inspection of all
44 files in `datasets/conec/earnings21/contexts/`.

## Finding

They are **unigram word-frequency lists**, not prose documents:

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

## Blocking gap found during the build (owner attention needed)

`core.driver.run_experiment` binds evidence identity by hashing the carrier's
**raw ConEC per-sample file** and checking it against D1
(`verify_evidence_content_identity`). Any evidence source that **transforms**
that content — the capped bias list, the reconstructed phrases, or the
carrier-independent distractor list — will fail that check on a gated run.

The rail is correct (what enters the prompt must be identity-verified); it was
simply designed for verbatim evidence. The fix should mirror the pattern this
repo already uses for derived audio: `core/model/slices.py` chains a derived
slice to its parent via `parent_sha256` + offsets. Derived evidence should
likewise carry a record chaining **verified source file hash + pinned
transform version → derived content hash**, so identity remains provable
without requiring the derived artefact to pre-exist in D1.

Until that lands, B-2a arms 2–4 cannot run against the frozen core. R4 is
unaffected (it injects the raw file verbatim).
