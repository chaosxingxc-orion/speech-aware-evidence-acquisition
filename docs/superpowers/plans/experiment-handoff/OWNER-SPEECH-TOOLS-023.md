# OWNER-SPEECH-TOOLS-023

Date: 2026-09-12

## Owner input

Construct effective local speech tools for the multimodal agent system. Whisper is one example, not the entire tool set. Let the Reviewer trigger investigation when it has high confidence that an error or missing evidence exists; the owner explicitly confirmed this interpretation. Download selected tools and weights locally into WSL and load them for local use.

## Root interpretation and execution

Preserve Reviewer critique, Planner control and frozen Solver answer authority. Treat auxiliary ASR as evidence, not a second task answer. Separate trigger quality, tool evidence quality and evidence-use quality.

Prepare official Whisper large-v3, Silero VAD, FFmpeg/ffprobe, and alignment/diarization capabilities. Reuse existing pinned MMS_FA and sealed Sortformer infrastructure first. Acquire pyannote community-1 when existing access permits it. Do not accept gated model conditions for the owner. Keep WhisperX an optional source integration rather than duplicate large-v3 weights.

Acquisition runs in isolated WSL paths and permits downloads, hashes, imports and CPU load-only validation. No research speech or reference material is read, no neural forward pass is performed, and the active Audio2Tool GPU source remains frozen. Future dataset use requires shared tool registration and a prospective experiment.

Read the full design in docs/readiness/2026-09-12-speech-tool-system-plan.md and the acquisition scope in docs/readiness/2026-09-12-local-speech-tools-acquisition.json.

## Scientific sequence

Close the active Audio2Tool comparison. Use SLURP for the first fast tool-availability comparison with matched stage structure. Then test the error-trigger policy against matched random selection, and only then add a named missing capability. Judge success by native task outcomes, corrected and newly harmed cases, and the role of OBS/ORG/SUPPLY/USE. Carry the resulting shared system to Audio2Tool and E21, with E22 development only under an admitted scope.

No training-free policy result is claimed by this decision. The planned tool/state/action interfaces provide the optimization surface for that later comparison.
