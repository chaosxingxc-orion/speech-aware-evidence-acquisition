"""Exercise fresh host observations without spawning Windows from WSL."""
import json
import threading
import time
from pathlib import Path
import pytest
from speech_aware_evidence_acquisition.core.session.windows_memory_mailbox import WindowsMemoryMailbox


def server(root, change=None, count=2):
    root.mkdir()
    (root/'ready.json').write_text(json.dumps({'session':'test-session', 'observer_pid':1234}))
    def loop():
        for n in range(1,count+1):
            request=root/f'request-{n:08d}.json'
            until=time.monotonic()+2
            while not request.exists():
                if (root/'STOP.json').exists() or time.monotonic()>until:return
                time.sleep(.002)
            q=json.loads(request.read_text())
            v=dict(q, observer_pid=1234, sampled_at=time.time()*1000, sample_elapsed_ms=.01,
                   available_bytes=(20+n)*1024**3,total_bytes=64*1024**3)
            if change:change(v)
            response=root/f'response-{n:08d}.json'
            tmp=response.with_suffix('.tmp');tmp.write_text(json.dumps(v));tmp.rename(response)
    t=threading.Thread(target=loop);t.start()
    return t


def test_fresh_roundtrips_keep_identity_and_preserve_evidence(tmp_path):
    root=tmp_path/'mail';t=server(root)
    with WindowsMemoryMailbox(root,session='test-session',observer_pid=1234,timeout=.5) as reader:
        a,b=reader(),reader()
        assert [a['host_free_gb'],b['host_free_gb']]==[21,22]
        assert a['observer_pid']==b['observer_pid']==1234
        assert b['sequence']==2 and b['transport']=='windows-owned-mailbox-v1'
    t.join()
    assert reader()['host_free_gb'] is None
    assert json.loads((root/'STOP.json').read_text())=={'session':'test-session'}
    assert len(list(root.glob('request-*.json')))==2


@pytest.mark.parametrize('change',[
    lambda v:v.update(session='other'), lambda v:v.update(nonce='replay'),
    lambda v:v.update(sequence=0),lambda v:v.update(observer_pid=4567),
    lambda v:v.update(available_bytes=-1),lambda v:v.update(sample_elapsed_ms=9000),
    lambda v:v.update(total_bytes=True),lambda v:v.update(sampled_at=float('nan')),
])
def test_invalid_measurements_latch_without_retry(tmp_path,change):
    root=tmp_path/'mail';t=server(root,change,count=1)
    with WindowsMemoryMailbox(root,session='test-session',observer_pid=1234,timeout=.5) as reader:
        assert reader()['host_free_gb'] is None
        assert reader()['host_free_gb'] is None
    t.join();assert not (root/'request-00000002.json').exists()


def test_timeout_never_uses_old_value(tmp_path):
    root=tmp_path/'mail';t=server(root,count=1)
    with WindowsMemoryMailbox(root,session='test-session',observer_pid=1234,timeout=.1) as reader:
        assert reader()['host_free_gb']==21
        start=time.monotonic();bad=reader()
        assert bad['host_memory_error']=='timeout' and time.monotonic()-start<.4
        assert reader()['host_free_gb'] is None
    t.join()


@pytest.mark.parametrize('kind',['identity','occupied','oversize','bad-json','missing'])
def test_refuses_bad_endpoint_or_response(tmp_path,kind):
    root=tmp_path/'mail';root.mkdir()
    (root/'ready.json').write_text(json.dumps({'session':'test-session','observer_pid':1234}))
    if kind=='identity':(root/'ready.json').write_text('{}')
    if kind=='occupied':(root/'request-00000001.json').write_text('preserved')
    if kind=='missing':(root/'ready.json').unlink()
    if kind in ('oversize','bad-json'):
        (root/'response-00000001.json').write_text('x'*5000 if kind=='oversize' else 'invalid')
    with WindowsMemoryMailbox(root,session='test-session',observer_pid=1234,timeout=.1) as reader:
        assert reader()['host_free_gb'] is None
    if kind=='occupied':assert (root/'request-00000001.json').read_text()=='preserved'


def test_explicit_close_interrupts_wait(tmp_path):
    root=tmp_path/'mail';root.mkdir()
    (root/'ready.json').write_text(json.dumps({'session':'test-session','observer_pid':1234}))
    reader=WindowsMemoryMailbox(root,session='test-session',observer_pid=1234)
    result=[];t=threading.Thread(target=lambda:result.append(reader()));t.start()
    time.sleep(.04);reader.close();t.join(timeout=1)
    assert not t.is_alive() and result[0]['host_free_gb'] is None


@pytest.mark.parametrize('session,pid',[('',1234),('../bad',1234),('ok',True),('ok',0)])
def test_rejects_ambiguous_binding(tmp_path,session,pid):
    with pytest.raises(ValueError):WindowsMemoryMailbox(tmp_path,session=session,observer_pid=pid)


def test_second_client_cannot_attach_or_stop_first(tmp_path):
    root=tmp_path/'mail';t=server(root,count=1)
    with WindowsMemoryMailbox(root,session='test-session',observer_pid=1234,timeout=.5) as first:
        assert first()['host_free_gb']==21
        with WindowsMemoryMailbox(root,session='test-session',observer_pid=1234,timeout=.1) as second:
            assert second()['host_free_gb'] is None
        assert not (root/'STOP.json').exists()
    first.close()
    t.join()
