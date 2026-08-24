# DEV-100 iterative optimization campaign — preregistration (iteration-tier)

Date: 2026-08-23. Status: **REGISTERED — prep missions dispatched; flies after the prep
prerequisites land.** Profile: `bounded-discovery-probe` (campaign row) + supporting
`model-free-check`/preprocess rows.

## 1. Authority and evidence gate

- Owner rulings `2026-08-23-knowledge-plane-baseline-rulings.md`: §2.2 ratifies the DEV
  ladder as the agent-space optimization tier; §7.1 freezes the baseline form; §7.2 mandates
  iteration before conclusions; §7.3's expansion gate is SATISFIED by exposed-data evidence —
  the M11 operating-point sweep (`2026-08-23-m11-operating-point-sweep.md`, row
  `SAEA-SN-MF-M11-OPERATING-POINT-SWEEP`): 10/264 grid cells beat primary on BOTH exposed
  splits, contiguous positive plateau α ∈ [0.54, 0.65], recommended cell +2/+1 with zero
  correct→wrong on either split.
- This campaign supersedes, for the DEV ladder only, the M-line's blanket "devel remains
  blocked" statements (owner ladder ruling §2.2); FINAL60 stays reserved/unread; test stays
  untouched; DEV-500/1000 stay blocked until this campaign converges positive.

## 2. Surface and machinery

- **Split**: DEV-100 (receipt `docs/receipts/probe-samples/DEV-100.json`, split identity
  `d676d38b…33e1`, 100 SLURP devel utterances, scenario-stratified, FINAL60 and the historic
  probe-60 excluded at utterance granularity). `QueryState.use_partition_role = "dev"` as the
  contracts require.
- **Baseline form (frozen)**: the C3 policy chain `saea-kb-alpha-blend-v1` (+
  `saea-rank-wcos-prior-agree-v1`, `saea-fuse-supplyfilter-v1`) over the KB-BUILD full TRAIN
  snapshot (`slurp-kb-size-full`, sha256 `e27b2745…`); run through
  `run_speech_native_agent_loop` with the `openjiuwen-workflow-v1` executor on the resident
  receipt-bound decoder service; every contact carries the original speech packet. **The M11
  pair-boundary stage is NOT flown** (sweep verdict: zero repairs as flown; its two missed
  repairs are captured by the blend layer at zero contacts).
