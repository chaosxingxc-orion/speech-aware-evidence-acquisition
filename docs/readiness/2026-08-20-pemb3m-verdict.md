# P-EMB-3M verdict — EMB-WEAK-SCOPED (M1) + CASCADE-ROUTES (M4) (registered one-shot read, 2026-08-20)

Mechanical outcome per the registered metrics and verdict rules
(`docs/readiness/2026-08-20-pemb3m-preregistration-REGISTERED.md` §4), computed by the pinned
offline read suite (`analysis.pemb3m_read`, built and coordinator-reviewed BEFORE the read, flown
unmodified) over the already-flown sweep `SAEA-PROBE-pemb3m-388` — 234/234 scored embedding
contacts across the three flyable arms in the finalized attempt `attempt-20260820T112943Z-410bdb`
(durable state `FINALIZED`) — zero model contact, zero GPU, no attempt-directory mutation.

Read archive: `docs/checks/speech-aware-evidence-acquisition/2026-08-20-pemb3m-read/`
(`verdict.json`, `report.txt`, `verdict-flight-facts.json`, `report-flight-facts.txt`, `README.md`,
`MANIFEST.sha256`). The suite ran exactly once (idempotence-guarded output dir), exit 0, at study
HEAD `8695525` with a clean tree. Exposure row `SAEA-PROBE-pemb3m-388` flips to consumed in the same
commit. Scope: **descriptive, discovery-tier, n = 60 SLURP devel, 18 canonical labels, three flown
arms, single run per arm, same-distribution**. SLURP audio CC BY-NC 4.0 carried on every
audio-derived number below.

Pre-read gates, all green before anything was opened: `test_pemb3m_read.py` + `test_pemb3m_flight.py`
**106 passed**; the flight archive's `MANIFEST.sha256` verified **32/32 OK**; ledger row
`consumed = no`; tree clean at `8695525`. `PYTHONDONTWRITEBYTECODE=1` throughout. The read consumed
only the three derived per-arm vector manifests
(`derived/embeddings/SAEA-PROBE-pemb3m-388/<arm>/manifest.json`) plus scoring-side-only gold.

---

## 1. VERDICT

> ## OVERALL: **EMB-WEAK-SCOPED + CASCADE-ROUTES**
> the dedicated AUDIO embedder fails on this stack (scoped — the pooling override was present, so
> this is not a model-level refutation), while the TEXT-ONLY cascade reaches the routing tier: the
> embedder path has a working instrument, and it needs no audio embedding at all

| arm | model | side | accuracy | labels ever predicted | top-1 share | mean top-1 cosine | verdict |
|---|---|---|---|---|---|---|---|
| **M1 PRIMARY** | `lco-embedding-omni-3b-gguf` (llama.cpp) | audio↔text | **3 / 60 = 0.0500** | 5 / 18 (`recommendation` 36) | 0.6000 | +0.0707 | **EMB-WEAK-SCOPED** |
| **M2 CONTROL** (audio-TYPE) | `glap` (transformers) | audio↔text | **8 / 60 = 0.1333** | 16 / 18 (`iot` 11) | 0.1833 | +0.0223 | control (no clause) |
| **M3 CONTROL** (speaking-STYLE) | `clsp` | — | **not flown** | — | — | — | **DROPPED-RUNTIME-ERROR** |
| **M4 CASCADE** | T0 self-transcript → `qwen3-embedding-0.6b-gguf` | text↔text | **45 / 60 = 0.7500** | 17 / 18 (`play` 10) | 0.1667 | **+0.6030** | **CASCADE-ROUTES** |

### Against the registered thresholds (§4)

| clause | result | margin |
|---|---|---|
| **M1 EMB-ROUTES**: ≥ 0.65 | not met | 0.0500 vs 0.65 — short by 0.6000 (36 samples) |
| **M1 EMB-WEAK-SCOPED**: ≤ 0.30 with `POOLING-OVERRIDE-PRESENT` | **MET** | 0.0500 vs ceiling 0.30 — clears by 0.2500; the scoped name fires because flight gate (a) recorded the override |
| **M4 CASCADE-ROUTES**: ≥ 0.65 | **MET** | 0.7500 vs floor 0.65 — clears by 0.1000 (6 samples); M4 needed 39/60 and returned 45/60 |
| **M4 CASCADE-WEAK**: ≤ 0.30 | not met | — |
| **CONTROL-ANOMALY**: max(M2,M3) ≥ max(M1,M4) AND ≥ 0.30 | **NOT FIRED** | max(M2)=0.1333 vs max(M1,M4)=0.7500 — fails BOTH conditions (0.1333 < 0.7500 and 0.1333 < 0.30) |
| **INCONCLUSIVE-3M** | not reached | — |

