# E21 LOOP shared two-plan successor - held

This note records SAEA-E21-LOOP-SHARED-TWO-PLAN-V1. The original e21-loop-1-v1.json remains unchanged.

The successor compares two sealed predecessor component plans: the judge-targeted selective re-listen plan and its matched seeded-random plan. It does not claim live initial-draft selection, live judge selection, or a complete live system. The judge and random plans are fixed before any new contact and are reused as the generation inputs.

There are four held cells: a judge-plan fit and generation cell, and a matched-random-plan fit and generation cell. Both generation cells deliver all 1,593 fixed 90-second windows across all 44 discovery calls. Each contacts 600 planned windows for selective re-listen and back-fills the other windows from the sealed predecessor. The model-visible prompts, raw-audio path, repair frame, delivery parameters, and max_tokens=1024 remain those of the original LOOP baselines.

The two explicit OJW baseline derivatives are the minimum composition change. Each copies its corresponding original LOOP baseline and adds policy=obs-repair-loop-ojw, obs_controller_program=phase-direct-only-v1, and the OJW workflow timeout, preserving the original prompts and mechanism fields. No runtime code, prompt, launcher switch, or hidden override is used. The shared harness is core.flight.FlightRuntime through the OpenJiuwen phase-direct-only controller program.

Each generation has a ceiling of 720 calls and 18,500 speech seconds. The family has two generation groups with ceilings of 1,440 calls, 37,000 speech seconds, and 1.0 GPU-hour, allocated as 0.5 GPU-hour per generation. The shared raw-window fitter is budgeted at 601 contacts per fit: one GET /props plus one contacted request for each of the 600 selective windows. CPU request materialization is model-free; the later endpoint fit is not. Full materialization must verify this count before registration.

The source pins in the JSON use hashes computed from the predecessor receipt, both sealed plan files, both OJW baseline derivatives, and the model and dataset fragments. All attempt IDs are pending placeholders. Readiness is held pending the evidence-fit bridge, current live proof, exposure registration with consumed=false, measured serving geometry, and root review.

Gain is defined explicitly as gain(X over Y) = WER(Y) - WER(X), so positive gain means lower WER for X. Admission requires the inherited PERSON lower bound for gain over the sealed direct baseline to exceed zero, the lower bound for gain over KC-E1f to be at least -0.25009, and realized calls to be at most half of 1,593. Targeting is separate and requires the lower bound for gain over the matched random twin to exceed zero. Corpus, numeric, and insertion guards retain their inherited directions and values. The insertion guard is measured in percentage points: 100 times insertions divided by reference words, with upper bound +0.022178.

The historical KC-E1f scientific replica is complete and remains a descriptive comparator. It does not satisfy the evidence-fit bridge for these held cells and is not treated as a readiness receipt. No preparation, model, tokenizer, scorer, encoder, outcome read, or commit is performed by this successor task.

Root review retains all inherited integrity checks: delivered text outside accepted substitutions must match the sealed predecessor, token counts must match, and every window must appear exactly once. Negation-critical errors remain advisory under the inherited taxonomy because the null interval excludes zero. A positive lower bound for gain over KC-E1f is required for the additional improvement conclusion; it does not replace the separate targeting test.
