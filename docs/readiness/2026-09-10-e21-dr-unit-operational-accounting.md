# E21 DR unit-parent operational accounting

The first current packet-based DR parent is sealed and finalized. Its two complete official score jobs and both saved window-statistics views are also complete. This note records operational cost only; all-four-delivery quality comparisons remain pending.

The source-bound operational receipt is `analysis/SAEA-E21-DR-PACKETS-UNIT-GENERATION-V2/operational-summary-v1.json` under the data root, SHA256 `ba0a0bc871a046287f4a20150c413d185926c375608cb4a026765d5bd0d06e74`. It uses the existing shared serving-monitor summarizer at commit `e0472138`. The original parent, score receipts and monitor bytes remain unchanged. This read adds no model, encoder, tokenizer or official scorer contacts.

| Quantity | Observed value | Meaning |
| --- | ---: | --- |
| Recorded parent start to seal | 139.452 min | The registered parent interval, not exclusive GPU computation |
| Utilization-weighted GPU cost | 1.16919 GPU h | External 10-second monitor integral; original cap is 1.2 |
| Mean sampled GPU utilization | 50.3425% | Arithmetic sample mean from the shared summarizer |
| Classified parked time | 10.662 min, 7.6551% | All slots idle and sampled GPU utilization below 5% |
| Classified active time | 128.616 min | Complement of parked time within sampled coverage |
| Mean / peak sampled power | 87.02 / 104.82 W | Observations during the fixed parent interval |
| Completed model contacts | 1,593 | Durable attempt count, covering 44 calls |
| Completion throughput | 53.890 tokens/s | 450,904 completion tokens divided by the recorded parent interval |
| Contact throughput | 11.423/min | Durable contacts divided by that same interval |
| Summed request latency | 213.463 min | Concurrent request latencies overlap; this is not wall time |
| Root handoff gap | 6.524 min | Recorded context-recovery and seal-verification delay |
| Two full official score jobs | 61.368 min total | Sequential CPU jobs, both overlapping self generation |

The monitor covers 8,356.707 seconds of the 8,367.091-second parent interval; 10.385 boundary seconds are outside its first-to-last sample coverage. Its request counter reports 1,176 transitions, which is a sampling lower bound. Use the 1,593 durable contacts for throughput. The shared classifier's active time is not kernel time and must not be substituted for the utilization integral.

The recorded shared-service start precedes the parent budget interval by 19.454 minutes. This interval contains shared setup and other registered work; it is not an isolated model-load measurement. Separate pure model-load and data-wait durations are unavailable in the bound phase records. Do not infer either from parked time. The original manifest correctly retains inline GPU sampling as `NOT_AVAILABLE`; the external monitor receipt supplies separate evidence.

Self generation began before unit scores or a scientific verdict existed. The 391.456-second handoff therefore remains an operational delay, not a scientific-decision wait. Preserve it against the one-minute handoff target. The current comparison retains its registered serving geometry and prefetch behavior.

Reproduce the monitor portion in WSL with the existing shared entry:

```bash
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=/home/chao/saea-worktrees/dr-delivery-settlement/src \
/home/chao/.venvs/speechrl/bin/python \
/home/chao/saea-worktrees/dr-delivery-settlement/scripts/serving_monitor.py summarize \
  --session-id serving-e21-dr-packets-np6-v2 \
  --data-root /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data \
  --from 1789048400.0 --to 1789056767.091251
```

Before reproducing, verify the monitor prefix binding in the operational receipt. Later appends from self generation are outside the fixed interval. The complete-system cost report must retain the unavailable phase measurements explicitly until a subsequently registered run supplies them.
