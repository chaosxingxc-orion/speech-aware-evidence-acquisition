# Manual analysis metadata repair

The manual package author emitted a scorer-only projection. The real RewardProjection parser requires five exact fields. The author now constructs the established official SLURP projection through that parser's dataclass: scorer `slurp-slu-official-train`, endpoints `port_micro.slu_f1` and `port_micro.intent_accuracy`, and all twelve SLURP native sufficient-count fields. Its rule ID is `manual-architecture-official-counts-v1`.

Post-freeze resolution validates the projection before writing a package. It requires the frozen registration intent and analysis definition to contain the identical measurement profile, and explicitly carries that profile into the resolved registration before computing its hash. Current newly authored intents already carry the profile; historical incomplete intents require an explicit immutable metadata successor.

## Verification

The regression first reproduced the scorer-only failure with the real parser (two authoring cases failed). Final scoped tests passed: 166 tests in 29.22 seconds. The new end-to-end synthetic contract uses actual finalized bundles, complete saved-score receipts, real reward artifact construction and joins, the shared complete-evidence reader, attributed terminal/contact costs, measured sample timing with a common session pin, and pooled cohort statistics. No mocks replace those evidence or analyzer boundaries. Rehashed malformed projection, missing profile, and mismatched profile refuse before resolved output creation. Existing reader capture fixtures now validate the real projection contract instead of accepting a scorer-only placeholder.

The code audit also confirmed complete unique family/attempt/config/roster bindings; one successful official score job per member; official sufficient-count identity and aggregates; all native row counts; terminal and cost attribution; exact timing geometry/common session; complete utterance/stratum metadata; and registered paired resampling. No additional metadata defect was identified. Synthetic coverage does not certify actual task results, which remain root-owned.

## Immutable successor recommendation

Preserve the malformed frozen intent, original resolved package, original signed READ ledger row, and both failed derivative directories. Root may author a new resolved metadata package and an independently authorized successor READ ID with an appended ledger row. The manual reader matches READ identity across recipe, registration and authority; it has no hard-coded READ ID.

Copy scientific definitions and original runtime/member/source bindings unchanged. Add the exact existing recipe measurement profile to the successor registration; change its read_id to the new authorized ID and recompute registration_sha256. Copy the recipe, change only run_ids.read and its manual_architecture_registration raw pin. Copy the supplement, replace only projection plus the successor recipe/registration raw pins and any explicit metadata-successor provenance required by root. Preserve executing reader/analyzer source pins. Use a fresh derivative output directory and retain all prior output bytes.

This repair changes authoring metadata only. It changes no runtime, request, scorer, scientific metric, model input, serving control, experiment output, or prepared source envelope. No real model/scorer contact or scientific-result read was performed. Engineering: GPT-6.1 Sol. Independent review: GPT-6 Astra. Root owns metadata authorization, integration and any analysis invocation.
