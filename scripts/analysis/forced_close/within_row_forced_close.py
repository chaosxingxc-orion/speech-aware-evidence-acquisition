"""Model-free: the forced close as a within-row treatment, across two same-form flights of the Solver lock arm (budget-3072)
on the same Fold B roster: R2b (2026-10-18) and R2 rec2 (2026-10-20). Reads sealed traces + the official per-row columns only."""
import json, base64, os, random, statistics as st, collections
from pathlib import Path
D = Path(os.environ.get('SPEECHRL_DATA_DIR', '/home/chao/saea-data/speechrl-data'))
MSG = "Considering the limited time by the user, I have to give the solution based on the thinking directly now."
RUNS = {
 'R2b': (D/'runs/SAEA-SLURP-STAGE3-NXT-R2B-SOLVER-BUDGET-FOLD-B-V1/attempt-slurp-native-stage3-nxt-r2b-solver-budget-fold-b-generation-v1',
         D/'analysis/SAEA-SLURP-NXT-R2B-SOLVER-BUDGET-FOLD-B-READ-V1/columns/arm-budget-3072-slurp-slu-official-train-scores.json'),
 'R2rec2': (D/'runs/SAEA-SLURP-STAGE3-NXT-R2-THINKING-BUDGET-FOLD-B-V1/attempt-slurp-native-stage3-nxt-r2-thinking-budget-fold-b-generation-rec2-v1',
         D/'analysis/SAEA-SLURP-NXT-R2-THINKING-BUDGET-FOLD-B-READ-V1/columns/arm-budget-3072-slurp-slu-official-train-scores.json'),
}
ARM = 'budget-3072'


def load(run):
    att, col = RUNS[run]
    base = next(att.glob('*.outputs.jsonl'))
    cmap = {}
    supply = {}
    with base.open() as f:
        for line in f:
            r = json.loads(line)
            sid = r['sample_id']
            for b in (((r.get('native_episode_receipt') or {}).get('perception_branches') or {}).get('branches') or []):
                if b.get('branch_id') == ARM:
                    if b.get('contact_id'):
                        cmap[b['contact_id']] = (sid, 'perception')
                    if b.get('solver_contact_id'):
                        cmap[b['solver_contact_id']] = (sid, 'solver')
    agent = {}
    cost = {}
    wire = {}
    with next(att.glob('*.trace.jsonl')).open('rb') as f:
        for raw in f:
            head = raw[:40]
            if b'"USE"' not in head and b'"COST"' not in head and b'"MODEL_WIRE_RESPONSE"' not in head and b'"SUPPLY"' not in head:
                continue
            rec = json.loads(raw)
            ch = rec['channel']
            key = rec['record_id'].split('/', 1)[0]
            p = rec['payload'] or {}
            if ch == 'USE' and 'use_agent_contact_id' in p:
                agent[key] = p['use_agent_contact_id']
            elif ch == 'COST':
                cost[key] = p
            elif ch == 'MODEL_WIRE_RESPONSE':
                w = json.loads(base64.b64decode(p['response_b64']))
                msg = (w.get('choices') or [{}])[0].get('message') or {}
                rc = msg.get('reasoning_content') or ''
                wire[key] = {'forced': rc.rstrip().endswith(MSG.strip()), 'content_len': len(msg.get('content') or '')}
            elif ch == 'SUPPLY':
                supply[key] = len(p.get('supply_final_visible_value_ids') or [])
    rows = {}
    for key, c in cost.items():
        a = agent.get(key)
        if a not in cmap:
            continue
        sid, node = cmap[a]
        if node != 'solver':
            continue
        w = wire.get(key, {})
        rows[sid] = {'forced': bool(c.get('forced_close')), 'ctok': c.get('completion_tokens'), 'ptok': c.get('prompt_tokens'),
                     'lat': c.get('latency_seconds'), 'supply': supply.get(sid)}
    sc = json.load(open(col))
    ps = sc['per_sample'] if isinstance(sc, dict) and 'per_sample' in sc else sc['slurp-slu-official-train']['per_sample']
    for s in ps:
        sid = s['sample_id']
        if sid in rows:
            rows[sid].update({'tp': s['slu_f1_word_tp'], 'fp': s['slu_f1_word_fp'], 'fn': s['slu_f1_word_fn'], 'f1': s['slu_f1_f1'], 'intent': s['scenario_action_exact']})
    return {k: v for k, v in rows.items() if 'tp' in v}


