# Deployment-legal text-label source pin (P0.3, 2026-08-14)

Adversarial review wf_f412e338 withdrew KX-Q2's "deployment-legal form" claim: the Aldeyra
flip's text label was gold-derived at selection time. This pin defines what a deployment MAY
use for candidate/exemplar TEXT labels; gold/reference transcripts and their derivatives
remain banned from runtime.

Pinned source hierarchy (all inference-time-available):
1. Call metadata (primary): the earnings-call's own title/company/ticker fields as shipped in
   the earnings21-original asset metadata. The Aldeyra case is covered: the call's company
   name carries the exact spelling "Aldeyra".
2. Participant rosters / speaker labels shipped with the call container (when present).
3. Public issuer documents resolvable from (1) offline: IR page titles, filing headers —
   PRE-FETCHED into a versioned, hashed materialization before any run consumes them
   (derived-candidates discipline; no live network at runtime).

Explicitly NOT legal: reference transcripts, test annotations, any derivative of gold tokens
— including gold-guided SELECTION of which terms to supply (the P1 oracle materialization is
therefore a ceiling instrument only, never a method).

Scheduled probe (next GPU slot): SAEA-P1-metadata — the deployment-legal analogue of P1 arm C.
Same fast-3, same locked reference-only framing, same v3 shape; candidate lists built ONLY
from source (1)+(2) with NO gold-guided selection (company name, ticker, speaker names —
small-N roster form, alphabetized). Reads: metadata-arm vs locked-zero 14.48 on both ledgers
+ the targeted flip count (does Aldeyra 0->6 survive the legal source?); vs P1-C bounds how
much of the oracle ceiling metadata alone recovers. This replaces the earlier <=16-request
MM-1-style re-demo (a full arm is the same GPU class and yields both ledgers).

P1 context: static oracle candidates flipped 10/14 targeted rare entities (Aldeyra 0->6) at
+0.51pp aggregate collateral tax — see 2026-08-14-p1-ceiling-verdict.md. The metadata arm
tests whether the deployment-legal subset of that value survives with the same small-N form.

## RESULT (2026-08-14, SAEA-P1-metadata, commit c134038) — the probe WON on every ledger

- Macro 14.29% — best of all four supply arms (locked-zero 14.48, re-listen 14.56, oracle-C
  14.99). Per-sample better than oracle-C on all three calls.
- Entity ledger 813/1310 correct (37.94% entity-WER) — +31 vs zero-knowledge re-listen (782),
  +62 vs oracle-C (751): the FIRST supply arm to improve the aggregate entity ledger.
- Targeted flips under the legal source: Aldeyra 6/6, Frenz 2, Horne 1 — plus roster names the
  oracle selection did not even include: Kusera 1, Bistricer 3.
- Typo probe (benign failure mode): the metadata's own "Pheonix" was supplied verbatim; the
  core output "Phoenix" x2 correct, zero occurrences of the typo — the LM prior normalizes a
  wrong supplied form instead of being poisoned by it. ("Micheal Frenz" analogous: surname
  landed.)
- Residual number-format drift present but milder than oracle-C (twenty-twenty spellings on
  2 of 3 calls) — the format-pinning instruction variant (SAEA-P1-metadata-fmt) tests whether
  one instruction line recovers it.

CLAIM RESTORATION. KX-Q2's withdrawn "deployment-legal" claim is re-established on the TEXT
side, stronger than originally worded: a zero-training, zero-retrieval, deployment-legal
static roster from the call's own metadata improves BOTH ledgers over the locked-zero
baseline and flips the anchor rare entity 6/6 with correct casing. The acoustic-exemplar
version of the claim (own-history audio + document label) remains open pending a fixed
replay vehicle (see the P1 verdict's defect note).
