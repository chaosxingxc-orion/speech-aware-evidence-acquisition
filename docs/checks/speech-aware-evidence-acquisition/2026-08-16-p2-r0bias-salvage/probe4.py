import json, collections, hashlib, re, os
D='/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs/SAEA-P2-r0bias/attempt-20260816T002109Z-4e1f59'
R='SAEA-P2-r0bias'
recs=[json.loads(l) for l in open(f'{D}/{R}.trace.jsonl',encoding='utf-8')if l.strip()]
man=json.load(open(f'{D}/{R}.run-manifest.json',encoding='utf-8'))

# integrity: trace bytes vs manifest recorded sha
h=hashlib.sha256(open(f'{D}/{R}.trace.jsonl','rb').read()).hexdigest()
print('trace sha256 match:', h==man['raw_trace']['sha256'], h)
h2=hashlib.sha256(open(f'{D}/{R}.session-receipt.json','rb').read()).hexdigest()
print('session-receipt sha match:', h2==man['session_receipt']['sha256'])

bych=collections.defaultdict(list)
for r in recs: bych[r['channel']].append(r)

# split ids order
split_ids=man['split']['ids']
print('split ids', split_ids)

# per-sample OBS slice accounting
obs_slices=collections.defaultdict(list); obs_head={}
for r in bych['OBS']:
    rid=r['record_id']; p=r['payload']
    m=re.match(r'^(req-\d+)(?:-i(\d+))?/obs$', rid)
    assert m, rid
    req=m.group(1)
    if m.group(2) is None: obs_head[req]=p
    else: obs_slices[req].append((int(m.group(2)),p))
print()
print(f"{'req':9}{'sample':10}{'audio_s':>10}{'slices':>7}{'maxi':>6}{'lastEnd':>10}{'cover%':>8}{'final':>6}{'sat':>4}{'skip':>5}{'retry':>6}{'stitchIt':>9}")
use_by={re.match(r'^(req-\d+)/use$',r['record_id']).group(1):r['payload'] for r in bych['USE']}
tot_slices=0
for i,req in enumerate(sorted(obs_slices)):
    sl=sorted(obs_slices[req]); tot_slices+=len(sl)
    head=obs_head[req]; aud=head['obs_audio_seconds']
    last=sl[-1][1]
    finals=[x for _,x in sl if x['obs_final_window']]
    sat=sum(1 for _,x in sl if x['obs_saturated']); sk=sum(1 for _,x in sl if x['obs_skipped'])
    rt=sum(1 for _,x in sl if x['obs_retry_of'] is not None)
    end=last['obs_window_end_seconds']
    print(f"{req:9}{head['obs_speech_ref'].split('/')[1]:10}{aud:10.1f}{len(sl):7d}{sl[-1][0]:6d}{end:10.1f}{100*end/aud:8.2f}{len(finals):6d}{sat:4d}{sk:5d}{rt:6d}{use_by[req]['use_stitched_iterations']:9d}")
print('total obs slice records', tot_slices, ' sum stitched iterations', sum(p['use_stitched_iterations'] for p in use_by.values()))

# request/response id accounting
def kinds(ch,suf):
    c=collections.Counter()
    for r in bych[ch]:
        rid=r['record_id']
        if re.match(r'^req-\d+-i\d+/'+suf+'$',rid): c['obs-slice']+=1
        elif re.match(r'^req-\d+-replay\d+/'+suf+'$',rid): c['replay']+=1
        elif re.match(r'^req-\d+/'+suf+'$',rid): c['stitch']+=1
        else: c['OTHER:'+rid]+=1
    return c
print('MODEL_REQUEST', dict(kinds('MODEL_REQUEST','request')))
print('MODEL_RESPONSE', dict(kinds('MODEL_RESPONSE','response')))
print('COST', dict(kinds('COST','cost')))
print('cost calls sum', sum(r['payload']['calls'] for r in bych['COST']),
      'audio sum', round(sum(r['payload']['audio_seconds'] for r in bych['COST']),4),
      '| manifest', man['cost']['calls_used'], round(man['cost']['audio_seconds_used'],4))

# stitched final text vs outputs.jsonl
outs={json.loads(l)['request_id']:json.loads(l) for l in open(f'{D}/{R}.outputs.jsonl',encoding='utf-8') if l.strip()}
print()
ok=True
for r in bych['MODEL_RESPONSE']:
    rid=r['record_id']; m=re.match(r'^(req-\d+)/response$',rid)
    if not m: continue
    req=m.group(1); p=r['payload']
    o=outs[req]
    tsha=hashlib.sha256(p['text'].encode('utf-8')).hexdigest()
    same_txt = p['text']==o['text']
    a = tsha==p['response_text_sha256']; b = p['response_text_sha256']==o['response_text_sha256']
    c = use_by[req]['use_response_sha256']==o['response_sha256']
    d = len(p.get('stitched_from_response_sha256s',[]))
    print(f"{req} trace_text==outputs_text:{same_txt} sha(text)==recorded:{a} outputs_sha_match:{b} USE_sha_match:{c} stitched_from_n:{d} words:{len(p['text'].split())}")
    ok &= same_txt and a and b and c
print('ALL STITCH CONSISTENT:', ok)
