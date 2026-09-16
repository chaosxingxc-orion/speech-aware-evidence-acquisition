# STATUS-140: SLURP is not advanced; E21 static fit materializes

Date: 2026-09-16. The E21 static fit is still materializing. No final fit receipt exists, and generation remains formally held.

The frozen SLURP broad/factored TRAIN-A campaign finalized generation with
5,407 contacts at 2026-09-15T21:38:55 UTC. Its structural gate receipt is
DATA/coordination/slurp-broad-factored-v1/postseal-structural-gate-v1.json,
SHA-256
`d8d1b02aeedd8ccad90fd55f8b861708e52af6f2fba8894dbbab57161b416ff1`.
Root persisted the paired quality release at
DATA/coordination/slurp-broad-factored-v1/root-paired-quality-release-v1.json,
SHA-256
`0ceb82d0bf4f34542ea73fb24d6012cfde7d0de02842d1587b5eceb459884de8`.

The [registered analysis recipe](../../../readiness/2026-09-15-slurp-broad-factored-train-a-analysis-recipe-v1.json) remained source-bound. Root's primary verdict is recorded at
DATA/coordination/slurp-broad-factored-v1/root-primary-verdict-v1.json,
SHA-256
`757f42ccb810838e9670014649e79f8dc90f2394cdeb25f30e6fdda9407d4aff`.
The [root report](../../../results/2026-09-16-slurp-broad-factored-train-a.md)
preserves the registered result. The complete shared paired analysis reports a natural-mixture SLU change of
-0.898973 percentage points with CI95 [-2.607721, +0.782103] and an
equal-scenario change of -1.339493 percentage points with CI95
[-2.972230, +0.436023]. The formal decision is
`NOT_ADVANCED_FULL_TASK_GAIN_GATE_FAILED`: the analysis does not establish
overall harm statistically, but it does not demonstrate improvement. Entity-pair
F1 changes by -2.031629 percentage points with CI90
[-3.758411, -0.329307].

The final analysis closure is
DATA/coordination/slurp-broad-factored-v1/root-analysis-closure-v1.json,
SHA-256
`35255922134dbd95689c8416e5f9ff0a402cc3ce77b93bde7c89e21da1e602d3`.
Candidate coverage changes from 937 to 947 of 1,080
(86.7593% to 87.6852%). Among the same 917 rows covered by both arms, final
correctness changes from 834 to 824. Non-exact slots change from 525 of 842 to
540 of 841. Among the same 807 intent-correct rows, exact entity sets change
from 303 to 293. Planner records 1,080 ACCEPT and 2 REVISE decisions; 1,081
analytical tool calls and zero observation calls occurred. There were no output
cap or length stops.

The SLURP analysis is closed and no successor is admitted. The legacy optional
own-card suffix mapping could not represent the factored store's non-label
value, so root removed that unsupported optional metric and completed the
unchanged base stage projection. No official rescore or model rerun occurred,
and these stage diagnostics do not support a causal claim.

Root resumed dispatch at about 2026-09-16T02:11 UTC. The prior SLURP server
stopped at the 02:13:24 custody boundary. The boundary receipt records about
4.5 hours of delayed root dispatch; its cause is not established. Do not label
that interval scientific waiting. The Audio2Tool np3 server loaded at 02:14 UTC,
the shared monitor began before dispatch, and the first campaign process started
at 02:20 UTC.

The first Audio2Tool campaign process, PID 335954, exited at
2026-09-16T02:21:40 UTC before any model contact or attempt ledger opened.
Preflight raised `GateClosed` because the exposure-ledger carrier column named
`Audio2Tool original-speech union4000` instead of exactly one carrier lock
key. The original source and failure log remain preserved. Root corrected only
that ledger registration in an isolated successor. No Audio2Tool generation
began.

The failed launch metadata is bound by these receipts:

- DATA/coordination/a2t-scope-tools-registration-v1/root-slurp-to-a2t-boundary-v1.json,
  SHA-256
  `47752303548d3474658e095e24d7e52dbb5042de976347dc75de6508ad46e734`;
- DATA/coordination/a2t-scope-tools-registration-v1/root-serving-launch-v1.json,
  SHA-256
  `a64c1b01e20055a2874401a0701df9cd0dbeedbfac3602261d91736d9b608a9e`;
- DATA/coordination/a2t-scope-tools-registration-v1/root-monitor-launch-v1.json,
  SHA-256
  `55943271aead84e34bd680b4fdcb62bd400f3824c006bbacfc857572aaceec50`;
