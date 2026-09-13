# Prospective native speech evidence readiness

Keep this candidate version held until the current direct-versus-native pair
has a complete analysis and names an error component that warrants extension.
Preparation is not admission. No Whisper inference, audio read, model load,
tokenizer endpoint or scorer contact occurred in this work.

## Reuse the implemented native tool

The existing live speech observation tool supports model-selected full-utterance
Whisper evidence. Configure it only in Reviewer. Perception and Solver remain
knowledge consumers; Planner retains decision authority and Solver retains
answer authority. Reviewer may call only for a concrete suspected speech error
or missing decisive speech evidence, with a named lexical distinction. Treat
the transcript as fallible evidence. Do not trigger merely because a knowledge
card lists a slot, and reuse any transcript already returned in the episode.

Preserve Reviewer=3, Planner=1 and at most one revision. The current bound supports
two native tool interactions followed by a review. No additional framework or
answering model is introduced. The complete-system comparison remains primary;
no knowledge ablation is queued.

## Resolve the actual source-version discrepancy

The old inventory declares openai-whisper 20250625, but installed distribution
metadata is absent. All other declared dependency versions match. The backend
already imports the declared local source directory and rejects any other
import location. Do not install packages into the active shared environment or
pretend that a distribution is installed.

The explicit saea-local-whisper-runtime-inventory-v2 successor selects a
pinned-source-file version origin. Verify all declared source/checkpoint bytes,
then parse the hash-bound whisper/version.py as exactly one literal __version__
assignment without importing or executing Whisper. Dependencies still require
exact installed metadata. Historical v1 inventories retain their strict
distribution requirement; missing metadata never silently activates a fallback.

The real successor inventory passed this model-free verifier. Its SHA-256 is
e5e6d37646438ab57bb3362ced18726cde4f2762a2893f7e6a416e7e484d0427.
The verification receipt SHA-256 is
5863c96a720b14030bdd746feb6dd910914c6f507ca07b7a52699f7a53011c32.
Both live under
prepared/SAEA-SLURP-NATIVE-SYSTEM-LIVE-SPEECH-PREPARE-V1 in the data root.
The original inventory remains unchanged.

Validation: 61 focused preparation, backend and live-observation tests passed
in WSL, including explicit-source opt-in, unchanged v1 refusal, wrong dependency
version, tampered source, wrong version and nonliteral version rejection.
No test loaded neural weights.

## Preserve pending decisions

The source inventory binds the existing 1000 speech packets without opening
audio. The CPU decoding protocol retains English, temperature zero, beam five,
batch one and the 256-token ASR ceiling. Its cpu_workers=4 controls audio
preparation, not the inference library's thread pool. Before activation, pin
CPU library thread limits in the worker environment and record them rather
than claiming that the existing field does so.

The live-ASR ExecutionPlan, exposure row, attempt output namespace, model/fit
and scoring registrations, and final capability admission remain unset.
Do not turn a successful inventory verification into a claim of on-demand
decode success or task-quality benefit.
