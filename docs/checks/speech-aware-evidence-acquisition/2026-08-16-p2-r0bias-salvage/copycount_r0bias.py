"""PRE-LOCALIZE echo / copy-count measurement for SAEA-P2-r0bias.

Honours the D7E guard-2 aperture note (docs/exposure-ledger.md SAEA-D7E):
"guard-2 aperture is zero at the localized layer -- echo metrics MUST be
extracted pre-localize". Every measurement below is taken on
`replay_replay_text` (the RAW replay transcript, before _localize_replay_words
subsets it), never on `replay_localized_words`.

Reuses the study's OWN code, not a reimplementation:
  reproduction.replay_loop._reference_echo_reject       (Guard 2 predicate)
  reproduction.replay_loop._unsupported_reference_word  (Guard 3 predicate)
  core.retrieval.normalize_term                         (the frozen normalizer)
The delivered `{reference}` slot is reconstructed EXACTLY as replay_loop.py
builds it at lines ~1623-1637:
  reference_text = " ".join([t for t,_ in delta_terms] + [exemplar labels])
which in the trace is replay_candidates[].text + replay_exemplars_attached[].label.
"""
import json
import collections
from pathlib import Path

# core/__init__ performs the policy+scorer registration chain; importing
# reproduction.replay_loop first hits the core.policies <-> replay_loop cycle.
from speech_aware_evidence_acquisition import core as _core  # noqa: F401
from speech_aware_evidence_acquisition.reproduction.replay_loop import (
    _reference_echo_reject,
    _unsupported_reference_word,
)
from speech_aware_evidence_acquisition.core.retrieval import normalize_term

D = Path('/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs/SAEA-P2-r0bias/attempt-20260816T002109Z-4e1f59')
S = Path('/mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/95b8e5b0-424d-494b-9d7b-4f101bc186be/scratchpad')

wins_deriv = []
for p in sorted(D.glob('SAEA-P2-r0bias.replay-derivation.*.json')):
    d = json.loads(p.read_text(encoding='utf-8'))
    assert d['schema'] == 'saea-replay-derivation-v1'
    wins_deriv.extend(d['replay_windows'])
wins_trace = [
    r['payload']
    for r in (json.loads(l) for l in open(D / 'SAEA-P2-r0bias.trace.jsonl', encoding='utf-8') if l.strip())
    if r['channel'] == 'REPLAY'
]


def key(w):
    # the no-candidates skip path leaves window_iteration/span_index None
    return (w['replay_sample_id'],
            -1 if w['replay_window_iteration'] is None else w['replay_window_iteration'],
            -1 if w['replay_span_index'] is None else w['replay_span_index'],
            w.get('replay_slice_iteration') or -1)


same = sorted(wins_deriv, key=key) == sorted(wins_trace, key=key)
print('replay windows: derivation=%d trace=%d identical=%s' % (len(wins_deriv), len(wins_trace), same))
wins = sorted(wins_trace, key=key)


def delivered_reference(w):
    parts = [c['text'] for c in (w.get('replay_candidates') or [])]
    for pair in (w.get('replay_exemplars_attached') or []):
        lab = pair.get('label')
        if isinstance(lab, str) and lab:
            parts.append(lab)
    return ' '.join(parts)


def contains_subseq(hay, needle):
    n, m = len(hay), len(needle)
    if m == 0 or m > n:
        return 0
    return sum(1 for i in range(n - m + 1) if hay[i:i + m] == needle)


