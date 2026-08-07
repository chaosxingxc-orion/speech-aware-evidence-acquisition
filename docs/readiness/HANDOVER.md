# R0.1 readiness survey — handover

Status at 2026-08-07 (second session): **complete.** All five work items have landed. The
2026-08-07 resumed session (web-search quota raised to 1000 before launch, surveys run serially
in the foreground per the operational notes below) closed items 1–5.

## What is done (committed)

| File | Covers |
|---|---|
| `2026-08-07-dataset-content-verification.md` | 15 on-disk datasets verified **by content** (not by name): modality, task shape, label layers, scale, license, scope verdict |
| `2026-08-07-prior-readiness-group1.md` | Families A (contextual ASR/entity), C (spoken QA), E (meeting) — 22 prior lines |
| `2026-08-07-prior-readiness-group2.md` | Families B (SLU), D (speech agentic/tool calling), F (assistant omnibus) — 19 lines |
| `2026-08-07-artifact-hunt.md` | (a)/(b)/(c) artifact matrix for every candidate line in both groups; **corrects two group-1 "NONE found" assertions** (ConEC and CMT-LLM official repos exist); PlanRAG-Audio re-checked, still unreleased |
| `2026-08-07-carrier-mechanism-map.md` | Per-carrier performance trajectories + consolidated three-bucket mechanism map — the deliverable the owner framing called most important |

## Headline findings for the owner decision

1. **Audio2Tool publishes numbers for our exact frozen core** (Qwen-3-Omni-30B: Tier1 92.4% →
   Tier8 41.7%, deterministic metrics, prompt-only protocol) on an on-disk carrier — the only
   same-model published anchor found anywhere; its eval scripts are unreleased (placeholder repo)
   and there is a paper-vs-disk license contradiction (CC-BY-4.0 vs CC-BY-NC-4.0) to resolve.
2. The group-1 open finding **splits** for B/D/F: method papers still ship zero runnable
   artifacts, but ≥6 benchmark harnesses are runnable under our boundary with published numbers
   (AIR-Bench SLURP-IC, Audio2Tool, VoiceAgentBench, VoiceBench, VoiceAssistant-Eval, URO-Bench,
   Big Bench Audio). HANDOVER option 2 (official scorer + our arm vs published numbers) is
   concretely enabled; option 3 pairs with it naturally. Owner decision still pending.
3. Across all 17 in-scope carriers, **no published inference-time evidence-acquisition method
   exists** — the study's target mechanism class is unpopulated everywhere (bucket 3 of the map).
4. The strongest reachable, ablation-precedented arm designs: transcript self-mediation
   (Big Bench Audio 66→~92 et al., with FDB-v3's self-correction reversal as the counter-case),
   context-injection (Siskos dose-response on E21), one-shot prompting (VoiceAgentBench +10–17pp).
5. Judge dependency: three of four Family F harnesses used paid judges — blocked by the =0
   paid-API budget; VoiceBench's deterministic MCQ/rule tier and VoiceAssistant-Eval's open
   gpt-oss-20b judge are the boundary-clean precedents.

## What is NOT done

Nothing from the original five items. Remaining work is owner-side: the R1 re-plan decision
(options 1–4 below) with both survey groups, the artifact matrix, and the mechanism map in hand.

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
published number** — every "runnable" line would have to be reimplemented from the paper.
**2026-08-07 update (group 2 answered the conditional):** for families B/D/F the finding splits —
confirmed for method papers (still zero runnable method artifacts), refuted for benchmark harnesses
(several runnable protocols with published numbers, incl. one same-model row: Audio2Tool ×
Qwen-3-Omni-30B). "R1 = closest-prior *method* reproduction" remains not achievable as written;
protocol-level reproduction is. The owner has said explicitly that this re-planning is on the table.
Options sketched (owner decision, would need a dated record like the 2026-08-06 budget-caps
retirement):
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
