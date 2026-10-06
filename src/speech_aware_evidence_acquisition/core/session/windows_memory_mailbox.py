"""Opt-in transport for an explicitly bound Windows-owned memory sampler.

The Windows launcher owns sampler lifetime. WSL publishes one nonce-bound request
per measurement and reuses the existing strict physical-memory validator. Files
are job-private evidence, never cached measurements or authority to run a flight.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import re
import time
from .windows_memory import WindowsMemoryObserver


def _read_bounded(path):
    with path.open('rb') as handle:
        raw=handle.read(4097)
    if len(raw)>4096:
        raise ValueError('oversized mailbox record')
    return json.loads(raw)


def _publish(path, value):
    temporary=path.with_suffix('.tmp')
    with temporary.open('x',encoding='ascii') as handle:
        json.dump(value,handle,ensure_ascii=True);handle.flush();os.fsync(handle.fileno())
    # Link publishes complete bytes atomically and refuses existing evidence.
    os.link(temporary,path)
    temporary.unlink()


class WindowsMemoryMailbox(WindowsMemoryObserver):
    """Require one fresh directory and the launcher's expected session/PID."""

    def __init__(self, directory, *, session, observer_pid, timeout=8.0):
        super().__init__(timeout=timeout)
        if not isinstance(session,str) or re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,127}',session) is None:
            raise ValueError('invalid mailbox session')
        if type(observer_pid) is not int or observer_pid<=0:
            raise ValueError('invalid bound Windows PID')
        self.directory=Path(directory)
        self.session=session
        self._observer_pid=observer_pid
        self._claimed=False

    def _start(self):
        if self._claimed:
            return None
        ready=_read_bounded(self.directory/'ready.json')
        if not isinstance(ready,dict) or ready.get('session')!=self.session or type(ready.get('observer_pid')) is not int or ready['observer_pid']!=self._observer_pid:
            raise ValueError('mailbox readiness differs from launcher binding')
        _publish(self.directory/'client.json',{'session':self.session,'pid':os.getpid()})
        self._claimed=True
        return None

    def _exchange(self, process, request, deadline):
        request=dict(request,session=self.session)
        stem=f"{request['sequence']:08d}"
        _publish(self.directory/f'request-{stem}.json',request)
        response=self.directory/f'response-{stem}.json'
        while not self._closed.is_set():
            if time.monotonic()>=deadline:
                raise TimeoutError('mailbox response deadline')
            if response.exists():
                value=_read_bounded(response)
                if not isinstance(value,dict) or value.get('session')!=self.session:
                    raise ValueError('mailbox session mismatch')
                return value
            self._closed.wait(min(.02,max(0,deadline-time.monotonic())))
        raise OSError('mailbox observer closed')

    def __call__(self):
        value=super().__call__()
        if value.get('host_memory_error') is None:
            value['transport']='windows-owned-mailbox-v1'
        return value

    def close(self):
        self._closed.set()
        if self._claimed:
            try:
                _publish(self.directory/'STOP.json',{'session':self.session})
            except FileExistsError:
                pass
