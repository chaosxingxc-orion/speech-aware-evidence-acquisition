"""Keep unavailable Windows observations diagnosable without weakening custody."""
import json
import subprocess
from types import SimpleNamespace
import pytest
from speech_aware_evidence_acquisition.core.session.serving import read_host_memory
from speech_aware_evidence_acquisition.core.flight.process_guard import _sample, MemoryPolicy

@pytest.mark.parametrize("outcome,reason", [
    (subprocess.TimeoutExpired("observer",8), "timeout"),
    (subprocess.SubprocessError("private failure"), "subprocess-error"),
    (SimpleNamespace(returncode=True,stdout="{}"), "exit-nonzero"),
    (FileNotFoundError("observer"), "os-error:FileNotFoundError"),
    (SimpleNamespace(returncode=7,stdout="private diagnostic",stderr="private diagnostic"), "exit-nonzero"),
    (SimpleNamespace(returncode=0,stdout="malformed private output"), "invalid-json"),
    (SimpleNamespace(returncode=0,stdout="[]"), "not-object"),
    (SimpleNamespace(returncode=0,stdout='{"FreePhysicalMemory":null}'), "invalid-free-memory"),
    (SimpleNamespace(returncode=0,stdout='{"FreePhysicalMemory":-1}'), "invalid-free-memory"),
    (SimpleNamespace(returncode=0,stdout='{"FreePhysicalMemory":true}'), "invalid-free-memory"),
    (SimpleNamespace(returncode=0,stdout='{"FreePhysicalMemory":NaN}'), "invalid-free-memory"),
    (SimpleNamespace(returncode=0,stdout='{"FreePhysicalMemory":Infinity}'), "invalid-free-memory"),
])
def test_observation_failure_is_categorized_and_not_raw_output(tmp_path,outcome,reason):
    calls=[]
    def run(*args,**kwargs):
        calls.append((args,kwargs))
        if isinstance(outcome,Exception):raise outcome
        return outcome
    value=read_host_memory(run=run,meminfo_path=tmp_path/'missing')
    assert value['host_memory_error']==reason
    assert value['host_free_gb'] is None
    assert len(calls)==1 and calls[0][1]['timeout']==8
    assert 'private' not in json.dumps(value)
    observed=_sample(lambda:value,MemoryPolicy(start_gib=12.5,floor_gib=8))
    assert observed['reason']=='windows-reading-unavailable'
    assert observed['reader_error']==reason

def test_current_windows_reading_preserves_units_and_has_no_error(tmp_path):
    result=SimpleNamespace(returncode=0,stdout=json.dumps({'TotalVisibleMemorySize':64*1024**2,'FreePhysicalMemory':25*1024**2,'VmmemWorkingSet64':30*1024**3}))
    value=read_host_memory(run=lambda *a,**k:result,meminfo_path=tmp_path/'missing')
    assert value['host_free_gb']==25 and value['host_total_gb']==64 and value['vmmem_ws_gb']==30
    assert value['host_memory_error'] is None
    assert _sample(lambda:value,MemoryPolicy(start_gib=12.5,floor_gib=8))['reason'] is None

def test_vm_free_memory_never_substitutes_for_missing_windows_value(tmp_path):
    p=tmp_path/'meminfo';p.write_text('MemTotal: 67108864 kB\nMemAvailable: 62914560 kB\n')
    result=SimpleNamespace(returncode=0,stdout='{"FreePhysicalMemory":null}')
    value=read_host_memory(run=lambda *a,**k:result,meminfo_path=p)
    assert value['vm_available_gb']==60 and value['host_free_gb'] is None
    assert _sample(lambda:value,MemoryPolicy(start_gib=12.5,floor_gib=8))['reason']=='windows-reading-unavailable'