### Against the comparators (same frozen 60 SLURP devel samples, same frozen core)

| comparator | scenario accuracy |
|---|---|
| P-FEW FS-NONE closed-set decode routing (cited, consumed) | **0.8167** (49/60) |
| A1′r closed-set decode routing (cited, consumed) | **0.7833** (47/60) |
| **M4 CASCADE (this read)** | **0.7500** (45/60) |
| best constant predictor (always `calendar`, the modal gold class) | 0.1333 (8/60) |
| **M2 GLAP control (this read)** | **0.1333** (8/60) |
| uniform chance over 18 labels | 0.0556 |
| **M1 LCO (this read)** | **0.0500** (3/60) |
| chat-core pooled embeddings (P-EMB-1 / P-EMB-2 / P-EMB-3L, refuted 3/3) | 0.0500 |

**M4 lands 2 samples below A1′r and 4 below FS-NONE — inside the ±2-sample cross-session band the
scoreboard already records between the two decode measurements.** M1 lands exactly on the number
every refuted chat-core construction returned, and below uniform chance.

---

## 2. M1 — the dedicated audio embedder reproduces the attractor pathology, and the result is SCOPED

`pooling_override_present = TRUE` (flight gate (a): one synthetic 2 s sine clip embedded under two
separate LCO boots, `--pooling mean` and `--pooling last`, returned **byte-identical** 2048-dim
vectors, both sha256 `e2be3465…4ead`, while the server demonstrably parsed the flag). Registration §4
therefore substitutes the scoped name. **`EMB-WEAK-SCOPED` is a refutation of the
LCO-on-this-llama.cpp construction, not of LCO and not of the dedicated-embedder hypothesis.**
LCO is a last-token-pooling model; this build never delivered last-token pooling on the audio side,
so the arm was run in a pooling mode LCO's contrastive training never used. The E-1 identity record
already flagged LCO's speech-content fit as UNVERIFIED; it remains unverified.

What the arm actually looks like:

- **Prediction distribution:** `recommendation` 36, `datetime` 7, `takeaway` 7, `play` 6, `news` 4 —
  **5 of 18 labels ever predicted**, 60 % of the mass on one label. `calendar`, the modal gold class
  (8 of 60), is never predicted, exactly as in P-EMB-3L.
- **Confusions are attractor absorption, not semantic error:** `play→recommendation` 4,
  `calendar→recommendation` 3, `datetime→recommendation` 3, `qa→recommendation` 3,
  `transport→recommendation` 3, `weather→recommendation` 3 — gold classes of every kind funnelling
  into one attractor with no visible relation between the gold class and the absorber.
- **The three hits are coincidences of absorption:** two of them are `recommendation` (the label
  emitted 36 times) and one is `play`.
- **Descriptive, unregistered:** re-pairing M1's own 60 predictions to the 60 samples at random has
  analytic expectation **3.283** hits; M1 observed **3** (delta **−0.283**). As with every chat-core
  arm before it, the argmax carries no detectable audio-content signal.
- **Geometry:** 60/60 winning cosines are **positive** but confined to a narrow near-orthogonal band
  (mean **+0.0707**, min +0.0401, max +0.1077). This is not the 400/400-negative reference pathology
  P-EMB-2 measured on Audio2Tool; it is the *near-orthogonal* variant P-EMB-3L's last-pooled arms
  showed (+0.0377 / +0.0042). **Top-1-vs-top-2 margins are minuscule — median 0.00737, min 0.00008,
  max 0.02947** — i.e. the argmax is essentially undetermined across the whole label set.

---

## 3. M4 — the cascade is the working instrument, and it is jitter-robust

45/60 = **0.7500**, against a re-pairing expectation of its own prediction vector of **4.317**
(delta **+40.683**, descriptive/unregistered). This is the first embedding arm in the program whose
argmax carries an unambiguous content signal.