- DATA/coordination/a2t-scope-tools-registration-v1/root-campaign-launch-v1.json,
  SHA-256
  `ff379ea58f17bf2cfd5c67a2f01df9c0bc4a735fe680c5cb4b9001ee03aaaa09`;
- DATA/coordination/a2t-scope-tools-registration-v1/root-campaign-process-exit-v1.json,
  SHA-256
  `fcbf317b65adddc8011fe1d019bf1459a2635e2e36d7d8ef085f55ae7336fa7c`;
- DATA/coordination/a2t-scope-tools-registration-v1/observer-initial-failure-v1.json,
  SHA-256
  `156a4d604eb03aec7cf9e51df838149bf63454379be6336cac425666842757eb`.

The failed launch used source
`219e305f306f11998e39c44b5fb055b4fcfb3179`, server PID 335471 and monitor
PID 335883. Root then committed the two-file carrier-case correction at
`790c176f847496c6d2fd8b9d0aeed0b9156f2173`. Its validation receipt is
DATA/coordination/a2t-scope-tools-ledger-correction-v1/validation-v1.json,
SHA-256
`7d4e7181f7013773efba49275bbc02cbe670a9eaebb64571fad92a03092ebced`.
All four exposure rows parse and bind successfully, and direct preflight passes.

System preflight independently fails before attempt or contact because the
Perception request requires 34,868 tokens for a 32,768-token slot; the physical
margin is -2,100 tokens and the required-reserve operational margin is -10,292.
The corrected source is not ready to freeze. Root closed the original A2T
dispatch path and stopped its service normally at 02:42:34 UTC. CPU feasibility
commit `a4576cf438ff2fb14b162c6c07c5e65acb17a787` establishes the np2
candidate geometry, but the shared hard-coded 32,768-token coarse rail still
blocks it despite an actual 49,152-token slot. Root authorized a bounded shared
configuration-limits fix in isolated source while preserving default identity
and reserve behavior. It has no GPU proof yet and must pass a future four-row
proof before a full flight. No Audio2Tool generation, fit or model contact
occurred, and no Audio2Tool result was released.

Root advanced the independently registered [E21 direct static fit](../../../readiness/2026-09-15-e21-native-window-direct-fit-registration-v1/README.md) under
DATA/coordination/e21-native-window-registration-v1/root-a2t-precontact-to-e21-boundary-v1.json,
SHA-256
`3ad4ba5e27ba21a9caea8e8e3b4853a488aed61f2f848cb085acf89d190efba7`.
All 5,732 frozen files at
`1daad5186119b23c3414e36676afb296599dc29f` were verified. The E21 server is
PID 338888, the monitor is PID 339094, the direct static fit worker is PID
339183 and the lease owner is PID 339182. The fit started at
2026-09-16T02:44:51 UTC with a cap of 4,780 endpoints over 1,593 units.

The launch receipts are:

- DATA/coordination/e21-native-window-registration-v1/root-serving-launch-v1.json,
  SHA-256
  `a8638e730989038ebc97537ee3f72cffa43589c5b03bc5470ead36b42d9db2fd`;
- DATA/coordination/e21-native-window-registration-v1/root-monitor-launch-v1.json,
  SHA-256
  `5b184a8d2b7d5225d62114c7633087efc169a5b8c53f4c84733fca8c5e40187e`;
- DATA/coordination/e21-native-window-registration-v1/root-direct-fit-launch-v1.json,
  SHA-256
  `ac5caf2f1afe955f0880e09f784c73d16bed241c09d44fc6b204d15bcf3daf43`.

Current fit activity is additionally bound in
DATA/coordination/e21-native-window-registration-v1/root-active-handoff-v1.json.
The GPU is resident for the E21 fit, but generation is not active. Do not infer
maximum load from fit materialization. E21 generation remains held until the
static fit passes and root completes a separate final registration. The
final-registration checkout derived from `1daad5186119b23c3414e36676afb296599dc29f`
contains documentation scaffolding only and cannot dispatch. Native fit and CPU
ASR also remain held and unregistered.

Preserve the SLURP, Audio2Tool, E21 order, all original failure provenance and
prior historical verdicts. Stable benefit for the queued versions and
trajectory-sampling or training-free RL remain unproven. This handoff update performs no model, tool, scorer or service contact and reads no new task outcome.
