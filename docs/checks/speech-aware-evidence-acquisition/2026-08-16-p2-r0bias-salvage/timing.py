import json, time, resource
from pathlib import Path
from speech_aware_evidence_acquisition.core.scorers import score_asr_outputs
from speech_aware_evidence_acquisition.data.lock import data_root, load_lock, umbrella_lock_path
from speech_aware_evidence_acquisition.data.references import reference_tokens
from speech_aware_evidence_acquisition.scoring import tokens_v1

D=Path('/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs/SAEA-P2-r0bias/attempt-20260816T002109Z-4e1f59')
S=Path('/mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/95b8e5b0-424d-494b-9d7b-4f101bc186be/scratchpad')
root=data_root(); lock=load_lock(umbrella_lock_path())
rows=[json.loads(l) for l in open(D/'SAEA-P2-r0bias.outputs.jsonl',encoding='utf-8') if l.strip()]
tot=0
print(f"{'sample':10}{'reflen':>8}{'hyplen':>8}{'cells_M':>10}")
for r in rows:
    ref=tokens_v1(' '.join(reference_tokens(lock,root,r['carrier_lock_key'],r['sample_id'])))
    hyp=tokens_v1(r['text'])
    cells=len(ref)*len(hyp); tot+=cells
    print(f"{r['sample_id']:10}{len(ref):8d}{len(hyp):8d}{cells/1e6:10.1f}")
print('TOTAL cells (M):', tot/1e6)
# time the smallest one through the real registered scorer
small=min(rows,key=lambda r:len(r['text'].split()))
p=S/'one.outputs.jsonl'; p.write_text(json.dumps(small,ensure_ascii=False)+'\n',encoding='utf-8')
t=time.time(); res=score_asr_outputs(p,lock,root); dt=time.time()-t
print('smallest sample',small['sample_id'],'took %.1fs'%dt, 'wer=%.5f'%res['per_sample'][0]['wer'],
      'peakRSS_MB=%.0f'%(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024))
cells=len(tokens_v1(' '.join(reference_tokens(lock,root,small['carrier_lock_key'],small['sample_id']))))*len(tokens_v1(small['text']))
print('rate: %.2f Mcells/s -> full 10-sample asr-wer ETA %.1f min'%(cells/1e6/dt, tot/1e6/(cells/1e6/dt)/60))