- **Prediction distribution is near-uniform over the label space:** 17 of 18 labels ever predicted,
  top-1 share 0.1667 (`play` 10), top-2 share 0.2833 — no attractor. Contrast M1's 5/18 at 0.6000.
- **Errors are semantically adjacent, not absorptive:** the 15 misses are spread thin, the largest
  cell being `music→play` 2, then singletons such as `calendar→datetime`, `calendar→play`,
  `calendar→takeaway`, `datetime→calendar`, `email→calendar`, `general→alarm`, `general→iot`.
  Correct cells cover 16 distinct labels.
- **Geometry:** 60/60 winning cosines positive, mean **+0.6030**, min +0.3133, max +0.7767 — an order
  of magnitude above every audio-side arm ever measured here, and the first arm whose winners are
  strongly aligned rather than near-orthogonal or anti-aligned.

### Repeat-call jitter (registration §6 / E-1 Mission C) — tolerance holds, argmax stability does NOT

| | |
|---|---|
| pair cosine of the same text embedded twice | **0.9999006** |
| declared tolerance | ≥ 0.9999 — **within tolerance, by 6.3 × 10⁻⁷** |
| L2 distance between the two unit-normalized repeats (δ) | **0.014097** |
| argmax over the same 18 labels | `audio` (call a) vs `play` (call b) — **NOT stable** |

**The registration's claim that "argmax verdicts are unaffected at that magnitude" is falsified as
stated, and rescued by the data.** The jitter pair is the synthetic non-corpus string
`repeat call determinism sample`, which has no scenario content: its own top-1/top-2 margin is
**0.000485**, a coin flip between `audio` and `play`. The scored samples do not live there:

| bound | samples with top-1/top-2 margin below it | of which currently CORRECT | worst-case accuracy if every one flipped |
|---|---|---|---|
| 1 × δ = 0.014097 | 5 / 60 | 1 | 44/60 = **0.7333** |
| 2 × δ = 0.028194 (adversarial flip bound) | 15 / 60 | 5 | 40/60 = **0.6667** |

**Even under the adversarial 2δ bound, with every affected correct prediction flipping to wrong, M4
returns 0.6667 — still above the registered CASCADE-ROUTES floor of 0.65.** The verdict does not
depend on the jitter. The minimum scored margin is 0.00209 (4.3 × the null string's margin) and no
scored sample sits below 0.002.

---

## 4. CONTROL-ANOMALY — not fired, but evaluated against ONE control only

**CONTROL-ANOMALY did NOT fire.** `max(M2, M3) = 0.1333` vs `max(M1, M4) = 0.7500`, floor 0.30: both
conditions fail, and by wide margins. The content-routing result is not confounded by an
audio-event-TYPE space.

**The registered adversarial design was only half-executed.** M3 (`clsp`, the speaking-STYLE control)
was **DROPPED-RUNTIME-ERROR** — `AttributeError: 'CLSPModel' object has no attribute
'all_tied_weights_keys'`, a transformers **5.12.1** vs pinned-remote-code **4.57.3** incompatibility
of a *present* dependency. Nothing was installed, downgraded or patched, per the registration's
"never pip-installed" clause and the charter's prohibition on undisclosed instrument modification.
Consequences, stated plainly:

1. **The style confound went untested.** No number in this document excludes the possibility that a
   speaking-STYLE space matches or beats a content-aligned model on content routing. The
   CONTROL-ANOMALY evaluation above is an evaluation **against GLAP alone**, and must be cited that
   way. It does not become a two-control result by omission.
2. Because M4 (0.7500) is a *text-only* arm, a style control could not have confounded it in any
   case — CLSP's absence bears on the audio-side claim (M1/M2), not on CASCADE-ROUTES.
3. CLSP re-entry requires an **environment change** (an isolated venv, or the model's own pinned
   transformers branch), which is a new registration item, not a re-run.

### GLAP is the secondary finding worth carrying

M2 returned **0.1333 (8/60)** — numerically identical to the best constant predictor, but produced by
a genuinely dispersed argmax (**16 of 18 labels ever predicted**, top-1 share 0.1833), and **+4.750
above the expectation of re-pairing its own predictions at random** (8 observed vs 3.250 expected).
Its cosine profile is mixed-sign (44 positive / 16 negative, mean +0.0223, range −0.0486 to +0.1312).

**Every generation-core embedding construction the program has measured sat AT or BELOW its own
shuffle expectation. A dedicated contrastive audio-text model, even one whose training target is
audio TYPE rather than linguistic content, sits clearly ABOVE it.** That is weak evidence that the
audio-side embedding path is not dead in principle — it is 2.4 × chance and still 0.5670 below the
cascade, far under the 0.30 registration floor, and it is a CONTROL, so no clause attaches. It is
recorded here as a design input, not a result.

---

## 5. Cross-arm structure — the arms do not agree, because they are not deciding on the same thing

| pair | per-sample predicted-label agreement |
|---|---|
| M1 (LCO) vs M2 (GLAP) | **1 / 60 = 0.0167** |
| M1 (LCO) vs M4 (CASCADE) | **3 / 60 = 0.0500** |
| M2 (GLAP) vs M4 (CASCADE) | **11 / 60 = 0.1833** |

Correct-set overlap: **M1 ∩ M4 = 2**, **M2 ∩ M4 = 7**, **M1 ∩ M2 = 0**. Only **2** samples that M4
misses are recovered by either audio arm — i.e. the audio arms contribute essentially nothing M4 does
not already have, and nothing the two audio arms share.

---

## 6. Interpretation scope, fixed before the read

- **`EMB-WEAK-SCOPED` is stack-scoped.** It refutes LCO-Embedding-Omni-3B **as reachable through this
  pinned llama.cpp build with the audio pooling override in force**. It is not a model-level
  refutation, not a refutation of last-token pooling (which this build cannot deliver on audio), and
  not a refutation of the dedicated-embedder hypothesis. The pooling-override defect is now
  reproduced on **two entirely different models** (P-EMB-3L's local core and P-EMB-3M's LCO) and is a
  property of the build.
- **`CASCADE-ROUTES` is a text-side result about a speech carrier.** The 60 query vectors are
  embeddings of the frozen core's OWN T0 self-transcripts (from the consumed `SAEA-PROBE-pkey2-338`,
  registry sha256 `f8f6426a…4959`, 60/60 present and re-verified at M4 entry). No audio embedding is
  involved. The result therefore **extends the P-KEY ~89 %-text-side pattern to representation
  matching** and says nothing about audio-native routing.
