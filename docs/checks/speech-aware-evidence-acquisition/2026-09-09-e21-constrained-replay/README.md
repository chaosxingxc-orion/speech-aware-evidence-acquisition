# Complete historical E21 constrained-delivery parity

The current shared delivery implementation reproduces all 1,593 original KC-E1f window deliveries and all 44 stitched call transcripts byte for byte. There are zero mismatches.

The check verifies the original complete generation bundle and its frozen direct-baseline predecessor, then uses core.bundle.delivery_replay.replay_delivery with the registered substitution rule at 4 / 0.60 / 0.10. Each replayed window is checked against its original obs_delivered_text hash, and every stitched call is compared against the sealed output bytes. Original manifests, traces and outputs are unchanged; no derivative declaration was retroactively inserted.

The source contains three saturated terminal responses, all reproduced as predecessor fallback. Other whole-response refusals are 75 below the anchor floor and four above the substituted-fraction ceiling; 1,511 windows have no whole-response refusal. There are no terminal retries or skipped windows in this source. Those absent branches require the separate synthetic tests and are not claimed as observed full-roster evidence.

This is the required complete historical constrained-delivery compatibility proof. It does not prove current OpenJiuwen live execution, any new DR generation, efficacy, or four future derivative scores. DR still requires explicit migration to two generation groups/four predeclared deliveries, actual-window capacity checks and separate generation registration.

No scorer, model, tokenizer, encoder, network service or GPU was used. The registered read and exact source/implementation hashes are retained in summary.json.
