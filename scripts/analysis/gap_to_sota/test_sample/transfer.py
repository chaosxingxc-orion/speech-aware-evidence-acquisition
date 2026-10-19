"""Transfer table DEV / Fold B / TEST (raw and post-stratified) from the aggregate JSONs. Aggregates only."""
import json
t = json.load(open('gap-numbers-test.json'))['populations']['TEST']
d = json.load(open('gap-numbers-devfb.json'))['populations']
P = {'DEV': d['DEV']['ext_raw'], 'FB': d['FOLDB']['ext_raw'], 'TEST': t['ext_raw'], 'TEST_PS': t['ext_poststrat']}
keys = list(P['TEST']['point'])
rows = []
for k in keys:
    dv, fb = P['DEV']['point'][k], P['FB']['point'][k]
    lo, hi = min(dv, fb), max(dv, fb)
    row = {'key': k}
    for n in P:
        row[n] = P[n]['point'][k]; row[n + '_ci'] = P[n]['ci95'][k]
    for n in ('TEST', 'TEST_PS'):
        c = P[n]['ci95'][k]
        row[n + '_flag'] = 'ABOVE' if c[0] > hi else ('BELOW' if c[1] < lo else '')
    rows.append(row)
tiers = {"LauraGPT": (73.45, 87.87), "SFT-Qwen2-Audio-7B": (76.75, 88.13), "UniverSLU-14": (79.5, 90.3)}
ps = P['TEST_PS']['point']; ci = P['TEST_PS']['ci95']
base = (ps['slu'], ps['intent'])
shares = {}
oracles = {'o_i_slu_central_gain': 'slu', 'o_ii_slu_gain': 'slu', 'o_iii_slu_gain': 'slu', 'o_iv_slu_gain': 'slu', 'o_iii_iv_slu_gain': 'slu', 'o_v_slu_gain': 'slu',
           'o_i_intent_gain': 'intent', 'o_ii_intent_gain': 'intent', 'o_iib_intent_gain': 'intent', 'o_v_intent_gain': 'intent', 'o_vb_intent_gain': 'intent'}
for o, m in oracles.items():
    shares[o] = {'gain': ps[o], 'ci95': ci[o]}
    for tn, (s, i) in tiers.items():
        gap = (s - base[0]) if m == 'slu' else (i - base[1])
        shares[o][tn] = {'gap': gap, 'share_pct': 100.0 * ps[o] / gap, 'share_ci_pct': [100.0 * x / gap for x in ci[o]]}
json.dump({'schema': 'saea-slurp-v30-gap-transfer-v1', 'transfer': rows, 'test_gap_shares_poststrat': shares, 'tiers': tiers,
           'note': 'flag = TEST CI95 lies wholly outside [min(DEV,FB), max(DEV,FB)]; raw = roster mixture; TEST_PS = post-stratified natural mixture'},
          open('test-gap-transfer.json', 'w'), indent=1)
f = lambda v: f"{v:.2f}"
for r in rows:
    print(f"{r['key']:32s} DEV {f(r['DEV'])} [{f(r['DEV_ci'][0])},{f(r['DEV_ci'][1])}] FB {f(r['FB'])} [{f(r['FB_ci'][0])},{f(r['FB_ci'][1])}] TEST {f(r['TEST'])} [{f(r['TEST_ci'][0])},{f(r['TEST_ci'][1])}] {r['TEST_flag']} | PS {f(r['TEST_PS'])} [{f(r['TEST_PS_ci'][0])},{f(r['TEST_PS_ci'][1])}] {r['TEST_PS_flag']}")
for o, v in shares.items():
    print(o, f(v['gain']), [f(x) for x in v['ci95']], {tn: (f(x['gap']), round(x['share_pct']), [round(y) for y in x['share_ci_pct']]) for tn, x in v.items() if tn in tiers})
