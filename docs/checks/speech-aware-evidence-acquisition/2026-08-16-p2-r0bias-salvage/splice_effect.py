"""Did the 3 accepted REPLAY splices actually reach the final transcript?
Plus the HER substrate under the ONLY in-repo HER criterion
(docs/exposure-ledger.md:247 -- 'accepted replays INSERTED the delivered reference').
"""
import json
from pathlib import Path

D = Path('/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs/SAEA-P2-r0bias/attempt-20260816T002109Z-4e1f59')
S = Path('/mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/95b8e5b0-424d-494b-9d7b-4f101bc186be/scratchpad')

from speech_aware_evidence_acquisition import core as _core  # noqa: F401
from speech_aware_evidence_acquisition.core.retrieval import normalize_term

rows = json.loads((S / 'r0bias.copycount.json').read_text(encoding='utf-8'))
outs = {json.loads(l)['sample_id']: json.loads(l)['text']
        for l in open(D / 'SAEA-P2-r0bias.outputs.jsonl', encoding='utf-8') if l.strip()}

print('=== accepted splices: reached the final transcript? / HER-specimen criterion ===')
for r in rows:
    if not r['accepted']:
        continue
    final = outs[r['sample']]
    loc, p1, ref = r['localized'], r['pass1'], r['ref']
    ref_n = normalize_term(ref)
    loc_n = normalize_term(loc)
    print('')
    print('  sample=%s window=%s span=%s' % (r['sample'], r['win'], r['span']))
    print('    delivered reference : %r' % ref)
    print('    pass-1 span text    : %r' % p1)
    print('    spliced-in text     : %r' % loc)
    print('    spliced text present in final transcript : %s' % (loc in final))
    print('    pass-1 text still present in final       : %s' % (p1 in final))
    print('    HER specimen (spliced text INSERTED the delivered reference): %s'
          % (ref_n in loc_n.split() or ref_n in loc_n))

n_acc = sum(1 for r in rows if r['accepted'])
n_her = 0
for r in rows:
    if r['accepted']:
        ref_n, loc_n = normalize_term(r['ref']), normalize_term(r['localized'])
        if ref_n and (ref_n in loc_n):
            n_her += 1
print('')
print('ACCEPTED EDITS (HER denominator)        : %d' % n_acc)
print('reference-inserting edits (HER numerator, exposure-ledger criterion): %d' % n_her)
print('=> HER under that criterion             : %d/%d = %.4f' % (n_her, n_acc, n_her / n_acc))
print('')
print('total final-transcript words across the ten calls: %d'
      % sum(len(t.split()) for t in outs.values()))
