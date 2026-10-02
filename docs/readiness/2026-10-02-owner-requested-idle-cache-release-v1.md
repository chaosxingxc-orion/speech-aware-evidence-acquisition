# Owner-requested idle memory audit and targeted cache release

The owner asked whether residual tasks consumed the large host memory and authorized releasing unnecessary memory. The audit found no large leftover research process. Windows has 63.43 GiB physical memory. WSL occupied about 29.5 GiB while Linux reported about 27.0 GiB cached file pages, 39.76 GiB available (including reclaimable pages), and 2.24 GiB anonymous pages. The resident llama-server was approximately 2.49 GiB RSS; the next largest Linux processes were about 45 MiB each. Windows Memory Compression was approximately 5.55 GiB, a system-managed component and not a stale experiment to kill. Private committed memory is not physical resident memory and must not be added to working sets.

## Action and measured outcome

Global synchronization stalled in the kernel `super_lock` path before the requested global cache-drop operation. Root requested termination of only the owned diagnostic helper, then used a narrower completed operation: advisory eviction of unused file-cache pages for the exact read-only mapped GGUF file. No file content was read or rewritten by this operation. The GGUF size/inode/mtime were unchanged.

Linux file cache fell from about 27.0 to 9.90 GiB. Windows later reclaimed that headroom: free physical memory increased from 14.39 to 31.18 GiB, while WSL's Windows working set fell to 12.47 GiB. The original service PID, start identity and argument hash were preserved. Its fresh telemetry remained healthy/idle, with four slots, 22,976 MiB GPU memory and unchanged request count 20,749. STOP, queue, status, flight source pins and stale lease hashes remained identical. No trial, generation, tokenizer or scoring contact occurred.

The kernel documents `POSIX_FADV_DONTNEED` as an advisory cache-release request, not a file deletion. Evicted pages may need disk reads later. This is a one-time idle diagnostic, not a routine cache-clearing policy or a change to host memory settings. See [Linux interface semantics](https://man7.org/linux/man-pages/man2/posix_fadvise.2.html) and [global cache-drop limitations](https://docs.kernel.org/admin-guide/sysctl/vm.html#drop-caches).

## Remaining limitations

At 11:13Z the global-sync diagnostic helper PID 310214 remained blocked in kernel disk sleep with 15,744 KiB RSS and termination signals pending. Its original Python command was revalidated before each signal. It had not reached the global cache-drop write, and it cannot proceed to that Python statement after the pending fatal signal takes effect. This small helper is recorded, not represented as a terminated process. Do not spawn more global-sync helpers or restart WSL merely to remove it while the resident service is healthy.

The real earlier startup also retained eight fully materialized runtimes and peaked at about 11.05 GiB RSS. Cache reclamation and that process-lifetime defect are distinct. The tested sequential process guard remains appropriate. The user request to free memory does not approve proposed owner decision 218 or reopen the failed attempt. Exact recovery disposition, fresh source/registration and live admission still precede any new generation. Complete-family READ remains unsigned; all unrelated holds remain.

Exact timestamps, observations, preservation checks and immutable evidence hashes are in [the operational receipt](../receipts/continuation/2026-10-02-owner-requested-idle-cache-release.json).
