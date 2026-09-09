# KU-S4N G2 model-free preparation registration

Register `SAEA-SLURP-KU-S4N-G2-PREPARE-V1` before reading or producing new preparation artifacts. This is CPU-only preparation for the accepted G2 N/twin pair; it does not admit generation, tokenization, encoding or scoring.

Use the committed successor configurations `slurp-kus4n-candidates-successor-v1` and `slurp-kus4n-candidates-twin-successor-v1`, their fixed generation cell/attempt identities, the existing full DEV-1000 roster, candidate bank and knowledge snapshot. Verify the bank by file SHA-256 and the snapshot by its canonical KnowledgeSnapshot content hash, as the common runtime does. No new roster or reference labels enter runtime.

Run each arm sequentially through `scripts/flights/run_campaign.py prepare-supply` with explicit repository/data/runtime/lock paths, the generation cell selected, and at most eight preparation workers in total. No preparation task starts an inference or encoder service. The current root-owned G1 generation may overlap this CPU work. If G1 enters its next preprocessing stage, suspend new preparation dispatch until the shared eight-worker allowance is free.

Write immutable artifacts beneath `SPEECHRL_DATA_DIR/prepared/SAEA-SLURP-KU-S4N-G2-PREPARE-V1/`, separately as `candidates-supply.json` and `twin-supply.json`. Preserve any failed or existing path; never overwrite a conflicting artifact. Verify full ordered roster, IDs and supply content against the respective provider selection, then demonstrate warm consumption with zero bootstrap producer calls and zero endpoints. Source/config/implementation hashes remain binding; integration changes require fresh preparation instead of relabeling old bytes.

The result is a preparation receipt only. Both successor generations remain held until actual full-roster fits, the complete G1 decision, separate exposure registration, source pins and root admission. Both N and twin must seal and score before outcome reading. Exemplar encoding remains gated by the formal N non-inferiority decision.

## Initial preparation refusal and correction

The first N-arm CPU preparation refused before artifact creation because the successor lacked executable `preparation_source_receipts`. Documentary source_pins were not sufficient for the common preparation validator. No generation, tokenizer, encoder or scorer endpoint was contacted; no artifact existed to overwrite. Both successors now bind the original preparation and vector receipts, candidate-bank file hash, snapshot file hash (in addition to its separately checked content identity), and sealed predecessor manifest. The mechanism, samples, attempt IDs and scientific rule are unchanged. Continue the same registered CPU preparation only after these source bindings are committed and checked.
