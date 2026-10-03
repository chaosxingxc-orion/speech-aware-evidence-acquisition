# Bind context layout to the complete policy

Implement the human's context-space amendment as a prospective whole-policy identity. Keep experimental controls fixed while allowing independent node instructions and declared context layouts to vary. Do not require identical role prompts, fixed role slots or a cache-hit floor. Compare complete-system quality, intent, completion and measured cost.

The existing `saea-system-text-policy-bundle-v1` remains unchanged. A new `saea-system-text-policy-bundle-v2` adds exactly `context_layout.native_role_query_placement`, selecting `null` for historical placement or `"before-speech-v1"` for the implemented shared renderer. Hash the layout, all role text, knowledge/supply bindings and cumulative ancestry together. Preserve ancestry when changing layout or returning to historical placement. Refuse a silent downgrade from v2 to v1.

Compile the declared layout and role text together through the existing consumption compiler. Disabled compilation returns the unchanged input configuration. Verify the final four-fragment runtime composition against the immutable bundle before launch; examining only the baseline would miss a layout introduced through a model, dataset or experiment fragment. Use the same composer as the shared runtime and fail closed on missing fragments or collisions. Preserve legacy receipt fields for v1.

The existing v1 proposal language does not acquire new edit permissions. A v1 proposal against a v2 parent preserves that parent's layout but cannot alter it. Prospectively register an expanded proposal protocol and equal L/B editable surfaces before asking a proposer to choose a layout. Do not modify spent opportunities, current round8 policies or frozen workers. This capability creates no proposal allocation or runtime authority.

## Verification

The combined policy, archive, compiler, construction, cohort and prelaunch suite passed 275 tests. The targeted gate coverage run passed 144 tests, which are a subset of that suite, not additional independent tests. Statement coverage is 95% for the policy module and 91% for the prelaunch gate; the new statements are covered. Ten integration cases place the option in model, dataset or experiment fragments, or introduce missing/colliding fragments. Declared layouts are accepted and unbound layouts are refused. All checks used synthetic/model-free inputs.

Engineering-base, harness-admission, finite-completion and shared OpenJiuwen reuse checks passed. The initial OpenJiuwen check invocation omitted its required output argument and exited before running the proof; the corrected invocation wrote the existing synthetic proof outside the repository. No model, tokenizer, scorer or GPU contacts occurred for this change.

## Next activation boundary

Keep current round8 on its registered historical layout. Its three capacities passed independently and its separately admitted four-row structural stage remains under the GPU coordinator. A new layout policy still needs its own maximum-legal-request FIT, structural proof, exact family registration and complete-family READ. Measure node prefill, decode and client duration separately; do not infer queue duration by subtraction or campaign wall time by summing overlapping calls. Keep same400 assets, Omni answer custody, L/B isolation, owner227's human boundary before8x400, other-carrier holds and the paused SLURP heartbeat.