def f1(rs):
    tp = sum(r['tp'] for r in rs); fp = sum(r['fp'] for r in rs); fn = sum(r['fn'] for r in rs)
    return 100 * 2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) else float('nan')


def acc(rs):
    return 100 * sum(r['intent'] for r in rs) / len(rs) if rs else float('nan')


def share(rs, pred):
    sel = [r for r in rs if pred(r)]
    return f"{100 * sum(1 for r in sel if r['forced']) / max(1, len(sel)):.0f} % (n={len(sel)})"


def summarize(name, rs):
    fo = [r for r in rs if r['forced']]
    na = [r for r in rs if not r['forced']]
    print(f"[{name}] rows {len(rs)} forced {len(fo)} ({100 * len(fo) / len(rs):.1f} %)")
    for lab, g in (('forced', fo), ('natural', na)):
        eg = [r for r in g if r['tp'] + r['fn'] == 0]
        ff = sum(1 for r in eg if r['fp'] > 0)
        print(f"   {lab:8s} n={len(g):4d} SLU-F1 {f1(g):6.2f} intent {acc(g):6.2f} FP/row {sum(r['fp'] for r in g) / len(g):.3f} "
              f"FN/row {sum(r['fn'] for r in g) / len(g):.3f} ctok {st.mean(r['ctok'] for r in g):6.0f} ptok {st.mean(r['ptok'] for r in g):6.0f} "
              f"supply {st.mean(r['supply'] or 0 for r in g):5.1f} s/contact {st.mean(r['lat'] for r in g):5.1f} | empty-gold n={len(eg)} "
              f"false-fill {100 * ff / len(eg) if eg else 0:.1f} %")
    print("   forced share by supplied items:", ", ".join(f"{lo}-{hi}: " + share(rs, lambda r, lo=lo, hi=hi: lo <= (r['supply'] or 0) < hi)
                                                        for lo, hi in [(0, 20), (20, 30), (30, 40), (40, 999)]))
    print("   forced share by Solver prompt tokens:", ", ".join(f"{lo}-{hi}: " + share(rs, lambda r, lo=lo, hi=hi: lo <= r['ptok'] < hi)
                                                             for lo, hi in [(0, 6000), (6000, 8000), (8000, 10000), (10000, 99999)]))


A = load('R2b')
B = load('R2rec2')
summarize('R2b lock arm', list(A.values()))
summarize('R2 rec2 lock arm', list(B.values()))
common = sorted(set(A) & set(B))
print(f"\ncommon rows {len(common)}")
grp = collections.defaultdict(list)
for s in common:
    grp[(A[s]['forced'], B[s]['forced'])].append(s)
for k, v in sorted(grp.items()):
    print(f"  forced(R2b,rec2)={k}: {len(v)}")
for lab, k in (('forced-both', (True, True)), ('natural-both', (False, False))):
    rs = [A[s] for s in grp[k]] + [B[s] for s in grp[k]]
    print(f"  {lab:13s} SLU-F1 {f1(rs):6.2f} intent {acc(rs):6.2f} supply {st.mean(r['supply'] or 0 for r in rs):.1f} ptok {st.mean(r['ptok'] for r in rs):.0f}")
