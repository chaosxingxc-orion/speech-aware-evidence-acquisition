# Audio2Tool native dispatch and terminal-custody proof

Recorded by ChatGPT root on 2026-10-02. This is offline engineering evidence.

## Scope

The earlier Audio2Tool integration covered the actual runtime adapter and
native episode graph, including ordered repeated tool calls and prepared
knowledge. This proof adds the shared FlightRuntime dispatch, canonical
terminal output construction and output-to-trace verification to that path.
No production code changed and no new defect was observed.

Nine routes each execute two independent synthetic Audio2Tool samples:
ACCEPT, revision, nonempty acquisition, empty acquisition, revision-budget
exhaustion, empty first Solver, empty revised Solver, whitespace-only Solver,
and empty length-terminated Solver. The second sample remains an unaffected
control in each route. These are 18 synthetic complete trajectories, not a
registered research flight or a task-quality estimate.

The proof verifies:

- Preserve all five ordered answer calls, including four repeated calls to
  the same tool. Do not expose those answer-domain tools as executable tools.
- Deliver the latest eligible Solver revision; preserve an earlier eligible
  draft when a revision is empty, or produce the configured abstention.
- Supply knowledge only after the model's acquisition action. Accept empty
  material and preserve the extra Solver's final answer authority.
- Keep sample histories separate and preserve the task contract prefix.
- Refuse any runtime path to target loaders, gold or adapter scoring.
- Match the recorded model contact count, request receipts and minimum
  trace-derived count, including refused completions.
- Verify canonical terminal outputs against their actual recorded trace.

## Validation and limits

The focused proof has 9 passing tests. The combined adapter, native episode,
FlightRuntime dispatch and new proof group has 57 passing tests, with three
existing dependency deprecation warnings. Changed-file Ruff and Git
whitespace checks pass. No production-source coverage claim is made.

The Audio2Tool runtime adapter, FlightRuntime dispatcher, OpenJiuwen executor,
acquisition binding and canonical-output/trace validators are real. Dataset
loading, speech bytes, released knowledge, model replies and capacity admission
are synthetic local fixtures. The FlightRuntime object uses the existing
unit harness; its factory and whole-flight admission, manifest sealing,
finalization and official scoring are not proved by this test. No external
model, tokenizer or scorer was contacted. No task answer or quality result
from a research flight was read.

This completes the missing dispatch/custody join for Audio2Tool's native
branches. It does not admit a cross-carrier optimizer or GPU flight.
Audio2Tool and Earnings still require their own exact knowledge/data bindings,
actual capacity, same-chain A/A, metric rules and coordinated admission.
The system-text bundle and active search remain SLURP-specific.

## Active experiment

At 2026-10-02T07:33:51.922806Z, update1's four parent/replicate members were
FINALIZED with 400 rows, one successful official score and zero failed scores
each. B-candidate-2 was OPENED with 501 contacts and no completed manifest.
Contacts are not completed rows. STOP was absent; the standard status script
reported a healthy running service and the frozen campaign remained active.
Windows free memory was 10.77 GiB immediately after that observation.

The frozen worker remains at 2f07dd3d6f52eee79d24243c40a0dff195260816.
Its sources and queue were not changed. All five members and the exact root
READ are still required before quality interpretation or next-round parent
selection. Existing carrier holds and all spent proposal slots remain intact.
