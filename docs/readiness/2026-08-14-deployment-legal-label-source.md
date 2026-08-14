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
