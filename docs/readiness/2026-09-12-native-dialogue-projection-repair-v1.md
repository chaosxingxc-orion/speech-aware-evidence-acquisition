# Native dialogue projection repair

## Closed failure and correction

The sealed four-row SAEA-SLURP-NATIVE-TOOLS-ENGINEERING-V1 attempt executed actual local CPU ASR and supplied its transcripts, but all four final responses were textual tool-call frames. The official result remains unchanged and unqualified. See 2026-09-12-native-speech-tool-engineering-result-v1.md for the sealed result and hashes.

The source review identified generic user-text replay of native calls/results and repeated acquisition instructions. The shared transport now projects new source-bound native tool states into assistant tool calls followed by matching tool returns. This fixes a concrete protocol mismatch; no claim is made that it was the sole cause of the failed answers.

The dispatcher retains exact native call bytes, its source phase identity, explicit sample/phase/query-packet facts and the actual returned content at invocation time. The transport verifies the counted custody receipt, exact arguments, source response and packet binding. It preserves task-contract and memory results, supplies observation text once across repeated cache invocations, and retains earlier knowledge views even when later selections replace the current aggregate view.

Historical knowledge speech packets remain in their returned order after the corresponding tool result. Their bytes are checked with the shared packet loader. Request capacity uses every speech packet occurrence in the actual rendered body, including historical packets; it does not infer capacity solely from the current aggregate supply.

Envelopes without the new native fields retain their historical request shape, including plain-text generic tool states. No historical manifest, raw response, score or pinned configuration was rewritten.

## Integrated adjacent corrections

- Native answer-or-tool fitting accepts an exact initial roster followed by ordered shrinking active rosters, with no stopped-sample resurrection.
- The native controller rejects escaped or truncated textual tool frames before sealing a task answer.
- Runtime custody receipts now include the sample identity.

## Validation

All validation ran in WSL Ubuntu-24.04 with the existing speechrl environment and literal checkout PYTHONPATH. The final focused and adjacent suite passed 419 tests with one skipped test and three dependency deprecation warnings. Ruff, the engineering base check and git diff whitespace checks passed.

The tests cover actual shared dispatch and runtime custody, three speech prompt layouts, matching rendered/sent bodies, call/result association, repeated cache evidence, changed or absent receipts, earlier paired knowledge packets, speech capacity, native early stopping and historical compatibility. Fake transports/tokenizers were used; this validation made no new experimental model, ASR, encoder, tokenizer endpoint or scoring contact.

## Next execution boundary

Register at most the single permitted recovery of the closed four-row engineering proof, with distinct acquisition, evidence-use and final-answer instructions and new bound source/config identities. Preserve the existing service geometry and model boundary. A valid recovery proves engineering only; it does not establish an autonomous trigger or task effectiveness.

After a runnable native baseline is established, implement the owner's retained-hypothesis joint intent/slot mechanism described in 2026-09-12-joint-intent-slot-hypotheses-root-design-v1.md. Its hypothesis state, knowledge view and final delivery must be configured together. No Top-N effectiveness flight is authorized by this repair note.
