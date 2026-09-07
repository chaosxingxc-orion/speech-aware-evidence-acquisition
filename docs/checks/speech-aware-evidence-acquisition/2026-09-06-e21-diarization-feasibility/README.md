# Which diarization route exists on this machine — both, and Route B is selected

An **environment inventory**, not an exposure event. It hashes files, probes which interpreters can
import what, and invokes the pinned runtime binary only for `--version`, `help diarize` and
`doctor --json` — none of which loads a model or reads one byte of corpus audio, all with
`CUDA_VISIBLE_DEVICES` empty. **No frozen-core contact, no GPU, no corpus audio, no install.** The
corpus diarization pass is separately pre-registered as `SAEA-E21-TOOL-DIARIZATION-V1`
(`docs/readiness/2026-09-06-e21-diarization-obs-v1-preregistration.md`) and **has not been run**.

Generator: `scripts/e21_diarization_feasibility.py`. Every tool fact — revision, payload sizes and
SHA-256s, deployment runtime, binary hash, `research_role`, `claim_limit` — is read from the umbrella
lock through `data.lock` at run time; none is copied into this repository.

## The tool

`diar-sortformer-4spk-v2` — NVIDIA streaming Sortformer v2, 117 M parameters, 16 kHz mono, **max 4
speakers**, revision `5240a640…`, CC-BY-4.0, ungated. `research_role`: *frozen tool-level speaker
diarization … TOOL_DIAR tier*.

Both governed payloads are present and **byte-identical to the lock's pins**, re-hashed here:
`diar_streaming_sortformer_4spk-v2.nemo` (471,367,680 B) and
`diar_streaming_sortformer_4spk-v2.q8_0.gguf` (147,075,776 B).

## The two routes

| | route A — NeMo reference | route B — NeMo-Speech.cpp |
|---|---|---|
| payload | the fp32 `.nemo` | the first-party `q8_0` GGUF |
| host | isolated venv `~/.venvs/diar` | CUDA build of `nemo-speech` at pinned commit `4c749a70…` |
| present | **yes** — `nemo` and `torch` both importable there | **yes** — binary SHA-256 `1a3e3f4f…` matches the lock's `binary_sha256` exactly |
| **live** | **yes** | **yes** |

`nemo` is **absent from the shared `~/.venvs/speechrl`**, which is the correct state and stays that
way: nothing in this study installs it there, or anywhere. `ffmpeg` is absent from PATH, as pinned.

**Route B is selected.** It is the deployment path the lock itself designates, its binary identity is
pinned and verified, it emits RTTM directly, and it diarizes a whole directory in one process with
one model load. Its CLI, read from the binary:

```
nemo-speech diarize INPUT [--model MODEL] [--device cuda[:N]|cpu] [--preset streaming|offline]
                          [--format text|json|rttm] [--output-dir DIR] [-r] [-c N]
                          [--onset|--offset|--pad-onset|--pad-offset|--min-duration-on|--min-duration-off]
```

`doctor --json` reports `diarization: true`, `backend_cuda: true`, and — with
`CUDA_VISIBLE_DEVICES` emptied for this probe — `accelerator_available: false` with a CPU-only device
list. That refusal is the evidence the probe touched no GPU.

Route A stays as the named fallback if Route B's output disagrees with itself on the pass's preflight
call.

## The limitation this receipt exists to surface

The lock's own `claim_limit` records a **4-speaker design bound**. Earnings calls routinely carry more
— operator, several executives, a queue of analysts — so on this carrier the tool is used outside the
population it was designed for. The preregistration's §6 states how the pass reports that rather than
absorbing it, and why no diarization error rate is claimed anywhere.

## Files

| file | what it holds |
|---|---|
| `feasibility.json` | both routes with every probed fact, the re-hashed payloads, the binary identity comparison, the captured CLI and `doctor` output, and the zero-contact statement |
| `MANIFEST.sha256` | this directory's own byte manifest |
