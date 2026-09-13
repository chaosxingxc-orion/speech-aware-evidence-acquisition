# Native speech tool engineering result

Decision: **NOT QUALIFIED AS A COMPLETE AGENTIC BASELINE**.

The four-row run SAEA-SLURP-NATIVE-TOOLS-ENGINEERING-V1 completed and finalized from source commit 3781f738e0d0391bc856b2e6c9e3f85bd006fa4a. The complete official TRAIN scorer ran once. There were 12 Qwen generation contacts, 39 actual capacity endpoints, eight selected internal ASR invocations, four cold CPU Whisper forwards, and four warm cache hits. Every real phase request fitted the registered service. The source-bound transcript was absent before selection and present exactly once in each of the eight successor requests.

All four terminal outputs were escaped tool-call markup instead of the requested SLURP JSON answer. Official intent, scenario and action accuracy were all zero. This is an engineering failure diagnostic on four rows, not evidence of task effectiveness or a model capability ceiling.

The observed defect is precise: final tool_choice=none produced a textual tool-call frame, with no structured API tool_calls. The shared native controller treated the absence of structured calls as an answer without a terminal frame check. The acquire-oriented engineering instruction also repeated in later phases. Actual transcripts were supplied, so missing OBS transport is ruled out for this run; the effect of improved phase instructions remains untested.

Preserve the run and first score. Next, use distinct acquisition, evidence-use and terminal instructions through the shared phase-material configuration, quarantine escaped internal calls at terminal delivery, and complete actual active-roster fitting for native early stopping. Prove those cases with the real shared executor and fake transport, then register at most one four-row recovery. This result authorizes no full efficacy flight and no hidden rerun.

The stale prior TRAIN-A lease initially refused dispatch before any new attempt opened. Root archived it only after confirming its owner PID was absent, its prior attempt was ABORTED with zero contacts, no active socket remained, and consecutive resident monitor samples showed four idle slots and zero requests. The resident service was preserved.

The source-bound root verdict is DATA/coordination/slurp-native-tools-engineering-v1/root-verdict-v1.json, SHA-256 fdfda1572010a6a1c017ff1a151c213f7c82925d273f9ae8443af94d3c6f258b. Detailed per-sample metadata and artifact hashes remain in that receipt; raw traces and transcripts remain outside Git.
