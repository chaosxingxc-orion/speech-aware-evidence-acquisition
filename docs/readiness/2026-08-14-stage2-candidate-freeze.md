# Stage-2 convergence: the frozen large-scale candidates (2026-08-14)

Per the owner's stage goals — (1) an engineering base for large-scale experiments,
(2) research topics converged into a small number of large-scale items with frozen
hypotheses, settled designs and priced budgets — this document freezes the candidates.
Stage-2's endpoint (qualified paper candidates) runs THROUGH these items; execution of
each work package below remains discovery-profile until the owner schedules it.

## Candidate B (PRIMARY): listen-score-replay — a training-free agentic policy for
## targeted multimodal knowledge consumption on a frozen speech-omni core

FROZEN HYPOTHESIS. On a frozen core, targeted re-listening — flag low-confidence spans,
retrieve entity-grade (audio, text) knowledge for them, re-decode short windows with
reference-only-framed candidates, splice by localized comparison — recovers a meaningful
fraction of knowledge-addressable entity errors at bounded extra cost (<=1.3x), where
every static supply interface measurably fails.

EVIDENCE BASIS (all registered). Static text supply: net harm at n=10 (tax +1.55pp
p=.027; four-setting replication), presence-not-content at aggregate (p=1.0), asymmetric
entity sensitivity (wrong content +4.1pp entity, right content +0.9 no-gain); the sole
positive static form (names roster: -0.28 aggregate, -7.7pp entity) is oracle-sourced
and does not generalize to deployment. Mechanism: acoustic exemplars flip rare entities
from the call's own history (Aldeyra), zero insertion side effects; inert on
morphology. Loop: airworthy at 1.18x with all decision branches exercised; short-window
re-listening carries an independent context-length benefit. Interface laws: framing is
first-order (locks cut taxes 3-4x), prompts are first-class registered variables.

DESIGN (settled). The merged obs-replay-loop policy (commits b2c530e/24deddb) on the
locked A2 serving base (90s windows, np8 evidence shape, featcache, v3 four-tier);
knowledge side = the error-pattern KB below; measurement = paired WER + entity-WER
against the locked-zero baseline, evidfloor noise discipline, pre-registered contrasts.

WORK PACKAGES.
- WP1 error-pattern KB micro-build (= MM-6): the kb-construction intersection-refusal
  gate check (designed, unbuilt); drafts for 2-3 of the frozen 34 calls; gold-offline
  confusion-pair extraction (speech span, gold text, model error text); first
  entity-grade exemplar banks. ~2h serialized.
- WP2 modality A/B on entity-grade banks (= deferred MM-2, fragments committed at
  0c136d9): text vs text+audio at identical terms. ~40min GPU.
- WP3 threshold/candidate tuning + the science pilot (= MM-4): flag thresholds swept
  offline on MM-3 traces first (zero GPU), then the tuned pilot vs baseline. ~1.5h.
- WP4 formal read: n=10 replay vs locked-zero with entity-WER, Wilcoxon. ~5h GPU.
- WP5 cross-carrier replication: contextasr-bench B-8a (unlock patch authored, 60-utt
  frozen split) + E-22. ~2h.
- WP6 speaker-indexed KB extension (ECAPA locked): additive index axis. Optional.

BUDGET ENVELOPE. Discovery caps as registered per-row; the full package ~15-20 GPU-h.
Numeric global caps stay abolished per the 2026-08-06 owner amendment; pre-registration
and one-shot attempt semantics unchanged.

## Candidate A (SUBSYSTEM, frozen jointly): the error-pattern multimodal KB
## ("错题集" — the model's own confusion pairs as retrievable knowledge)

FROZEN HYPOTHESIS. A KB of (speech span, gold text, model-error text) triples built
OFFLINE from the isolated kb-construction split (34 calls, identity 67e32336..., gold
never at runtime, evaluation-split intersection machine-refused) supplies entity-grade
labels the self-supervised path structurally cannot (measured: morphological-neighbor
capture, no cross-call occurrences for unique entities, self-labels wrong on the hardest
names) — and its error-to-error matching outperforms generic phonetic retrieval at
equal k.

STATUS. Split frozen (bea16af); anti-cheat wall specified; consumed by Candidate B's
WP1/WP2. Not an independent campaign until B's pilots justify one.

## Explicitly out of scope for this freeze
W-D / training-free-RL system optimization (owner sequencing: after both knowledge
dimensions' large-scale items run); the PO prompt-optimization protocol (parked as a
separate paper-topic candidate); np24/np32; IC-001 as an umbrella framing (its live
content is absorbed: commit-window law measured, state-carry burden priced, L4/L5 = the
replay loop itself).
