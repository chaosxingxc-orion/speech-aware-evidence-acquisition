# Feature-cache require-hit guard review

Date: 2026-09-09

This report accompanies committed source patch cddb000cb45ab44d33c84483cf5e5962cbbaa5bf in the isolated llama.cpp
worktree /home/chao/llama-worktrees/featcache-require-hit.

## Pinned source identity

- Source repository: /home/chao/llama.cpp-featcache
- Original source commit: 04ccc72a2207347ca76161b93fd9d846dd0a8675
- Original tools/server/server-context.cpp SHA-256:
  e235949a10bfa9284b8d79c735b638569e3db533e0eee8da2f3e474ca2701248
- Study worktree base: 3ceef395beee9135bc50c788f6c29450f643cc2e
- Patched source SHA-256 (commit cddb000cb45ab44d33c84483cf5e5962cbbaa5bf):
  5c503c22bd4abe99560acfc427cc828dfd6f8222886fe366c34aece04c4d6e80
- Patch diff SHA-256:
  3c3460432f5a42455747c92bace468f82f752174af9f0c8836c9ee0cb9300ccb

## Guard behavior

The patch adds the opt-in environment flag
LLAMA_MTMD_FEAT_CACHE_REQUIRE_HIT. It is unset by default, preserving the
existing cache miss and encoder fallback behavior.

For raw media chunks, the opt-in mode:

1. Refuses startup-path use when LLAMA_MTMD_FEAT_CACHE_DIR is absent.
2. Refuses the incompatible LLAMA_MTMD_FEAT_CACHE_VALIDATE mode.
3. Requires a valid cache entry before the raw-input path can construct or
   encode an mtmd batch.
4. Rejects RAM entries whose vector length does not match the current chunk
   token count and model embedding width.
5. Rejects disk entries with a short payload or trailing bytes after the
   declared payload.
6. Returns a failure when cached decode fails, instead of falling through to
   mtmd_batch_encode.
7. Adds a final refusal immediately before the encoder path as a defense
   against future fallthrough changes.

The supplied decoder-ready speech-feature path returns before this logic and is
unchanged. Legacy behavior is preserved: when REQUIRE_HIT is unset,
VALIDATE still bypasses cache loading and forces the existing encode-and-compare
path, and the stricter RAM-shape and trailing-byte checks are only active in
REQUIRE_HIT mode. Strict mode also bypasses any pre-existing media batch before
checking the cache, so a stale batch cannot satisfy the required-hit contract. Since the require-hit path returns on every raw chunk cache miss or
decode failure, a request containing multiple chunks cannot encode one chunk
while accepting cache hits for others; each raw chunk must pass its own cached
decode.

## Source-level validation

tools/server/test_featcache_require_hit_source.py contains three source-level
tests. They verify the incompatible/missing-cache guards, ordering of both
missing/decode-failure refusals before mtmd_batch_encode, and RAM/disk
integrity checks.

Executed in the isolated llama worktree:

/home/chao/.venvs/speechrl/bin/python -m pytest -q tools/server/test_featcache_require_hit_source.py
3 passed

At this source-test stage, git diff --check also passed. No build, binary,
service, model, tokenizer, encoder, or runtime request was run. The later
compile qualification is recorded below. Runtime proof still requires a human-owned
build and a raw-input multi-chunk request with complete cache entries, plus
negative cases for missing, malformed, incompatible-VALIDATE, and forced
cached-decode failure.


## Isolated build qualification

The patched source was compiled in the fresh build directory
/home/chao/llama-worktrees/featcache-require-hit/build-qualify, using the
pinned source commit and the existing original build settings. The fixed CUDA
architecture was 120; no GPU autodetection was used. The initial CMake
configuration was:

    /home/chao/.venvs/speechrl/lib/python3.12/site-packages/cmake/data/bin/cmake -S /home/chao/llama-worktrees/featcache-require-hit -B /home/chao/llama-worktrees/featcache-require-hit/build-qualify -G Ninja -DCMAKE_MAKE_PROGRAM=/home/chao/.venvs/speechrl/bin/ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_COMPILER=/usr/bin/cc -DCMAKE_CXX_COMPILER=/usr/bin/c++ -DCMAKE_CUDA_COMPILER=/usr/local/cuda-12.8/bin/nvcc -DCMAKE_CUDA_ARCHITECTURES=120 -DGGML_CUDA=ON -DGGML_CCACHE=ON -DGGML_NATIVE=ON -DLLAMA_BUILD_SERVER=ON -DLLAMA_CURL=OFF

The build was completed with the server target compile and link commands.
The normal Ninja attempt requested no more than four compiler workers. The
CMake UI asset provisioning target could not complete because the
remote-disabled asset package lacked loading.html. For this compile-only
qualification, generated ui.cpp and ui.h from the original build were copied
into the fresh build directory and the UI archive was compiled locally; no
network fetch, model, or service was used.

Toolchain identity:

- GNU C++: c++ (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0
- CUDA compiler: Build cuda_12.8.r12.8/compiler.35583870_0
- CMake: cmake version 4.3.4
- Ninja: 1.13.0.git.kitware.jobserver-pipe-1

The resulting isolated server binary SHA-256 is
33c80bb2eceb29b8e81739cf0d799fe8d5fb754f73f047aba3c34838f06c66c1.
For comparison, the untouched original binary at
/home/chao/llama.cpp-featcache/build/bin/llama-server has SHA-256
d0b42ace8d8e02dc772a0e4a1e1667068b3ad799b1ca4c98c741cf89d58404f2.
The original checkout remained at
04ccc72a2207347ca76161b93fd9d846dd0a8675 and was clean after qualification.
Copied UI source hashes are ui.cpp ceade106f91d25955ed64d5585dd15526c61e2f4e4f4fe5c72c4cb3770550a36 and ui.h 3c53266fec4effa0e1ff54f62459b57bb72279c4656e1f9152175e9a992382f1; the generated libllama-ui.a hash is b69dd37cc170565d9325c9a59d163eb94c16ac8869a974150857667f79a9d5fe. The provenance record hash is 46b60ac7777d6d8fe12bda610fb7cb1307ae4e8a24725408e21b27b88671195d.
The durable command record is at
/home/chao/saea-worktrees/featcache-require-hit-study/docs/readiness/2026-09-09-featcache-require-hit-build-provenance.txt
(SHA-256 46b60ac7777d6d8fe12bda610fb7cb1307ae4e8a24725408e21b27b88671195d). This is a source and compile qualification, not runtime hit/miss proof: no
weights were loaded, no server was started, and no model, tokenizer, encoder,
scorer, or endpoint was contacted.
