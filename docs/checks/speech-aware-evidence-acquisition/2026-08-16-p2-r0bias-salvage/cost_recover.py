"""Recover the cost aggregates the ABORTED manifest marked NOT_AVAILABLE.

The manifest could not run core.driver.run_experiment's own cost aggregate,
but every per-call COST trace record survived, so the token/latency totals are
straight sums over the COST channel.
"""
import json
import collections
from pathlib import Path

D = Path('/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs/SAEA-P2-r0bias/attempt-20260816T002109Z-4e1f59')
recs = [json.loads(l) for l in open(D / 'SAEA-P2-r0bias.trace.jsonl', encoding='utf-8') if l.strip()]
cost = [r['payload'] for r in recs if r['channel'] == 'COST']
man = json.loads((D / 'SAEA-P2-r0bias.run-manifest.json').read_text(encoding='utf-8'))

tot = collections.Counter()
for p in cost:
    for k in ('calls', 'prompt_tokens', 'completion_tokens'):
        tot[k] += p[k]
aud = sum(p['audio_seconds'] for p in cost)
lat = sum(p['latency_seconds'] for p in cost)

print('RECOVERED from the COST trace channel (%d records):' % len(cost))
print('  calls_used             = %d      (manifest: %s)' % (tot['calls'], man['cost']['calls_used']))
print('  audio_seconds_used     = %.4f (manifest: %.4f)' % (aud, man['cost']['audio_seconds_used']))
print('  prompt_tokens_total    = %d      (manifest: %s)' % (tot['prompt_tokens'], man['cost']['prompt_tokens_total']))
print('  completion_tokens_total= %d      (manifest: %s)' % (tot['completion_tokens'], man['cost']['completion_tokens_total']))
print('  latency_seconds_total  = %.2f   (manifest: %s)' % (lat, man['cost']['latency_seconds_total']))
print('  audio hours            = %.3f' % (aud / 3600.0))
print('')
print('  NOT recoverable from the trace (never emitted per-call): gpu_seconds, peak_vram_mib,')
print('  cpu_seconds, gate_setup_seconds, supplied/admitted_evidence_bytes totals, saturated/skipped')
print('  slice ID lists (the last two are derivable from the OBS channel: obs_saturated/obs_skipped).')

sat = [r['record_id'] for r in recs if r['channel'] == 'OBS' and r['payload'].get('obs_saturated')]
skip = [r['record_id'] for r in recs if r['channel'] == 'OBS' and r['payload'].get('obs_skipped')]
print('')
print('  derived saturated_slice_count = %d %s' % (len(sat), sat))
print('  derived skipped_slice_count   = %d %s' % (len(skip), skip))
supply = [r['payload']['supply_content_bytes'] for r in recs if r['channel'] == 'SUPPLY']
print('  derived supplied_evidence_bytes (SUPPLY channel sum) = %d over %d samples' % (sum(supply), len(supply)))
