"""Bounded observer-only diagnosis never retries, changes services or contacts models."""
import importlib.util
import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('memory_probe', ROOT/'scripts/checks/windows_memory_observer_probe.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


@pytest.mark.parametrize('fail_at', [None, 1])
def test_configured_probe_records_and_closes_one_observer(tmp_path, fail_at):
    config = {'schema':'saea-memory-observer-probe-v1','sample_count':3,'interval_seconds':5.,'timeout_seconds':8.}
    state = {'reads':0,'closed':0,'spawned':0}
    class Observer:
        def __init__(self, **kwargs):
            assert kwargs == {'timeout':8.};state['spawned'] += 1
        def __enter__(self): return self
        def __exit__(self,*args): state['closed'] += 1
        def __call__(self):
            i=state['reads'];state['reads'] += 1
            return {'host_free_gb':None if i == fail_at else 20.,'host_memory_error':'ValueError' if i == fail_at else None}
    sleeps=[]
    result=probe.run_probe(config,tmp_path/'proof',observer_factory=Observer,sleep=sleeps.append)
    assert result['status'] == ('completed' if fail_at is None else 'observation-failed')
    assert state == {'reads':3 if fail_at is None else 2,'closed':1,'spawned':1}
    assert sleeps == [5.]*(state['reads']-1)
    assert len((tmp_path/'proof/samples.jsonl').read_text().splitlines()) == state['reads']
    assert result['model_contacts'] == result['scorer_contacts'] == 0
    with pytest.raises(FileExistsError):probe.run_probe(config,tmp_path/'proof',observer_factory=Observer)


@pytest.mark.parametrize('field,value', [('sample_count',0),('sample_count',True),('interval_seconds',0),('interval_seconds',float('nan')),('timeout_seconds',9),('schema','wrong')])
def test_invalid_probe_config_prevents_process_and_output(tmp_path, field, value):
    config={'schema':'saea-memory-observer-probe-v1','sample_count':3,'interval_seconds':5.,'timeout_seconds':8.}
    config[field]=value
    with pytest.raises(ValueError):probe.run_probe(config,tmp_path/'proof',observer_factory=lambda **kw:pytest.fail('spawned'))
    assert not (tmp_path/'proof').exists()