- **Round-0 knobs (sweep-recommended)**: α 0.60; rrf rank weighting; evidence =
  rank + prior + agreement; τ 0.5 (safety rail); top-k 5 (sweep: raise above 3); label priors
  from TRAIN (the KB snapshot's own p(intent|scenario)); prior-source (train vs dev-refit) is
  an explicit later-round knob, dev-legal, recorded per round.
- **Query-side content vectors**: the direct-decode answer text (agent intermediate,
  auxiliary) embedded via the pinned `qwen3-embedding-0.6b-gguf` tool; KB-side vectors from
  the registered text-embedding pass. Speech dim NOT active this campaign (deferred per the
  4R mean-centering design input).

## 3. Iteration semantics (the point of this campaign)

- **Round 0**: arm M0 direct decode (1 contact/sample, 100 contacts) + arm BLEND at round-0
  knobs (≤2 core contacts/sample + 1 embedding tool contact). Gold opens scoring-side ONLY
  after all round arms complete (runner seal-before-score).
- **Rounds 1..N**: knobs adjusted from prior-round results (gold between rounds only, never
  runtime); each round is its own attempt under this ONE campaign row with per-round
  accounting appended to the ledger row; byte-identical-resend discipline: each round records
  the server `-np` and one identical-prompt resend pair (the pcorrf divergence lesson).
- **Stopping rule (preregistered)**: CONVERGED when the best arm's accuracy changes < 1
  sample across two consecutive rounds with zero correct→wrong regression growth; FALSIFIED
  when no knob setting beats M0 direct after 3 completed rounds. Hard cap 6 rounds.
- **Outputs**: the dev-tuned knob table (frozen as `configs/policy/kb-policy-v1-dev100.json`),
  a campaign report with per-round tables (per-arm accuracy, wrong→correct, correct→wrong,
  contacts, worst-round disclosure). NO promotion claim: the tuned config's confirmatory
  reading happens later on DEV-500 (one-shot), per the ladder.
- **Owner sync (standing instruction, 2026-08-23)**: after EVERY round is scored, the
  coordinator reports to the owner before the next round flies: per-arm accuracy, W→C / C→W
  counts, delta vs the previous round, contacts spent vs ceilings, and the proposed next-round
  knob adjustment with its rationale; stopping-rule triggers are reported the moment they fire.

## 4. Ceilings (campaign totals, all rounds)

≤ **1,800** frozen-core contacts (round 0 ≤ 300; each later round ≤ 300); ≤ **1,500**
pinned-tool embedding contacts; ≤ **2,400** metered audio-seconds; ≤ **2.0** GPU-h
(GPU-active basis). One-shot semantics apply per ROUND attempt (no silent intra-round
retry); the campaign row itself stays open across rounds until the stopping rule fires.

**Owner-approved ceiling amendment (2026-08-24, after the round-0 sync):** round-0's five
aborted attempts (all serving/harness pathologies, zero scientific loss, fully documented in
the attempt records) consumed audio budget the original cells sized for clean rounds. With
round-0 sealed at cumulative 688 core / 300 tool / 1,824.52 audio-s, the owner approved at
the round-0 sync: **metered audio-seconds 2,400 → 5,500** and **frozen-core contacts
1,800 → 2,500** (supports up to 5 further iteration rounds at ~560 audio-s / ~210 contacts
each). Tool and GPU-h cells unchanged. The serving-pathology attribution (build-bound to
`build-singleton-zero-copy`; decode inner loop, NOT preprocessing — prompt-eval stayed
healthy and the featcache warmup is offline/CPU-side by design) is recorded in the round-0
attempt records; scientific flights use the base `llama.cpp-featcache` binary.

## 5. Prep prerequisites (each its own registered artifact, before round 0)

1. Text-embedding pass over the full snapshot's content-facet and value texts
   (`SAEA-SN-TOOL-KB-TEXT-EMB-PASS`): encode-only checked, CPU-served (`-ngl 0`) to leave the
   resident decoder's VRAM untouched, vectors + manifests on the data root, hashes in Git,
   jitter pair recorded.
2. DEV-100 runtime-view dataset fragment (per-sample audio sha256 manifest) + 100 devel
   packets materialized through the CPU preprocessing sidecar (label-free, own
   preprocess row, GATE-C36 pattern) + promotion receipt into the resident service's feature
   root.
3. Campaign experiment fragment (knob table + stopping rule machine-readable) + composition
   against the resident model fragment + session-bound tokenizer-only prompt-fit for the C3
   prompt shapes.
4. GPU preflight: Lenovo SmartFanMode == 3 AND enforced power limit ≥ 95 W (the 2026-08-23
   35 W quiet-mode incident), plus the standing runtime-integrity checks.

## 5b. Pre-registration amendment (coordinator, 2026-08-24, BEFORE the campaign row was
## registered and at zero campaign spend)

The round-0 launch attempt fail-closed at the session-bound prompt-fit: the C3 evidence
contact measured 7,773 worst-case tokens against the np16 profile's 4,096-token slot
(margin −3,741; receipt under `2026-08-24-dev100-c3-prompt-fit/`). Two remedies adopted,
both pre-registration:

1. **Contract-rendering fix** in `rails/kb_policy.py`: the evidence contact's instruction
   REFERENCES the task contract already present in the system message instead of
   re-rendering it (~1,957 duplicated tokens removed). Rendering fix only; no knob, grammar,
   or policy-id change.
2. **np8 serving variant** for this campaign: model fragment
   `q4km-mmproj-free-speech-native-np8-zcopy-speech-query-prefix-max64` (`-np 8` at
   `-c 65536` → 8,192-token slots; all other server args identical to the resident zcopy
   profile). Measured-sufficient alone (+355 margin); combined with remedy 1 the expected
   worst-case margin is ≈ +2,300. Halved slot concurrency is accepted for 100-sample rounds.
   The campaign's composed config hash is therefore the np8 composition; a fresh
   session-bound prompt-fit against the np8 service must show nonnegative margin on the
   POST-fix rendering before the campaign row is registered.

Also recorded: the predecessor resident session (`33639d3d…`) died uncleanly in the window
2026-08-24 03:50:39Z–04:32Z (no stop receipt; no error lines; silent external termination;
zero scientific loss), and the first C3 prompt-fit MF row WAS executed (7 tokenizer
contacts) — its ledger row carries the facts. Value vectors remain SEALED; percept
admission is facet-side (verified against the implementation).

## 6. Discipline

Gold never in runtime; devel gold opens scoring-side between rounds only. SLURP CC BY-NC 4.0
carried. No test, FINAL60, DEV-500/1000 access. Speech packet on every core contact; no
transcript-only query. Exposure rows before results, always.
