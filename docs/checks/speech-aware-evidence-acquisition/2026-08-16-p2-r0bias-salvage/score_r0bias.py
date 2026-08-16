"""OFFLINE SALVAGE SCORING for SAEA-P2-r0bias (ABORTED-manifest attempt).

Reuses the study's OWN frozen scoring code paths verbatim:
  core.scorers.score_asr_outputs        (registered scorer "asr-wer")
  core.scorers.score_entity_wer_outputs (registered scorer "entity-wer")
Both are called with the SAME (outputs_path, lock, root) signature the in-run
score_bundle path and the offline analysis.entity_wer_offline CLI use, so the
numbers are bit-identical to what a COMPLETED manifest would have carried.
Writes ONLY to the scratchpad. Never touches the repo or the attempt dir.
"""
import json, sys
from pathlib import Path

from speech_aware_evidence_acquisition.core.scorers import (
    score_asr_outputs, score_entity_wer_outputs, ENTITY_WER_ADAPTER_VERSION,
)
from speech_aware_evidence_acquisition.data.lock import data_root, load_lock, umbrella_lock_path
from speech_aware_evidence_acquisition.scoring import SCORING_STACK_VERSION

D = Path('/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs/SAEA-P2-r0bias/attempt-20260816T002109Z-4e1f59')
OUT = D / 'SAEA-P2-r0bias.outputs.jsonl'
SCRATCH = Path('/mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/95b8e5b0-424d-494b-9d7b-4f101bc186be/scratchpad')

root = data_root()
lock = load_lock(umbrella_lock_path())
print('scoring stack version:', SCORING_STACK_VERSION)
print('entity-wer adapter   :', ENTITY_WER_ADAPTER_VERSION)
print('data root            :', root)

asr = score_asr_outputs(OUT, lock, root)
ent = score_entity_wer_outputs(OUT, lock, root)

print('\n=== asr-wer (score_asr_outputs) ===')
print(f"{'sample':10}{'wer':>9}{'hits':>8}{'sub':>7}{'del':>7}{'ins':>7}{'reflen':>8}")
for e in asr['per_sample']:
    reflen = len(e['ref_hit_mask'])
    print(f"{e['sample_id']:10}{e['wer']:9.5f}{e['hits']:8d}{e['substitutions']:7d}{e['deletions']:7d}{e['insertions']:7d}{reflen:8d}")
print('AGGREGATE (macro mean_wer):', asr['aggregate'])
tot_err = sum(e['substitutions']+e['deletions']+e['insertions'] for e in asr['per_sample'])
tot_ref = sum(len(e['ref_hit_mask']) for e in asr['per_sample'])
print(f'micro/corpus WER = {tot_err}/{tot_ref} = {tot_err/tot_ref:.6f}')

print('\n=== entity-wer (score_entity_wer_outputs) ===')
print(f"{'sample':10}{'expected':>9}{'correct':>8}{'ent_wer':>9}{'recall':>9}")
for e in ent['per_sample']:
    print(f"{e['sample_id']:10}{e['expected_total']:9d}{e['correct']:8d}{e['entity_wer']:9.5f}{e['recall']:9.5f}")
agg = ent['aggregate']
print('AGGREGATE:', json.dumps({k:v for k,v in agg.items() if k!='by_entity_type'}, indent=1, sort_keys=True))
print('ENTITY LEDGER expected_total (corpus) =', agg['expected_total'])
print('by_entity_type:')
for t, s in agg['by_entity_type'].items():
    print(f"  {t:22} expected={s['expected_total']:5d} correct={s['correct']:5d} entity_wer={s['entity_wer']:.5f}")

(SCRATCH/'r0bias.asr-wer.json').write_text(json.dumps(asr, indent=1, sort_keys=True), encoding='utf-8')
(SCRATCH/'r0bias.entity-wer.json').write_text(json.dumps(ent, indent=1, sort_keys=True), encoding='utf-8')
print('\nwrote', SCRATCH/'r0bias.asr-wer.json', 'and r0bias.entity-wer.json')
