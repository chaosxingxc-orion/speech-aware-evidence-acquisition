# R0.1 readiness survey — handover

Status at 2026-08-07: **incomplete.** Two of five work items landed; three were lost to an
exhausted session-level web-search quota (200/200). This file is the brief for whoever resumes.

## What is done (committed)

| File | Covers |
|---|---|
| `2026-08-07-dataset-content-verification.md` | 15 on-disk datasets verified **by content** (not by name): modality, task shape, label layers, scale, license, scope verdict |
| `2026-08-07-prior-readiness-group1.md` | Families A (contextual ASR/entity), C (spoken QA), E (meeting) — 22 prior lines |

## What is NOT done

1. **Family B — SLU (intent/slot)**: `slurp`, `speech-massive`, `minds14`. Not surveyed.
2. **Family D — speech agentic / tool calling**: `audio2tool`, `voiceagentbench`. Not surveyed.
   This is the family that would calibrate the study's X4 question; currently no prior evidence at all.
3. **Family F — assistant omnibus**: `voicebench`, `voiceassistant-eval`, `uro-bench`, `big-bench-audio`.
4. **GitHub artifact hunt**: for every candidate line, does an open-source implementation exist
   (official or third-party), plus any reproduction report.
5. **Carrier usage survey + mechanism map**: see the framing rules below — this is the most important
   missing piece.

## Framing rules the owner set (these were corrections to an initially wrong framing — apply from the start)

1. **Judge scope by CONTENT, never by name.** Already proved twice: `audio2tool` is genuine human
   speech → tool call (in scope); `tau2-bench` is tagged `spoken-agent` but has **zero audio on disk**
   (out of scope); `omni-deepsearch`'s "SPEECH" tag means speaker-ID, not linguistic content.
2. **The reproduction target is the PAPERS THAT USE these datasets, not the datasets.** A dataset gives
   us only (a) a carrier and (b) an official scorer for comparability. Its own introductory baseline is
   a *reference floor*, never an R1 candidate — it contains no evidence mechanism, so reproducing it
   says nothing about this study's question.
3. **The question is: what scientific method did later papers use to get BETTER numbers on this
   carrier?** Not how the dataset evaluates. Build a **performance trajectory** per carrier: the floor,
   the current best, and each step up attributed to a concrete mechanism (e.g. "retrieved entity list
   injected into the prompt", "n-best reranked by a knowledge-grounded scorer", "two-pass correction
   conditioned on retrieved context", "fusion adapter trained over the audio encoder"). Attribution
   must be supported by the paper's own ablation; if it is not, label it weak evidence.
4. **For evaluation, follow the dataset's own shipped scripts** where they exist (`slurp` repo,
   `slue-toolkit`, both already on disk) — a standalone post-hoc scorer makes our numbers comparable
   without reimplementing anyone's system.
5. **Boundary is the decisive filter.** API-only frozen core (prompt + audio → text over
   chat-completions), zero training, no logits, no decoder access, no adapters/LoRA, no trained head,
   no second answering LLM. Anything needing those is `INCONCLUSIVE_BASELINE_NOT_READY` **with the
   exact blocker** — that record is itself evidence of a capability gap no published method fills here.
6. Distinguish rigorously: **(a) an artifact exists**, **(b) it reproduces the published number**,
   **(c) it runs under our boundary**. Conflating these makes the survey worthless.

## The mechanism map (the deliverable that matters most)

Three buckets per carrier:
- mechanisms shown to work **and** reachable under our boundary → R1 calibration candidates;
- mechanisms shown to work but **unreachable** (logits/training/head) → structural-gap evidence;
- mechanism classes **never tried on that carrier** that we *can* reach → where this study's
  contribution could plausibly sit.

## Open finding that may force a plan change

Group 1's conclusion: across its 22 lines, **no candidate ships a runnable artifact that reproduces its
published number** — every "runnable" line would have to be reimplemented from the paper. If the
outstanding surveys confirm this for families B/D/F, then "R1 = closest-prior *reproduction*" (entry
contract) is not achievable as written, and R0/R1 must be re-planned. The owner has said explicitly
that this re-planning is on the table. Options sketched (owner decision, would need a dated record like
the 2026-08-06 budget-caps retirement):
1. reproduce a paper that does ship a usable artifact, even if a weaker/older line;
2. official dataset scorer + our own arm, compared against published numbers (calibrates the pipeline,
   not the method — and does not import "did we understand the paper correctly" as a confound);
3. constructive self-calibration: a degradation ladder (no context → correct → mismatched → oracle)
   proving the metric moves monotonically, which also tests metric sensitivity;
4. drop the standalone R1 stage and fold prior comparison into the X probes as an arm.

## Operational notes for the resumed session

- **Raise `CLAUDE_CODE_MAX_WEB_SEARCHES_PER_SESSION` before launching** — it must be set at startup.
- **Run these surveys serially and in the foreground.** They are web-quota bound; parallelism cannot
  help when a shared session quota is the bottleneck, and background agents hid a 45-minute stall.
- Check remaining quota before dispatching, and do not let a sub-agent spawn its own sub-agents
  (one stalled agent here dead-locked waiting on a child that had itself hit the quota).
- Never modify `docs/datasets.lock.json`: the missing `speech-aware-*` profiles on `slurp`,
  `speech-massive`, `minds14`, `spoken-squad`, `heysquad`, `audio2tool`, `voiceagentbench` are why the
  gate cannot see them, but assigning a profile is a data-identity change requiring the umbrella's
  formal path and owner approval.
- Licensing already established: `slurp` audio is **CC-BY-NC-4.0** (new finding), `speech-massive`
  CC-BY-NC-SA-4.0, `audio2tool` CC-BY-NC-4.0, `voiceagentbench` a non-standard Krutrim community
  licence; `full-duplex-bench-v3` and `omni-deepsearch` state **no licence at all**.
- No model touch anywhere in this work. R0.3 (`SAEA-E-001`) remains unauthorized and unrun.
