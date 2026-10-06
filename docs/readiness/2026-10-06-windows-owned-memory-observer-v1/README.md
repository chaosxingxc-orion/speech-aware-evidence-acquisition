# Windows-owned physical-memory observation

Status: model-free leased-envelope qualification passed. Actual capacity remains stopped.

The original Windows-launched WSL campaign could complete a stable memory wait,
then fail an eight-second pipe observation in its leased child before any model
contact. Reusing the pipe observer did not repair that actual launch. Preserve
both failures. The lower-level pipe failure cause remains unestablished.

## Opt-in change

Start `scripts/flights/batch/windows_memory_mailbox.ps1` directly under the
Windows job owner. Bind a new private mailbox directory, session identifier,
and the owned process handle/PID. Inject `WindowsMemoryMailbox` into the existing
startup wait and process guard. Their default transport and all existing flights
remain unchanged. Never treat an arbitrary existing mailbox as a fresh session.

Each WSL request contains an unpredictable nonce and increasing sequence. The
Windows sampler measures physical available/total memory only after that request,
then atomically publishes its response. The shared validator requires the exact
nonce, sequence, bound PID and session, valid physical range, bounded Windows
measurement duration and receipt within the WSL monotonic deadline. Files persist
as evidence; no measurement is reused. Failure latches without fallback/reconnect.
A second client cannot attach. Client STOP closes only its claimed sampler; the
Windows wrapper owns handle-based cleanup and an idle deadline provides a backstop.

Keep20GiB startup,8GiB running,three startup samples ten seconds apart and the
original eight-second observation deadline. Preserve the original600-second
startup wait in any actual registration; model-free fixtures used60 seconds.
Do not lower thresholds, flush caches, restart WSL or change host settings.

## Evidence and limits

See ../../receipts/continuation/2026-10-06-update4-windows-mailbox-envelope-qualified.json.
The181 related unit tests pass, with100percent statement coverage of the new
Python transport. Two Windows-owned scheduled-task proofs cover System32 and
Linux launch directories, real shared lease handoff/kernel custody under private
fixture roots, a nested child, actual startup wait and running guard. All14 fresh
measurements passed; both harmless workers and samplers exited normally. Runtime
and resident-session factories were synthetic and contacted no service.

A separately registered sampler-loss proof stopped only its harmless private
worker group with exit125 and retained the fixture lease. The actual failed
campaign lease and frozen94190872 worker remain byte-identical. The first proof's
outer PowerShell exit-code capture defect is preserved: inner components passed,
but the outer receipt had null exit codes. A separate successor captures owned
process handles before waiting and passes both cases. Do not erase this distinction.

## Next boundary

Register a fresh, source-pinned actual capacity entry and its exact observer
lifecycle; do not resume either failed launch or silently reuse its registration.
Revalidate all member identities, service epoch, sources, supplies, contacts,
STOP and lease custody before any tokenizer contact. Preserve one-shot semantics
and record the root disposition. Only a passed capacity family admits structural
engineering, and only later exact full-family qualification admits quality reads.
Do not claim that model-free transport proof is actual capacity or business gain.

The learning priority remains official quality/reliable completion, then support,
review detection/false alarms/repair/damage with uncertainty, then latency/cost.
No changes to templates, knowledge, sampling or scientific acceptance rules occur here.
