# Status 015: completed G1 generation and revised feature serving

Date: 2026-09-10 UTC. Supersede STATUS-014 as a coordination snapshot; preserve its historical bytes.

## Service and owner direction

The recovered G1 resident service has stopped after all three 1,000-row arms finalized and completed one whole official score each. Do not restart G1 or replay any completed arm. The actual G1 session used `--no-mmproj`, only the decoder model, and prepared speech packets. Current GPU telemetry reports no allocation. The stopped monitor reports 46.69% parked time; this is an efficiency gap, not a reason to add unregistered generation.

Follow OWNER-FEATURE-SERVING-007: prepare neural speech features before generation and keep mmproj out of resident GPU memory. G2 already has a decoder-only packet model. Existing E21 V1 DR/LOOP GPU-mmproj configurations must not dispatch unchanged. A read-only local audit is comparing strict per-window packet support with the smaller raw-input/fresh-cache/CPU-projector bridge. No old E21 feature cache is admitted by this direction. The owner clarification about GPU use during the separate encoding window is pending; no new encoding occurs now.

## G1 scientific read

Registered paired analysis completed once, with both NEW500 row-SLU-F1 numerical gates passing: speech minus matched control +6.6374 pp, CI90 [4.6451, 8.6327]; speech minus twin +3.6544 pp, CI90 [1.6033, 5.7033]. Speaker-cluster sensitivities remain positive. These are historically exposed, sealed-predecessor component results. The full per-scenario table, both weightings, OLD500, DEV1000, official aggregate micro and costs are in the 2026-09-10-ku-s3-max256-recovery-verdict receipt.

The raw slot outputs are not complete SLU answers: 456 IDs have different raw scenario/action tuples across arms because entities-only replies are permitted. The historical KC-S1b read explicitly joined the common predecessor intent with each arm's entities. The inherited joined-delivery protection is restored through a tested shared pure extraction and uniform, zero-contact read-side restoration. All 1,000 joined intents match the predecessor across every arm; entity sequences and original source hashes remain unchanged. Root decision is ADMITTED_COMPONENT. Do not claim a complete-system result from the raw score columns. Preserve the control's one length stop, all malformed rows and every original artifact. The restoration was registered before any joined derivative was produced.

## Accepted engineering and pending work

Canonical master includes b85bfa3e (shared retained-count micro-F1 comparison and explicit scorer views) and ac1b7bf2 (one official projected-primary score with a separate raw-label normalized view). Root reviewed both changes. The merged targeted check passed 20 tests, and the engineering base check passed. Frozen G1 source remains 05b0f05e. G2 source remains at 9feffbc2 until a deliberate boundary refresh.

G2 N/twin V2 retrieval preparations have full 1,000-row parity and zero warm recomputation. Before contact, bind the aligned scorer in thin successor configuration, refresh any configuration-bound preparation, finalize scientific closure, register actual np8 fits and freeze the new runtime. Neither N nor twin has generated.

The E21 construction subset implementation is not accepted as an exact-four runtime proof. Its owner agent corrected the overclaim; the combined fitter/OJW fake-transport count test remains incomplete. Keep its isolated commits out of canonical until the actual proof passes.

Next work order: G1 component verdict is frozen; admit aligned G2 preparation/fit; complete E21 feature-serving successor design and shared exact-window support; then run the already registered N/twin comparison. G3 encoding remains N-non-inferiority-gated. G4 samples, E21 DR/LOOP and G6 live complete-system work remain pending.

All implementation, preparation, tests and research execution use WSL Ubuntu-24.04 with an explicit checkout source path. Root retains service ownership and scientific decisions. No paid experiment API, new carrier or Stage-3 work is admitted.

Root additionally reviewed and integrated `2e536e0c`, the shared inherited SLURP delivery join; all 12 focused tests pass. Original G1 artifacts remain immutable.