rows = []
for w in wins:
    ref = delivered_reference(w)
    pre = w.get('replay_replay_text')
    loc = ' '.join(w.get('replay_localized_words') or [])
    pass1 = w.get('replay_pass1_text') or ''
    base = dict(
        sample=w['replay_sample_id'], win=w['replay_window_iteration'], span=w['replay_span_index'],
        ref=ref, pre=pre, pass1=pass1, localized=loc,
        accepted=w['replay_accepted'], reason=w['replay_reject_reason'],
    )
    if pre is None:
        base.update(echo_pre=None, echo_post=None, copies_pre=0, copies_pass1=0,
                    novel_copy=False, guard3_pre=None)
        rows.append(base)
        continue
    ref_t = normalize_term(ref).split()
    pre_t = normalize_term(pre).split()
    p1_t = normalize_term(pass1).split()
    copies_pre = contains_subseq(pre_t, ref_t) if ref_t else 0
    copies_p1 = contains_subseq(p1_t, ref_t) if ref_t else 0
    base.update(
        echo_pre=_reference_echo_reject(pre, ref),
        echo_post=_reference_echo_reject(loc, ref),
        copies_pre=copies_pre,
        copies_pass1=copies_p1,
        novel_copy=bool(copies_pre > 0 and copies_p1 == 0),
        guard3_pre=_unsupported_reference_word(pre.split(), ref, pass1.split()),
    )
    rows.append(base)

n = len(rows)
called = [r for r in rows if r['pre'] is not None]
print('')
print('replay windows total=%d  with a model call=%d  skipped(no-candidates)=%d' % (n, len(called), n - len(called)))
print('accepted splices            : %d' % sum(1 for r in rows if r['accepted']))
print('PRE-localize strict echo    : %d / %d' % (sum(1 for r in called if r['echo_pre']), len(called)))
print('POST-localize strict echo   : %d / %d   (the in-run guard-2 aperture)'
      % (sum(1 for r in called if r['echo_post']), len(called)))
print('PRE-localize COPY COUNT (delivered reference occurring inside the raw replay text):')
print('   total occurrences        : %d' % sum(r['copies_pre'] for r in called))
print('   windows with >=1 copy    : %d / %d' % (sum(1 for r in called if r['copies_pre'] > 0), len(called)))
print('   NOVEL copies (term absent from the pass-1 span it replaces): %d / %d'
      % (sum(1 for r in called if r['novel_copy']), len(called)))
print('   guard-3 unsupported-reference word present pre-localize   : %d / %d'
      % (sum(1 for r in called if r['guard3_pre']), len(called)))
print('')
print('reject-reason histogram: %s' % dict(collections.Counter(r['reason'] for r in rows)))

print('')
print('=== per-sample ===')
bys = collections.defaultdict(list)
for r in rows:
    bys[r['sample']].append(r)
print('%-10s%6s%7s%5s%8s%9s%8s%7s' % ('sample', 'wins', 'called', 'acc', 'echoPre', 'echoPost', 'copies', 'novel'))
for s in sorted(bys):
    g = bys[s]
    c = [r for r in g if r['pre'] is not None]
    print('%-10s%6d%7d%5d%8d%9d%8d%7d' % (
        s, len(g), len(c), sum(1 for r in g if r['accepted']),
        sum(1 for r in c if r['echo_pre']), sum(1 for r in c if r['echo_post']),
        sum(r['copies_pre'] for r in c), sum(1 for r in c if r['novel_copy'])))

print('')
print('=== ACCEPTED splices (the only ones that changed the transcript) ===')
for r in rows:
    if r['accepted']:
        keep = ('sample', 'win', 'span', 'ref', 'pass1', 'pre', 'localized', 'copies_pre', 'novel_copy')
        print(json.dumps({k: r[k] for k in keep}, ensure_ascii=False, indent=1))

print('')
print('=== every PRE-localize copy window ===')
for r in called:
    if r['copies_pre'] > 0:
        print('  %s w%ss%s ref=%r pass1=%r pre=%r copies=%d novel=%s accepted=%s reason=%s' % (
            r['sample'], r['win'], r['span'], r['ref'], r['pass1'], r['pre'][:160],
            r['copies_pre'], r['novel_copy'], r['accepted'], r['reason']))

(S / 'r0bias.copycount.json').write_text(json.dumps(rows, indent=1, ensure_ascii=False, sort_keys=True), encoding='utf-8')
print('')
print('wrote %s' % (S / 'r0bias.copycount.json'))