disc = [(A[s], B[s]) for s in grp[(True, False)]] + [(B[s], A[s]) for s in grp[(False, True)]]
n = len(disc)
print(f"\nDISCORDANT rows {n}: within-row delta (forced decode minus natural decode of the same row)")
d = {k: sum(f[k] - nn[k] for f, nn in disc) for k in ('tp', 'fp', 'fn', 'intent')}
print("  sums:", {k: round(v, 2) for k, v in d.items()}, " per row:", {k: round(v / n, 3) for k, v in d.items()})
fo = [f for f, _ in disc]
na = [nn for _, nn in disc]
print(f"  pooled SLU-F1 forced decodes {f1(fo):.2f} vs natural decodes {f1(na):.2f} (delta {f1(fo) - f1(na):+.2f}); intent {acc(fo):.2f} vs {acc(na):.2f}")
random.seed(20261024)
boots = []
bi = []
for _ in range(4000):
    smp = [disc[random.randrange(n)] for _ in range(n)]
    boots.append(f1([f for f, _ in smp]) - f1([nn for _, nn in smp]))
    bi.append(acc([f for f, _ in smp]) - acc([nn for _, nn in smp]))
boots.sort()
bi.sort()
print(f"  bootstrap CI95 SLU-F1 delta [{boots[100]:+.2f}, {boots[3899]:+.2f}]; intent delta [{bi[100]:+.2f}, {bi[3899]:+.2f}]")
better = sum(1 for f, nn in disc if f['f1'] > nn['f1'])
worse = sum(1 for f, nn in disc if f['f1'] < nn['f1'])
print(f"  rows where the forced decode scores higher {better}, lower {worse}, tie {n - better - worse}")
ib = sum(1 for f, nn in disc if f['intent'] > nn['intent'])
iw = sum(1 for f, nn in disc if f['intent'] < nn['intent'])
print(f"  intent: forced right/natural wrong {ib}; forced wrong/natural right {iw}")
eg = [(f, nn) for f, nn in disc if f['tp'] + f['fn'] == 0]
print(f"  empty-gold discordant rows {len(eg)}: false-fill forced {sum(1 for f, _ in eg if f['fp'] > 0)} vs natural {sum(1 for _, nn in eg if nn['fp'] > 0)}")
print(f"  completion tokens: forced {st.mean(f['ctok'] for f in fo):.0f} vs natural {st.mean(nn['ctok'] for nn in na):.0f}; "
      f"s/contact {st.mean(f['lat'] for f in fo):.1f} vs {st.mean(nn['lat'] for nn in na):.1f}")
# whole-column bound: if every forced row in each flight scored like a natural decode (apply the discordant per-row deltas)
for name, R in (('R2b', A), ('R2rec2', B)):
    rs = list(R.values())
    nf = sum(1 for r in rs if r['forced'])
    tp = sum(r['tp'] for r in rs) - d['tp'] / n * nf
    fp = sum(r['fp'] for r in rs) - d['fp'] / n * nf
    fn = sum(r['fn'] for r in rs) - d['fn'] / n * nf
    print(f"  {name}: column SLU-F1 {f1(rs):.2f} -> {100 * 2 * tp / (2 * tp + fp + fn):.2f} if the forced-close effect were removed from all {nf} forced rows")
nat = sorted(r['ctok'] for r in list(A.values()) + list(B.values()) if not r['forced'])
print(f"\nnatural-close completion tokens (both flights, n={len(nat)}): p50 {nat[len(nat) // 2]} p75 {nat[int(.75 * len(nat))]} "
      f"p90 {nat[int(.9 * len(nat))]} p95 {nat[int(.95 * len(nat))]} max {nat[-1]}")
json.dump({'common': len(common), 'groups': {str(k): len(v) for k, v in grp.items()}, 'discordant_delta_sums': d, 'discordant_n': n,
           'slu_delta': f1(fo) - f1(na), 'slu_ci': [boots[100], boots[3899]], 'intent_delta': acc(fo) - acc(na), 'intent_ci': [bi[100], bi[3899]]},
          open(os.environ.get('FORCED_CLOSE_OUT', 'forced-close-within-row.json'), 'w'), indent=1)
