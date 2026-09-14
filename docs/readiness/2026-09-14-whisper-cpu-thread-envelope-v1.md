# Whisper CPU thread envelope v1

Status: backend implementation and fake-only validation complete. No audio,
checkpoint, model, tokenizer, scorer, service, or GPU contact occurred.

The existing `saea-local-whisper-decode-v1` protocol accepts one new optional
field:

```json
{
  "cpu_workers": 1,
  "cpu_thread_limits": {
    "inference_threads": 6,
    "interop_threads": 1
  }
}
```

When `cpu_thread_limits` is absent, validation and runtime behavior remain
unchanged. An explicitly present value must be the exact mapping above; `null`
is refused. Both values must be positive integers, the device must be CPU, and
`cpu_workers + inference_threads + interop_threads` must be at most eight.
Validation occurs before the audio prefetch object is constructed.

On the first lazy stack load, the backend applies the two limits through
PyTorch before calling `whisper.load_model`, reads both values back, and refuses
an application failure or mismatch. The successful pair is process-global.
Later stack loads and every decode on an already loaded backend verify the
observed PyTorch state without resetting it; a different configured pair or
observed runtime drift is refused. The backend does not modify process
environment variables.

The focused backend and adjacent provider, preparation, and runtime suites use
only fake Whisper, Torch, audio, and model objects. They cover malformed and
over-eight envelopes before eager work, one-time ordered application, setter
failure, post-set mismatch, configured drift, observed drift, and unchanged
legacy behavior.
