# STATUS-054: Native Audio2Tool progress and local speech tool preparation

Snapshot UTC: 2026-09-12T06:00:31.053153+00:00

## Active campaign

Keep the original session and frozen source running. The resident decoder remains /home/chao/saea-worktrees/a2t-native-assembly-v1 at 7539aab510473b2e1dd1df02a9af3185c084478b. The campaign source remains /home/chao/saea-worktrees/a2t-native-campaign-v1 at cbc53ac0c36bed94fdb50c3b069a74569d935720. Serving session: serving-a2t-native-system-np3-v1, decoder-only, c98304, np3, max1024, no mmproj.

Metadata-only attempt snapshot:

{
  "DIRECT": [
    {
      "state": "FINALIZED",
      "calls": 4000
    }
  ],
  "STAGE-CONTROL": [
    {
      "state": "OPENED",
      "calls": 3250
    }
  ],
  "KNOWLEDGE": []
}

Calls are charged generation contacts, not a claim about correctness. DIRECT is finalized after complete scoring. Current quality results have not been read by root. Wait for all three complete manifests to seal before semantic inspection. Continue automatic deferred full scoring; never rescore for missing diagnostics.

## Analysis source

Isolated development source: /home/chao/saea-worktrees/a2t-native-analysis-v1. Shared pooled analysis now supports whole-cluster resampling across strata and explicit scorer-zero denominators. Shared score_compare_cli supports opt-in generic projections from complete score receipts or finalized score attachments, with exact native roster IDs. Legacy default behavior is retained.

Validation: 92 related synthetic/unit tests passed; Ruff, engineering base check and whitespace check passed. No current score or answer was read.

Freeze the statistical recipe in docs/readiness/2026-09-12-a2t-native-system-analysis-recipe.json. Actual finalized source and metadata pins remain to be bound after the full-seal gate. Full native official per-row mean metrics and official pooled parameter F1 are available. Ordered full-call-with-arguments accuracy is not persisted; repo v2 micro slot counts are not persisted per row. Label those limits explicitly and do not substitute another metric under their names.

## Owner steering and work in progress

OWNER-E21-QUALITY-PRIORITY-022 applies only to future E21 registrations.

OWNER-SPEECH-TOOLS-023 records local speech tool preparation and the confirmed high-confidence suspected-error trigger. Full design: docs/readiness/2026-09-12-speech-tool-system-plan.md.

Acquisition is in progress in /home/chao/speech-tools with isolated environments. Whisper/VAD, FFmpeg local dependency closure, and alignment/diarization inventory/download run independently without using GPU or research data. No new ASR or speech-tool forward pass has occurred.

## Immediate continuation

1. Keep the resident/campaign/ten-second monitor alive and observe only accounting/health metadata.
2. Complete local tool acquisition, pin hashes and prove local load status; report any gated access.
3. Bind and run the frozen shared score analysis after all three seals and complete first scoring.
4. Decide current system contribution from native metrics, then register the first matched SLURP speech-tool comparison.
5. Keep Reviewer, Planner and Solver authority separate; add live auxiliary OBS accounting to the shared tool contract before dataset use.
