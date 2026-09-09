import hashlib
import json
from pathlib import Path

from speech_aware_evidence_acquisition.core.config import compose
from speech_aware_evidence_acquisition.core.flight.campaign import load_campaign_cells


REPO = Path(__file__).resolve().parents[2]
EXPERIMENT = 'e21-loop-shared-two-plan-v1'


def _read(relpath):
    return json.loads((REPO / relpath).read_text(encoding='utf-8'))


def test_held_loop_successor_composes_four_cells_and_pins_current_sources():
    document = _read(f'configs/experiment/{EXPERIMENT}.json')
    cells = load_campaign_cells(REPO, EXPERIMENT)
    assert len(cells) == 4
    assert all(cell.document['readiness']['state'] == 'held' for cell in cells)
    assert document['population']['fixed_90s_windows_one_pass'] == 1593
    assert document['population']['contacted_windows_one_pass'] == 600
    assert document['fit_execution_plan']['planned_endpoint_contacts_per_fit'] == 601
    assert document['comparators']['kc_e1f']['status'].startswith('scientific replica complete')
    assert next(guard for guard in document['decision']['guards'] if guard.startswith('over-generation')).endswith('<= +0.022178.')
    assert 'percentage points' in next(guard for guard in document['decision']['guards'] if guard.startswith('over-generation'))

    for cell in cells:
        composed = compose(
            REPO,
            model=cell.document['model_fragment'],
            dataset=cell.document['dataset_fragment'],
            baseline=cell.document['baseline_fragment'],
            experiment=EXPERIMENT,
        )
        assert composed.values['policy'] == 'obs-repair-loop-ojw'
        assert composed.values['obs_controller_program'] == 'phase-direct-only-v1'

    for old_name, new_name in (
        ('e21-loop-1-relisten-repair', 'e21-loop-1-relisten-repair-ojw'),
        ('e21-loop-1c-random-flag-twin', 'e21-loop-1c-random-flag-twin-ojw'),
    ):
        old = _read(f'configs/baseline/{old_name}.json')
        new = _read(f'configs/baseline/{new_name}.json')
        changed = {key for key in set(old) | set(new) if old.get(key) != new.get(key)}
        assert changed == {'policy', 'obs_controller_program', 'ojw_workflow_timeout_seconds'}
        assert new['policy'] == 'obs-repair-loop-ojw'
        assert new['obs_controller_program'] == 'phase-direct-only-v1'
        assert new['ojw_workflow_timeout_seconds'] == 21600

    for pin_name, pin in document['source_pins'].items():
        path = REPO / pin['repo_relpath']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == pin['sha256'], pin_name
