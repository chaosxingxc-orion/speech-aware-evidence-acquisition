"""Truncation check: do the durable artifacts end on a complete record?"""
import json
import hashlib
from pathlib import Path

D = Path('/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs/SAEA-P2-r0bias/attempt-20260816T002109Z-4e1f59')
R = 'SAEA-P2-r0bias'

for name in (f'{R}.trace.jsonl', f'{R}.outputs.jsonl'):
    b = (D / name).read_bytes()
    print('%-34s bytes=%-9d ends_with_newline=%s' % (name, len(b), b.endswith(b'\n')))
    last = b.rstrip(b'\n').rsplit(b'\n', 1)[-1]
    try:
        obj = json.loads(last)
        print('   last line parses OK; keys=%s' % sorted(obj.keys()))
    except Exception as e:
        print('   LAST LINE MALFORMED: %s' % e)

# trace-manifest covers every trace record and every content hash matches
tm = json.loads((D / f'{R}.trace-manifest.json').read_text(encoding='utf-8'))
recs = [json.loads(l) for l in open(D / f'{R}.trace.jsonl', encoding='utf-8') if l.strip()]
ids = [r['record_id'] for r in recs]
print('')
print('trace records=%d  manifest entries=%d  ids unique=%s  id sets equal=%s'
      % (len(recs), len(tm['records']), len(set(ids)) == len(ids), set(ids) == set(tm['records'])))

# reproduce TraceRecord.content_hash(): sha256 over the compact sorted serialization
from speech_aware_evidence_acquisition.contracts.boundary import TraceRecord
bad = 0
for r in recs:
    tr = TraceRecord(channel=r['channel'], record_id=r['record_id'], payload=r['payload'])
    if tr.content_hash() != tm['records'][r['record_id']]:
        bad += 1
        if bad <= 3:
            print('  HASH MISMATCH', r['record_id'])
print('trace-manifest content-hash mismatches: %d / %d' % (bad, len(recs)))

# final sample end-to-end
last_use = [r for r in recs if r['record_id'] == 'req-0010/use'][0]
last_obs = sorted([r for r in recs if r['channel'] == 'OBS' and r['record_id'].startswith('req-0010-i')],
                  key=lambda r: r['payload']['obs_iteration'])[-1]
head_obs = [r for r in recs if r['record_id'] == 'req-0010/obs'][0]
print('')
print('FINAL SAMPLE 4397829 (req-0010):')
print('  audio_seconds        =', head_obs['payload']['obs_audio_seconds'])
print('  last slice iteration =', last_obs['payload']['obs_iteration'])
print('  last window          = [%.2f, %.2f]' % (last_obs['payload']['obs_window_start_seconds'],
                                                 last_obs['payload']['obs_window_end_seconds']))
print('  obs_final_window     =', last_obs['payload']['obs_final_window'])
print('  obs_saturated/skipped=', last_obs['payload']['obs_saturated'], last_obs['payload']['obs_skipped'])
print('  use_admitted         =', last_use['payload']['use_admitted'])
print('  use_stitched_iters   =', last_use['payload']['use_stitched_iterations'])
stitch = [r for r in recs if r['record_id'] == 'req-0010/response'][0]['payload']
print('  final text words     =', len(stitch['text'].split()))
print('  final text tail      =', repr(stitch['text'][-120:]))
print('  sha256(final text)   =', hashlib.sha256(stitch['text'].encode('utf-8')).hexdigest())
print('  recorded text sha256 =', stitch['response_text_sha256'])
