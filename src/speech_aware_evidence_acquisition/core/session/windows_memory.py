"""Own one fresh Windows physical-memory observer for a guarded WSL campaign.

Reuse the transport process, never its measurements. Each request is bounded and
bound to a fresh nonce, sequence, timestamp and stable observer identity. Any
failure latches this instance closed; it never reconnects or falls back to VM
memory. The existing campaign guard remains responsible for stopping its worker.
"""

from __future__ import annotations

import json
import math
import os
import secrets
import select
import subprocess
import threading
import time

from .serving import _powershell_executable


SCRIPT = """
$ErrorActionPreference='Stop';
Add-Type -AssemblyName Microsoft.VisualBasic;
$info=New-Object Microsoft.VisualBasic.Devices.ComputerInfo;
while ($true) {
    $pending=[Console]::In.ReadLineAsync();
    if (-not $pending.Wait(15000)) { break };
    $line=$pending.Result;
    if ($null -eq $line -or $line -eq 'STOP') { break };
    $q=ConvertFrom-Json $line;
    $watch=[System.Diagnostics.Stopwatch]::StartNew();
    $free=$info.AvailablePhysicalMemory;
    $total=$info.TotalPhysicalMemory;
    $watch.Stop();
    [Console]::Out.WriteLine(([PSCustomObject]@{
        nonce=$q.nonce; sequence=$q.sequence;
        sample_elapsed_ms=$watch.Elapsed.TotalMilliseconds;
        sampled_at=[DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds();
        available_bytes=$free; total_bytes=$total; observer_pid=$PID
    } | ConvertTo-Json -Compress));
    [Console]::Out.Flush();
}
"""


def _number(value):
    return type(value) in (int, float) and math.isfinite(value)


