# STATUS 124 - On-demand speech spans verified on CPU; GPU hold unchanged

Read OWNER-GPU-AFTER-CURRENT-HOLD-2026-09-15.md first. This update changes no exposure,
scientific verdict, serving identity or GPU authorization.

## Scheduling authority

Allow only the already active Audio2Tool recovery task to finish. On completion, failure,
interruption or any other stop, do not start another GPU experiment, tokenizer fit, encoding,
restart or recovery until explicit owner resumption. SLURP and E21 successors remain held.
Do not proactively unload the resident model. Eligible complete CPU scoring, preparation
and root analysis continue. Current process metadata belongs to the bounded observer;
this engineering update does not assert fresh progress from a historical process snapshot.

## Completed shared implementation

The opt-in saea-tool-live-speech-span-v1 now joins the existing native tool dispatcher,
live speech provider, source reader and FlightRuntime. The Reviewer or Planner selects
start/end seconds relative to the current execution window. The shared provider validates
source identity and frame bounds, limits each selection to 30 seconds without clipping,
and retains source-bound cache artifacts. Cold contacts debit only the selected duration.
Warm identical unit/frame selections make no additional neural contact.

The public configured path exposed and resolved a missing runtime declaration check.
The final admission check also refuses mismatched full-utterance and execution-window
tool schemas before contact. The v3 toolkit is explicit opt-in; prior tables and pinned
legacy wrapper bodies remain unchanged.

The configured synthetic lifecycle uses two windows of one parent. A Reviewer requests
the tool, the returned evidence reaches the Planner and revised Solver, and the Solver
retains answer authority. It uses 16 simulated core contacts under a 22-contact reservation,
two simulated ASR contacts totaling 0.25 seconds, source-bound OBS traces, ordered parent
stitching and exactly one complete-manifest scoring handoff. Preprocessing and provider
construction perform no ASR.

Root regression: 1,042 passed, one skipped, eleven existing dependency/process warnings
at 2ba5043b. The final source-scope change at ff7758bc passed 74 focused tests.
These overlapping suites are reported separately. Ruff, engineering-base, tool-catalog
and diff checks passed.

Model service/post, neural ASR, native capacity checks, synthetic packet artifact loading,
manifest construction and bundle/scorer boundaries remain simulated. This establishes
shared engineering integration, not real service fit, tool-selection competence, task
quality or real bundle finalization. No real core, ASR, tokenizer, encoding or GPU contact
occurred during this work.

Source worktree: /home/chao/saea-worktrees/e21-native-window-runtime-v1.
Final code commit: ff7758bcbc00c3dd01d904f29dd5f9d426d496a9.
Documentation checkpoint: 7b37b46d.
Production integration remains pending the permitted flight boundary; frozen active
experiment worktrees were not modified.

## Root assessment and finite next work

1. Preserve the bounded A2T observer. Reconcile terminal records and complete eligible CPU
   scoring and paired analysis without dispatching any GPU successor.
2. Integrate reviewed shared changes at the permitted boundary.
3. Build external-governed ConEC named stores through the existing shared knowledge base.
   The released sources are 44 Name - Role files and 44 token/count files, not prose
   financial reports. Preserve explicit names, roles, lexical forms and source provenance.
   Do not invent semantic facts, pronunciations, spoken occurrences or TRAIN samples.
4. Freeze exact E21 role prompts, opt-in tool allowlists, matching direct/system
   configurations and per-unit contact/fit budgets. Keep task-native WER/PERSON analysis.
5. Preserve ready SLURP materials. Every actual GPU fit or experiment remains owner-held.

Engineering improvements do not constitute a training-free RL algorithm or evidence of
task benefit. The broader goal remains active; trajectory sampling and optimization follow
a demonstrated stable agentic task base.

## Receipts

Paths are relative to SPEECHRL_DATA_DIR.

- coordination/gpu-after-current-hold-20260915-v1.json.
- coordination/e21-native-window-bridge-v1/root-span-lifecycle-checkpoint-v1.json;
  SHA256 fc2152b65d8962aac5a289f1a4b3b46a93847b51530b640ff9b8ff754fd47b02.
- coordination/e21-native-window-bridge-v1/root-span-lifecycle-regression-v2.log;
  SHA256 6b7333804b0d941e156f998426f03e0a17637a3235f1c640fcdaccd13bcb121c.
- coordination/e21-native-window-bridge-v1/root-span-scope-admission-regression-v1.log;
  SHA256 99d1f2776ea1396ed3bc162d6d17ea3fd7698f38a4871b778d2f75e04a59a1f9.

Recorded at 2026-09-15T06:52:04.511282+00:00.