- **Cost honesty.** The cascade is not "routing at a fraction of decode cost" in the §4 sense that
  clause was written for (that clause names M1, the audio arm). Per sample the cascade still needs
  one frozen-core generation call to produce the transcript. Its leverage is different and real: the
  label side is an embedding lookup that scales to 152 tool rows — or arbitrarily many — without
  prompt growth, and the transcript it consumes is already produced for the supply and filling tiers.
  Zero generation contacts were spent by this flight because those transcripts already existed.
- **CONTROL-ANOMALY was evaluated against GLAP alone** (§4 above). Cite it with that scope.
- **No cross-probe vector comparison was performed**, and no vector values were compared across
  probes. Comparators are CITED from consumed probes, not co-measured.

---

## 7. What this decides for the routing tier

**An arm cleared 0.65, so the embedder path has a working instrument. It is named here:**

> **The M4 CASCADE — frozen-core T0 self-transcript → `qwen3-embedding-0.6b-gguf` (Q8_0, umbrella
> lock `qwen3-embedding-0.6b-gguf`, pinned llama.cpp `--embedding --pooling last`, text↔text) →
> argmax cosine over the label set — routes at 0.7500 on the frozen 60.**

**Its next step toward the A2T surface:** run the SAME instrument on the P-EMB-2 tool-routing
surface — the 400 frozen A2T samples against the 152 tool-registry rows, with the primary axis the
183 tool-wrong ids that no supply form reaches. P-EMB-2 measured that surface **audio-side** and
returned top-1 2/183 at chance with 400/400 negative cosines (`EMB-CLOSED`); the failure was on the
audio side, which the cascade removes. This is the highest-value successor because the tool surface
is where an embedding lookup beats a prompt: 152 rows do not fit a closed-set decode prompt the way
18 labels do. It requires its own registration, exposure row and owner-scoped ceilings, and a source
check for T0 self-transcripts over the 400 A2T ids (a transcription supplement if absent). **Nothing
here authorizes it.**

**What remains untested — carried forward verbatim:**

