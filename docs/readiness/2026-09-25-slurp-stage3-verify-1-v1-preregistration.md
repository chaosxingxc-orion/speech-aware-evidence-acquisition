# VERIFY-1: speech-grounded selection of sealed candidate answers

## Authority and question

The owner approved the ChatGPT continuation implementation on 2026-09-25.
Continue Fable F11: can the same frozen core select a better existing answer given
original speech and five sealed Solver candidates? This is bounded discovery, not
system admission or a test claim. Preserve old sealed-manifest behaviour.
Keep R01C 625, existing speech features, np4 x 24576, max512 and no retrieval/tools.

## Frozen prospective amendments to the inherited draft

Use balanced-block-v1, seed 20260925, over the complete source roster. Each source
index appears in each position exactly 125 times. Smoke uses the same assignment.
Primary analysis retains all 625 rows; separately report content-distinct 420,
all-parsed 414, identical 205 and score-disagreeing 225. Six rows containing malformed
source candidates remain visible. Invalid choice fallback is sealed source index 0.

Use official pooled word/character counts, paired utterance bootstrap, 10,000 draws,
seed 20260915. Positive CI95 lower bound versus mean-single plus intent NI at the
frozen R01C operational margin permits later Reviewer design, not system admission.
Keep medoid, sample 0 and metric-limited oracle references separate. Histograms
diagnose bias; their non-significance does not prove absence of semantic selection.
Reuse sealed counts without rescoring. Never report only a favourable subset.

## Execution

Smoke caps: 8 generation, 8 fit calls, 37 audio seconds, 0.2 GPU-hours.
Full caps: 1,250 generation, 1,250 fit calls, 5,454 audio seconds, 1.0 GPU-hour; expected 625
generation calls. These are inherited local bounds, not programme budget limits.
Mandatory full-roster real-request fit precedes generation; dry run only estimates.
Use existing WSL scheduled batch driver, attach-only service and exclusive lease.
The immutable flight continues without Codex, network or assistant credits.
Stop and preserve failures; never auto-replay. No new DEV-remainder or test read.

The primary mean-single comparator pools the uniform mean of the five candidates'
official counts per row. This differs from averaging five separately computed
nonlinear pooled F1 values; preserve that estimand label in the report.
