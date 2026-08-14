# The multimodal-knowledge ladder (MM series) — verdict (2026-08-14)

Owner framing that opened this ladder: text knowledge injection closed (matched text is
unavailable at real evaluation time); the question became whether MULTIMODAL knowledge has
value, explored in 30-35-minute baby steps, each with a pass/stop read. Standing GO for
exploration-level steps. All rows registered; smokes ran on manually-spawned servers per
the serving-bench precedent.

## MM-0 — arms unlocked (commit 4281053)
exemplar-context + fixed-legal-context-replay merged (D2 receipts regenerated via the real
generator); real-tree suite verified directly after fixing this session's test-runner,
which had been cd-ing into a stale agent clone (a real verification-infrastructure bug).

## MM-1 — the keystone: mapping ability EXISTS, precisely where it matters
SAEA-SMOKE-mapflip, three probe rounds (22/40 calls):
- Round a (word-fraction targeting): invalidated by its own forensics (3/5 wrong-slice).
- Round b (lexicon-anchored 24s windows): common-word morphology does NOT flip
  (significant/maintain — the LM prior wins); one morphological-form flip
  (presentations->presentation); one position perturbation. BONUS: the short-window
  control itself repaired several full-slice errors — a context-length recognition
  effect, an independent benefit source for short-window re-listening.
- Round c (entity target, OWN-CALL history exemplar): **Aldera -> Aldeyra flipped clean,
  with a spillover RAS -> RASp**, zero text changes elsewhere. Across all 11 probe pairs:
  ZERO insertion side effects (the verbatim-only constraint held everywhere).
Verdict: acoustic exemplars apply sound-to-spelling mappings on rare entities (weak prior
zone) and are inert on common-word morphology (strong prior zone). Deployment-legal in
its strongest form: the exemplar came from the call's own earlier audio.

## MM-5 — self-supervised banks: pipeline built, role corrected
Materializer (lexicon -> mc2-schema banks, round-trip validated through core.exemplars)
delivered v1 and rarity-biased v2. Honest structural finding: fuzzy correction-retrieval
over draft-aligned vocabulary CANNOT reach entities — morphological neighbors own the
top-k; sample-unique entities have no cross-call occurrences; own-call self-supervised
labels are wrong exactly on the hardest names (the draft teaches "Alderis"). Role
re-scoped: general-vocabulary banks. Entity-grade banks require the error-pattern KB
(gold offline, kb-construction split) — MM-2 modality A/B deferred to that bank.

## MM-3 — the agentic loop flies; the smoke earns its keep
Three flights, three real-payload defects the fixture suite could never reach, each fixed
with its incident fingerprint (commits 1e8c891, 19ecad1, 24deddb):
1. MMS aligner alphabet (raw transcript capitals crashed LOCATE);
2. id_slot per-sample sentinel unresolved on one-off REPLAY requests;
3. ACCEPT judged the whole window transcript against a 2-word flagged run (12/12
   impossible rejects) + RETRIEVE self-matched the flagged word at 1.0 — fixed with
   localize-before-judge (align replay text to window audio, splice only overlap words)
   and correction-semantics filtering (incl. no-candidates skip that saves the call).
Final flight (attempt f85d93): 10 REPLAY records — 6 accepted localized splices (incl. a
live entity-correction attempt: 'from Fang' -> 'comes from Feng.', candidates carrying
'ifeng'), 2 correct do-nothing rejects on hold-music catastrophe slices, 1 no-candidates
skip (model call saved), 1 no-overlap reject. Cost 1.18x (<=1.3 bar). WER 15.28 vs the
matched baseline's 14.99 — untuned thresholds, bag-pool candidates, zero exemplar
matches: mechanical PASS, science quality explicitly deferred to the frozen candidate's
tuning work package.

## Ladder disposition
MM-0/1/3/5 complete; MM-2 and MM-4/6 fold into the frozen large-scale candidate's work
packages (2026-08-14-stage2-candidate-freeze.md). The ladder's product: the mechanism
proof, the loop's airworthiness, the bank pipeline, and three production defects that
never reach a campaign.