1. **The nemotron escalation was never flown.** `omni-embed-nemotron-3b` is the only local candidate
   with *measured* audio-content retrieval (NDCG@10 0.82 LPM / 0.54 FineVideo, E-1 Mission A) and it
   is the strongest evidenced fit. It was excluded from this registration by design (NVIDIA OneWay NC
   license + a pinned `v4.51.3-Qwen2.5-Omni-preview` transformers branch, i.e. an environment change).
   It is a **pre-authorized escalation requiring its own registration**. Audio-side routing is
   therefore refuted only for the constructions actually flown, never for the best candidate.
2. **CLSP re-entry needs an environment change**, not a re-run (transformers 5.12.1 vs pinned 4.57.3).
   Until then the speaking-STYLE confound on the audio side is untested.
3. **The LCO result is stack-scoped while the pooling override stands.** A model-level reading of M1
   requires either a llama.cpp build whose `--pooling` flag actually reaches the audio side, or LCO
   driven through a non-llama.cpp stack. Both are environment changes.
4. **Audio-native routing remains without a working lever.** The best audio-side number the program
   has ever measured is a CONTROL at 0.1333. The scheme's speech-native routing claim does not
   advance on this read.

**What the routing tier falls back to for audio-native routing:** **closed-set decode**
(A1′r 0.7833 / FS-NONE 0.8167), which remains the only lever that consumes the speech signal
directly and is still the tier's best measured number. The cascade joins it as a second working
lever — cheaper to scale on the label side, but text-mediated, so it inherits every transcription
error the core makes and cannot be claimed as speech-native.

---

## 8. Bounds carried by every statement above

n = 60 SLURP devel, 18 canonical labels, four registered arms of which **three flew**, one run per
arm, one carrier, one frozen core, discovery tier. One control (CLSP) never flew, so the adversarial
control design is half-executed. The re-pairing-expectation figures in §2/§3/§4 are **descriptive,
unregistered, analytic** and carry no clause; no permutation simulation was run. The jitter-flip
bounds in §3 are analytic worst cases from a single measured repeat pair, not a repeat-run
distribution. Comparators (0.7833 / 0.8167 / 0.1333 / 0.0500) are **cited** from consumed probes, not
co-measured. Gold scenarios were used scoring-side only and never entered a runtime path. SLURP audio
CC BY-NC 4.0 carried. No test split was touched. No superiority, generalization, deployment, or
paper-scale claim attaches to any number in this document.

## 9. Addendum (2026-09-08): binding-config sha256 re-pinned, this flight's evidence unchanged

Umbrella commit `faebc8f` (owner Decision 11-D: commit the pending umbrella lock changes and
re-pin the study's P-EMB hashes, chosen over reverting the lock) resolved the umbrella lock's
`lco-embedding-omni-3b-gguf` entry from an unresolved local candidate (`LOCAL_CANDIDATE`,
`UNRESOLVED_LOCAL_SOURCE`) to a real Hugging Face source (`marksverdhei/LCO-Embedding-Omni-3B-GGUF`
@ `af8a36fbb6e7629c9dbcb218478c6b1477b36e09`, lifecycle `AUXILIARY`, 3 verified files with per-file
sha256; `glap`/`clsp`/`qwen3-embedding-0.6b-gguf` unchanged). `rails.probes.pemb3m_flight.
BINDING_CONFIG_SHA256` was re-pinned to the digest this resolved entry now produces; the prior
digest is preserved as `BINDING_CONFIG_SHA256_AT_FLIGHT` and still matches this flight's own sealed
`flight-receipt.json`/`config-values.json` `binding_config_sha256` field verbatim (test
`test_binding_config_sha256_at_flight_matches_the_sealed_pemb3m_receipt`) — **this flight was not
re-run and its evidence above is unchanged.** The lock's pre-`faebc8f` entry carried no per-file
sha256 for this model (only an aggregate size/file count, which moved by 1,462 bytes as the file
count dropped 5 → 3), so the lock's own metadata alone cannot prove the model bytes are identical
across the two lock versions; corroborating, not certifying, this flight's own
`model_file_measurements` independently hashed `LCO-Embedding-Omni-3B-Q8_0.gguf` and its mmproj
file at flight time, before the lock carried any per-file hash, and both measured values equal the
two GGUF hashes the resolved entry now pins (its third file, `README.md`, was never independently
hashed here). Any future reuse of this embedder must re-verify against the resolved lock entry
rather than lean on this note.
