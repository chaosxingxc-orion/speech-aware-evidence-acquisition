# N10 block + metadata replication verdict (2026-08-15)

Four arms, one night, zero failures: SAEA-E-005B-N10-{zero,matched,names} (the standing
2026-08-13 registration, relaunched after three environmental startup deaths) +
SAEA-P1R-metadata10. Identical frozen ten (split 744c4b2e...), 342 calls / 30,407 audio-s
per arm, study_commit c28e3a4, wall 5h35m total, one intervention (clock-lock re-apply).
Offline entity reads: derived/entity-wer/<run>/.

## Numbers (n=10 calls, paired)

| arm | macro WER | Δ vs zero | Wilcoxon | entity correct /8284 | entity-WER | prompt tok | GPU-s |
|---|---|---|---|---|---|---|---|
| zero (locked) | 12.38 | — | — | 5632 | 32.01 | 416k | 3898 |
| matched n=10 bag | 12.39 | +0.01 | n.s. | 5873 (+241) | 29.10 | 1671k | 4953 |
| names roster (oracle-sourced) | **10.88** | **-1.50** | **p=.027** (9/10) | **6631 (+999)** | **19.95** | 468k | 3963 |
| metadata roster (deployment-legal) | 12.09 | -0.30 | p=.19 (7/10) | 5749 (+117) | 30.60 | 451k | 3883 |

SCOPE AMENDMENT (2026-08-15, owner discussion): every "ceiling" in this document is the
ceiling of STATIC-BIAS DELIVERY only — knowledge consumed as a prompt-prior that shifts
decoding. The REFLECTION delivery family (per-span: audio + the model's own errored draft +
retrieved reference, verify-against-audio with abstention) is a different operator, is NOT
bounded by these numbers, and has never been measured in this program (the P1-D vehicle
failed before it could engage). The oracle-names 10.88 therefore anchors the bias family's
best case, not knowledge value overall.

## Law revisions (scale-grade, supersede the fast-3-era readings)

1. **The n=10 macro tax is ZERO under locked framing.** The historical +1.55pp tax was the
   generic-framing era; with the locked reference-only instruction the full bag costs nothing
   on macro. The full-bag penalty is now purely EFFICIENCY: 4.0x prompt tokens, +27% GPU-s,
   +20% wall (decode drops ~40% under the 4.2x KV context).
2. **Right content pays on entities at scale** (+241 for matched): the fast-3 "right content
   no-gain (+0.9)" reading was underpowered, not wrong-signed.
3. **Form dominates dose — the keystone.** The small cased names roster beats the full bag by
   1.51pp macro / +758 entity tokens at ~1/4 the token cost: -1.50pp macro (p=.027, 9/10
   calls), entity-WER 32.01 -> 19.95. Sole loss: 4389907 (+2.20, the hardest audio).
4. **The deployment-legal metadata roster replicates directionally at scale**: -0.30pp macro
   (7/10 calls, n.s. at n=10), +117 entities, and ~20 distinct rare names flip from a purely
   legal source (Aldeyra 0->6, Chumbley 0->1 — the reachability partition's a2 anchor class —
   Culp 1->9, Nextar 4->15, Frenz, Horne, Kusera, Horvers, Rafeh, Masood, Basham, Kotkin,
   Vashist, Valiquette, Sitime, Dearth, ...). It recovers ~20% of the oracle-names macro
   effect and ~12% of its entity effect. One regression: 4366522 +1.27 (format-drift suspect,
   the measured instruction-controlled number axis).
5. **The oracle-vs-legal gap is LABEL COVERAGE, not mechanism**: metadata carries only
   company + speakers; the names roster carries every error-prone entity. The path to closing
   the gap is the pinned tier-3 document-label route (IR pages / filings resolvable from the
   call's own metadata) — exactly the reachability partition's largest stratum (a2, 32.9% of
   error mass).

## Consequences

- Candidate B's supply claim now has scale-grade evidence in its strongest form: static
  small-N roster supply, deployment-legal source, both-ledgers-positive direction, p=.027 for
  the form's ceiling (oracle names). The frozen hypothesis wording (targeting / small-N
  supply, prompt-delivery co-primary) is confirmed by the delivery fork AND by scale.
- Next levers in value order: (i) tier-3 document-label materialization to close the roster
  coverage gap toward the names ceiling; (ii) the entity-aware flag (offline harness: S1
  roster-anchored band, proper-name P@1 0.252 vs production 0/17) to route TARGETED supply;
  (iii) the format axis (bounds metadata's 4366522 regression); (iv) the replay pass-1
  exemplar-hijack fix (defect, docs/readiness/2026-08-14-p1-ceiling-verdict.md) before any
  further splice-delivery measurement.
