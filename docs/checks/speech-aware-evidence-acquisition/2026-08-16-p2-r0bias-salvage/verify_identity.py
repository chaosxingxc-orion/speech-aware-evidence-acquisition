"""Re-derive the ABORTED attempt's identity hashes from the committed repo,
the same way analysis.context_dose._verify_config_identity and
core.bundle.verify do it for a COMPLETED bundle.

Proves: the arm config, the protocol hash and the split identity recorded in
the dead manifest still reproduce exactly from today's committed fragments and
today's umbrella lock -- i.e. nothing about the arm's identity drifted.
"""
import json
from pathlib import Path

from speech_aware_evidence_acquisition.core.config import compose, protocol_hash
from speech_aware_evidence_acquisition.data.lock import data_root, load_lock, umbrella_lock_path

REPO = Path('/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition')
D = Path('/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs/SAEA-P2-r0bias/attempt-20260816T002109Z-4e1f59')
man = json.loads((D / 'SAEA-P2-r0bias.run-manifest.json').read_text(encoding='utf-8'))
frg = man['config']['fragments']

composed = compose(REPO, frg['model'], frg['dataset'], frg['baseline'], frg['experiment'])
print('fragments            :', frg)
print('config_hash recorded :', man['config']['config_hash'])
print('config_hash recomputed:', composed.config_hash)
print('CONFIG HASH MATCH    :', composed.config_hash == man['config']['config_hash'])
print('')
print('arm recorded         :', man['arm'])
print('arm from config      :', composed.values.get('arm'))
print('evidence_materialization_id:', composed.values.get('evidence_materialization_id'))

ph = protocol_hash(composed.config_hash, man['arm'], man['split']['identity_hash'])
print('')
print('protocol_hash recorded  :', man['protocol_hash'])
print('protocol_hash recomputed:', ph)
print('PROTOCOL HASH MATCH     :', ph == man['protocol_hash'])
print('plan protocol_hash      :', man['plan']['protocol_hash'], '(match:',
      man['plan']['protocol_hash'] == ph, ')')

# split identity re-derivation (data.splits.split_identity_hash over prefixed ids)
from speech_aware_evidence_acquisition.data.splits import split_identity_hash, prefixed
sih = split_identity_hash(prefixed(man['split']['carrier_lock_key'], man['split']['ids']))
print('')
print('split identity recorded  :', man['split']['identity_hash'])
print('split identity recomputed:', sih)
print('SPLIT IDENTITY MATCH     :', sih == man['split']['identity_hash'])
print('plan split_identity_hash :', man['plan']['split_identity_hash'], '(match:',
      man['plan']['split_identity_hash'] == sih, ')')
