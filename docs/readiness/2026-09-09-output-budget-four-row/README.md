# Four-row output-budget engineering check

Owner decision OWNER-BUDGET-PROBE-004 admits a limited comparison on four fixed historical cases, with four generation calls per arm and no effectiveness claim. The separate capacity registrations each admit13 tokenizer endpoints and zero generation.

Both arms use the same resident model identity, frozen weights, schema-bearing slot phase, original audio packets and sealed closed-list predecessor. The only model-visible change is the configured completion ceiling64 versus256. Both opt into exact wire-response capture for stop-reason and structural diagnosis. Request IDs and slot routing remain operational fields.

The generation protocol is registered only after each real fit is bound. No adaptive retries, additional samples or follow-on budget sweep is implied. The larger cap is not a requested response length. The score readout is structural completeness, output length, stop reason and cost; do not invoke official accuracy scoring for these four selected cases.

Root validation at integrated source26eaa409:287 tests passed,1 skipped; engineering base check passed. The four selected requests constructed with the shared controller are equal across arms after excluding only request ID, slot routing and completion ceiling; see wire-parity.json. No real contact is implied by that contact-free proof.
