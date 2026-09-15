# E21 native window execution: root integration contract

The shared raw-native request/fit path and direct-only controller primitive are engineering prerequisites. They do not establish full E21 execution or quality. Complete the registered window path before admitting an E21 GPU flight.

## Preserve the two identity levels

Keep the dataset split at its 44 parent calls. Reuse the existing fixed-window inventory of 1,593 registered slices and their request keys as immutable execution-unit identities. Validate every unit against its parent, registered bounds, sample rate, source and derived audio hash. Do not create synthetic dataset sample IDs, reinterpret the split as 1,593 independent calls, or infer units from whatever media happens to be present in a later re-listen request.

An execution unit owns its native role history, model-contact limit, tool/revision budget, output and terminal state. A contact retains both the parent sample identity and the immutable execution-unit identity. Contact and trace identifiers must remain unique across two windows of the same parent. A re-listen changes the current observation binding while retaining the original execution unit and parent.

Use an explicit shared execution-unit contract in the existing runner and native bridge. Preserve original contact IDs and request bytes when this optional contract is absent. Do not solve identity collisions by silently changing global program IDs, appending fake sample IDs, or relying on per-worker mutable counters.

## Share execution and fitting

Run direct-only and native-role programs through the same controller, FlightRuntime and OpenJiuwen executor. Thread explicit raw query source and the actual registered slice bindings through public phase APIs. The currently feature-only FlightRuntime material binding must admit only the explicit raw arm through source validation, not by deleting the feature guard without a replacement.

Reserve generation/fit limits from the actual immutable unit inventory and each program's maximum contacts. Forty-four parent IDs multiplied by a per-window contact cap is incorrect. Bind raw capacity receipts to the exact rendered body, unit, parent and original slice source; include actual later observation and tool history where applicable. A direct-only request can use the existing static actual-request batch fit, while conditional native-role requests use the actual-contact gate. Both must exercise the same final request construction as generation.

Keep the original raw input protocol and local source validation. No old feature-cache path, implicit encoding service or alternate final-answer model is admitted.

## Aggregate before official scoring

Seal one terminal solver/delivery result for every registered window, including explicit failures and fallbacks. Reuse the existing deterministic chronological stitching and delivery functions to produce exactly one output per parent call. Preserve raw responses and derived delivery identities separately. Validate complete unit coverage, unique windows, parent association and order before allowing official scoring.

Run the standard complete-call Earnings scorer once over the 44 outputs. Evaluate overall WER and PERSON quality, with non-entity, numeric and insertion errors reported separately. Under the owner's future-experiment rule, a small insertion increase does not automatically veto overall and PERSON improvements. Preserve prior verdicts under their historical rules.

## Evidence required before generation

- Public raw direct-only and native-role paths consume exact original or registered-slice bytes using the real shared FrozenCoreClient.
- Two windows from one parent cannot share contact IDs, budgets or mutable native history.
- A re-listen cannot migrate to another unit or parent.
- Incomplete, duplicate or out-of-order window delivery cannot masquerade as a complete call manifest.
- Fitting and generation use identical rendered bodies and correctly reserved per-unit limits.
- The complete 1,593-window inventory maps to exactly 44 governed parent calls.
- Root registers the final configuration, geometry, protocol, exposure and scientific comparison before contact.

This contract is root's implementation direction, not a claim that the bridge is complete and not authority to launch E21. The current Audio2Tool flight remains isolated. SLURP preparation retains priority for the next fast iteration.

## Completed primitive evidence

Root reviewed the raw direct API and registered-slice custody changes at commits 8fdd3d3ddeae9ca126eea0f3ee640ccdc410998f and dd7f350ecd27faf225112b882f6ee6d18847d683. The independent combined regression run passed 420 tests, including shared feature/native behavior and public raw direct dispatch. Test transport was local and simulated; registered-slice tests establish byte custody, not acoustic task quality or a full-window campaign. The window contract above remains open.

Receipt: DATA/coordination/e21-native-window-bridge-v1/root-raw-direct-verification-v2.json. The v1 invocation named a nonexistent test file and ran no tests; v2 corrects the file list and is the successful evidence.
