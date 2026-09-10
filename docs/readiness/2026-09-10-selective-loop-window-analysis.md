# Selective LOOP delivery verification

The ordinary selective repair trace carries one terminal OBS record per selected
re-listen, with predecessor backfill in its delivered text. Treating those
contacts as fixed analysis windows loses the full predecessor grid.

The shared saved-score reader now detects selective OBS records and invokes
analysis.e21_selective_loop_windows.verified_selective_loop_windows. Supply
analysis.repo_root and analysis.data_root as retained source and data locations.
The source checkout must remain at the generation manifest's study commit; its
four fragment identities and composed hash must match that manifest. Existing
loaders verify the pinned predecessor snapshot and selective unit plan.

The verifier reuses RepairWindowHook.accept, the same terminal normalization and
registered delivery rule used during generation. It verifies exact plan ranges,
audio bounds, request identity/hash, output cap, retry terminal, usage/saturation,
skip fallback, backfill fields and complete stitch order. It reconstructs every
fixed predecessor window; unselected text remains byte-identical and selected
text can change only through the registered word-range delivery. Changed
responses are never selected by score.

This analysis invokes no model, encoder, reference loader or official scorer.
The complete official scorer runs once per ordinary parent with per-sample
alignment. The saved-score reader then partitions that existing alignment over
the verified full window grid. Both arms retain 44 calls and 1,593 windows;
600 is the planned contact count, not the analysis population.

Root implemented and reviewed the production verifier after identifying
omissions in the helper's initial draft. The helper supplied synthetic
regressions. Validation: 86 selected reader, repair, alignment and selective
trace tests passed; the engineering base check passed. Production generation
code and active source are unchanged.
