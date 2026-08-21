# Feature-cache and speech-packet directory convention

This document distinguishes two artifacts with different trust and runtime
roles. A legacy ``.feat`` cache is an encoder-side preprocessing accelerator.
A ``SpeechFeaturePacketV1`` tree is the audited decoder input used by formal
mmproj-free inference. They must never be treated as interchangeable.

The llama.cpp mtmd feature-cache patch
(`docs/patches/2026-08-11-mtmd-feature-cache.diff`) keys a persistent,
on-disk cache of audio-chunk encoder embeddings off a single environment
variable, `LLAMA_MTMD_FEAT_CACHE_DIR`, read by the spawned `llama-server`
process. This file is the single place that names the convention for
choosing that directory; the mechanics of how the variable reaches the
server are documented in `core/session/lifecycle.py` (`feat_cache_dir`,
`FEAT_CACHE_DIR_ENV`, `FEAT_CACHE_DIR_DEFAULT`) and
`scripts/run_arm_sequence.sh` (`--feat-cache-dir`).

## The rule

```
/home/chao/feat-cache/<dataset>-<encoder>/
```

for every **new** dataset campaign. `<dataset>` is a short, semantic segment
(e.g. `slurp`), `<encoder>` names the mmproj/encoder the cache was built
against (e.g. `q4km`) — cache entries are **mmproj-encoder-specific**: a
cached embedding was produced by one specific encoder and is only ever
valid for a server running that same encoder. Mixing encoders under one
directory risks a false cache hit serving the wrong encoder's features to a
decode step that never actually ran that encoder.

## The one exception: `q4km`

`q4km` (i.e. `/home/chao/feat-cache/q4km`, with no dataset segment) is the
**legacy** directory, already warm for the earnings21/22 family:

- 26GB, built and consumed across the featcache-bench and P2 R-ladder work
  (`docs/arms/featcache-bench.arms`, `docs/arms/featcache-np8.arms`,
  `docs/receipts/runtime-q4km-featcache.json`).
- It predates this convention (named for the encoder alone, no dataset
  segment), and every model config fragment that references it today
  (`configs/model/q4km-featcache.json`, `q4km-featcache-np8.json`,
  `q4km-featcache-validate.json`, `q4km-evid-v3.json`, the four
  `q4km-hbmfree-*` fragments, and the three `qwen3-omni-llamacpp-q4km*`
  fragments) hand-types this exact literal path in its own `server_env`.
- **It MUST NOT be renamed or moved.** Renaming it would silently orphan
  every one of those already-hashed config fragments (their
  `server_env.LLAMA_MTMD_FEAT_CACHE_DIR` value is part of `config_hash`,
  W3 2026-08-11) and cold-start a re-encode of everything already cached.
- It remains the default: `core/session/lifecycle.py::feat_cache_dir()`
  returns this exact path when `SAEA_FEAT_CACHE_DIR` is unset, so nothing
  that already relies on the literal string changes.

A **new** dataset never reuses `q4km` — even if it happens to share the
same encoder — because the directory name is the operator-visible signal
of which dataset's audio produced these cached embeddings. Example for a
SLURP campaign on the same `q4km`-encoder build:

```
/home/chao/feat-cache/slurp-q4km/
```

## How a run points at its directory

Two ways, from lowest to highest precedence (mirroring
`core/session/lifecycle.py::start_session`'s `os.environ` + `extra_env`
merge, where `extra_env` — a model fragment's own `server_env` — always
wins):

1. **Operator/launch-level, opt-in, per invocation** —
   `scripts/run_arm_sequence.sh --feat-cache-dir /home/chao/feat-cache/<dataset>-<encoder>`
   exports `LLAMA_MTMD_FEAT_CACHE_DIR` for that sequence only. Omitting the
   flag changes nothing (empty by default); this is the mechanism new
   campaigns should reach for first, since it needs no new config fragment.
2. **Config-fragment level, explicit, identity-bound** — a model fragment's
   own `"server_env": {"LLAMA_MTMD_FEAT_CACHE_DIR": "/home/chao/feat-cache/<dataset>-<encoder>"}`
   (the pattern every existing `q4km-*` fragment already uses). This bakes
   the directory into `config_hash`, which is correct when the directory
   choice is itself part of what a run's identity should pin down.

`core/session/lifecycle.py::feat_cache_dir()` (env var
`SAEA_FEAT_CACHE_DIR`, default `FEAT_CACHE_DIR_DEFAULT` =
`/home/chao/feat-cache/q4km`) is the single source of truth code and
operators should both defer to for "what is the default cache directory"
rather than re-typing the literal string.

## ext4 only

Every feature-cache directory — legacy `q4km` and every future
`<dataset>-<encoder>` directory alike — lives under `/home/chao` on the
WSL2 ext4 filesystem, **never** under `/mnt/e` (`SPEECHRL_DATA_DIR`). The
9p mount under `/mnt/e` is the known slow path for repeated small-file
read/write traffic (see the ext4-first model-mirror rationale in
`core/session/lifecycle.py` for the same class of finding against GGUF
reloads); a feature cache is precisely that traffic pattern — one small
file per audio chunk, read or written on nearly every decode step.

## Formal mmproj-free handoff

The SLURP Q4_K_M preprocessing and inference roots are deliberately separate:

```
/home/chao/feat-cache/slurp-q4km/          # legacy preprocessing cache
/home/chao/feat-cache/slurp-q4km-packets/  # formal packet handoff
```

The preprocessing process may load the pinned decoder and mmproj, populate or
reuse ``slurp-q4km``, and promote each required recording into a complete
``SpeechFeaturePacketV1`` under ``slurp-q4km-packets``. It must finish and exit
before formal inference starts. A missing legacy entry fails closed during
model-free promotion; promotion never silently encodes a cache miss.

The formal server loads the decoder from the fast ext4 model root
``/home/chao/models/qwen3-omni-30b-a3b-instruct-gguf-q4km`` and is launched
with the exact ``--no-mmproj`` boundary. Its environment contains
``LLAMA_SPEECH_FEATURE_ROOT`` and ``LLAMA_SPEECH_DECODER_SHA256`` only. It must
not contain ``LLAMA_MTMD_FEAT_CACHE_DIR`` and therefore cannot consult or
populate the preprocessing cache.

## Bounded validation concurrency

Independent small-file checks are intentionally concurrent. SLURP train-media
existence checks use a bounded 16-worker pool, and packet manifest/chunk
validation uses a bounded 8-worker pool. Both collect results in input order
and propagate the first input-ordered failure, so concurrency does not alter a
binding or weaken fail-closed behavior.

A standard SHA-256 over one GGUF is sequential by definition. The decoder's
full digest is therefore computed as one stream and retained through the
receipt-bound identity cache for eligible repeated checks. Concurrently
reading the decoder and mmproj from the same device is not used as a proxy for
faster validation: it can increase device contention and cannot accelerate the
single decoder digest required by formal inference.