class WindowsMemoryObserver:
    """Create the observer lazily within the guard's bounded sample operation."""

    def __init__(self, *, popen=subprocess.Popen, executable=None, timeout=8.0):
        if not _number(timeout) or not 0 < timeout <= 8:
            raise ValueError('Windows memory timeout must be in (0, 8] seconds')
        self._popen, self._executable, self._timeout = popen, executable, timeout
        self._state = threading.Lock()
        self._request = threading.Lock()
        self._closed = threading.Event()
        self._process = None
        self._failure = None
        self._diagnostics = {}
        self._sequence = 0
        self._observer_pid = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    @staticmethod
    def _dispose(process):
        # The pipe and Popen handle belong only to this observer. A short STOP
        # permits clean Windows exit; idle EOF/15-second expiry is a backstop.
        if process.poll() is None:
            try:
                os.write(process.stdin.fileno(), b'STOP\n')
            except OSError:
                pass
            try:
                process.wait(timeout=.25)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:
                    process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=1)
        for pipe in (process.stdin, process.stdout):
            pipe.close()

    def close(self):
        self._closed.set()
        with self._state:
            process, self._process = self._process, None
        if process is not None:
            self._dispose(process)

    def _start(self):
        if self._process is not None:
            return self._process
        process = self._popen(
            [self._executable or _powershell_executable(), '-NoProfile',
             '-NonInteractive', '-Command', SCRIPT],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, bufsize=0,
        )
        os.set_blocking(process.stdin.fileno(), False)
        os.set_blocking(process.stdout.fileno(), False)
        with self._state:
            closed = self._closed.is_set()
            if not closed:
                self._process = process
        if closed:
            self._dispose(process)
            raise OSError('observer closed during startup')
        return process

    def _exchange(self, process, request, deadline):
        pending = memoryview((json.dumps(request)+'\n').encode('ascii'))
        response = bytearray()
        while True:
            if self._closed.is_set():
                raise OSError('observer closed')
            remaining = deadline-time.monotonic()
            if remaining <= 0:
                raise TimeoutError('timeout')
            readable, writable, _ = select.select(
                [process.stdout], [process.stdin] if pending else [], [],
                min(remaining, .1),
            )
            if writable:
                pending = pending[os.write(process.stdin.fileno(), pending):]
            if readable:
                chunk = os.read(process.stdout.fileno(), 4097)
                if not chunk:
                    raise OSError('observer EOF')
                response.extend(chunk)
                if len(response) > 4096:
                    self._diagnostics['failure_code'] = 'oversized-response'
                    raise ValueError('oversized observer response')
                if b'\n' in response:
                    line, extra = response.split(b'\n', 1)
                    if extra or pending:
                        self._diagnostics['failure_code'] = 'unsolicited-response'
                        raise ValueError('unsolicited observer response')
                    return json.loads(line)

    def __call__(self):
        with self._request:
            if self._closed.is_set() or self._failure:
                return {'host_free_gb': None,
                        'host_memory_error': self._failure or 'closed',
                        'host_memory_diagnostics': dict(self._diagnostics)}
            started, wall_start = time.monotonic(), time.time()
            self._diagnostics = {'wall_start': wall_start}
            try:
                process = self._start()
                self._sequence += 1
                request = {'nonce': secrets.token_hex(16), 'sequence': self._sequence}
                value = self._exchange(process, request, started+self._timeout)
                finished = time.time()
                self._diagnostics.update(wall_end=finished,
                    roundtrip_seconds=time.monotonic()-started,
                    expected_sequence=self._sequence)
                # Record bounded numeric metadata only. Never persist raw JSON,
                # nonce contents or exception text from the transport.
                if isinstance(value, dict):
                    self._diagnostics.update({k: value[k] for k in
                        ('sequence', 'available_bytes', 'total_bytes', 'observer_pid', 'sample_elapsed_ms')
                        if _number(value.get(k))})
                    if _number(value.get('sampled_at')):
                        self._diagnostics['windows_sampled_at'] = value['sampled_at']/1000
                if not isinstance(value, dict) or any((
                    value.get('nonce') != request['nonce'],
                    type(value.get('sequence')) is not int,
                    value.get('sequence') != self._sequence,
                    not all(_number(value.get(k)) for k in
                            ('sampled_at','available_bytes','total_bytes','sample_elapsed_ms')),
                    type(value.get('observer_pid')) is not int,
                )):
                    self._diagnostics['failure_code'] = 'response-identity-or-type'
                    raise ValueError('invalid observer response')
                sampled = value['sampled_at']/1000
                # A matching unpredictable request nonce establishes causality:
                # this owned script samples physical memory only after reading
                # that request. Receipt before the WSL monotonic deadline bounds
                # its age by the roundtrip. Windows Stopwatch independently
                # bounds read duration without comparing independent wallclocks.
                # One millisecond covers elapsed-time serialization precision;
                # it never extends the WSL deadline. Wall time is diagnostic only.
                checks = (
                    ('request-causal-freshness', 0 <= value['sample_elapsed_ms']
                     <= min(self._timeout, self._diagnostics['roundtrip_seconds'])*1000+1),
                    ('roundtrip-deadline', time.monotonic()-started <= self._timeout),
                    ('physical-memory-range', 0 <= value['available_bytes'] <= value['total_bytes']
                     and value['total_bytes'] > 0),
                    ('observer-process-identity', value['observer_pid'] > 0
                     and self._observer_pid in (None, value['observer_pid'])),
                )
                for code, valid in checks:
                    if not valid:
                        self._diagnostics['failure_code'] = code
                        raise ValueError('stale or inconsistent observer response')
                self._observer_pid = value['observer_pid']
                return {'host_free_gb': value['available_bytes']/1024**3,
                        'host_total_gb': value['total_bytes']/1024**3,
                        'host_memory_error': None, 'sampled_at': sampled,
                        'observer_pid': self._observer_pid,
                        'sequence': self._sequence,
                        'transport': 'persistent-windows-physical-memory-v1',
                        'freshness': 'request-causal-monotonic-v1',
                        'sample_elapsed_ms': value['sample_elapsed_ms']}
            except (OSError, ValueError, TypeError) as error:
                self._failure = 'timeout' if isinstance(error, TimeoutError) else type(error).__name__
                self._diagnostics.setdefault('failure_code', 'invalid-json' if isinstance(error, json.JSONDecodeError)
                                             else 'transport-'+self._failure)
                self._diagnostics.setdefault('roundtrip_seconds', time.monotonic()-started)
                self._diagnostics.setdefault('wall_end', time.time())
                return {'host_free_gb': None, 'host_memory_error': self._failure,
                        'host_memory_diagnostics': dict(self._diagnostics)}
