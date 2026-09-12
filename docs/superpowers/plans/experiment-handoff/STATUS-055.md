# STATUS-055: Local speech tool readiness and live campaign

Snapshot UTC: 2026-09-12T06:18:33.402793+00:00

Native Audio2Tool attempt metadata:

{
  "DIRECT": [
    {
      "state": "FINALIZED",
      "calls": 4000
    }
  ],
  "STAGE-CONTROL": [
    {
      "state": "OPENED",
      "calls": 6234
    }
  ],
  "KNOWLEDGE": []
}

Keep campaign exec session 71462, resident owner session 2098 and monitor session 88815. Do not restart or edit frozen cbc53ac0. The all-three-sealed semantic result gate still applies. Source/scoring artifact reads remain pending until that gate.

Read docs/readiness/2026-09-12-local-speech-tool-readiness.json for hash-bound local acquisition receipts. Silero ONNX and MMS_FA CPU load-only checks passed. FFmpeg/ffprobe launchers work. CMUdict is source-only. Sortformer payloads/runtime are verified but not activated. WhisperX and pyannote runtime code snapshots are source-only alternatives.

Whisper large-v3 download continues in exec session 30436 from the official source, with a preserved contiguous partial file. Do not restart or replace it. Current partial receipt is /home/chao/speech-tools/whisper-vad/receipts/acquisition-partial-v1.json (SHA256 9eade5dee99b311786503139658d5d08a6ead197b7e1c50f0b062e1c217922a4). The exact total is 3,087,371,615 bytes; the snapshot recorded 803,328,000 bytes. Four-way range transfer did not improve throughput, so one resumed transfer remains active. Final expected SHA256 is e5b1a55b89c1367dacf97e3e19bfd829a01529dbfdeefa8caeb59b3f1b81dadb. Root granted Euclid the exclusive large CPU load slot after final hash success, only if fresh host-free memory is at least 14GiB. No forwards or GPU loads. Popper's MMS process has exited.

pyannote Community-1 payload download returned HTTP401 under current Hugging Face access. Public model/runtime source is pinned, but no payload was downloaded. The owner can enable access on its official model page; use existing Sortformer for the planned path in the meantime. Do not request or expose access tokens in conversation.

The shared generic saved-score analysis and owner tool plan were locally fast-forward merged into master at 200d60c50f21d4bf0ab632c6687bff247d7c46c3. No remote push is claimed. Analysis recipe bindings remain pending all seals. 92 related tests, Ruff and engineering-base checks passed. Tool readiness does not mean shared live OBS integration or task effectiveness.

Next: monitor existing download/campaign, write acquisition completion successors, analyze complete first score artifacts after the gate, then register the SLURP matched speech-evidence experiment described in docs/readiness/2026-09-12-speech-tool-system-plan.md. Keep the goal active.
