"""Coverage for the offline-guard leak fix.

Background (the defect this closes): ``analysis.dev100_reviewer_audit.
arm_offline_guard()`` monkey-patches ``socket.socket.connect``,
``socket.socket.connect_ex`` and ``socket.create_connection`` process-
globally, to make a model-free row's "zero network contacts" claim
something the process itself enforces. Before this fix it never restored
those three attributes. Many model-free analysis ``main()`` functions call
it; when a unit test executed one of those ``main()``s in-process, the
patch outlived that one test and every LATER test in the same pytest
session whose fixture opened a real loopback socket (a stub server, a
transport test's ``socket.create_connection``, ...) died with the guard's
own ``AuditError`` -- a cross-test leak, not a defect in whichever test
happened to run last.

This module proves, directly and without any model, network, tokenizer or
scorer contact:

1. ``arm_offline_guard()`` + ``_ConnectAttempts.disarm()`` restores the
   EXACT original callables (identity, not merely "some callable"), and
   ``disarm()`` is idempotent.
2. ``disarm()`` does not weaken what the NEXT ``arm_offline_guard()`` call
   refuses -- production semantics (a main() that arms and never disarms
   still refuses every later connection in that process) are unchanged.
3. ``disarmed_offline_guard()`` (the context-manager form) disarms on both
   a normal exit and an exception, while the guard genuinely refuses
   connections for the duration of its body.
4. The ``tests/conftest.py`` autouse fixture's own snapshot/restore halves
   (``_snapshot_socket_attributes`` / ``_restore_socket_attributes``, the
   exact functions ``_restore_socket_attributes_after_every_test`` drives)
   restore socket state after a body that arms the guard and never
   disarms it -- the historical leak pattern, reproduced here directly
   rather than via a nested pytest invocation.
5. A real loopback TCP server, connected to via ``socket.create_connection``
   after such a restore, actually connects -- the concrete end-to-end
   proof, not just an attribute-identity check.

Every socket opened here is a 127.0.0.1 ephemeral-port loopback listener
this test starts itself; nothing dials out.
"""

from __future__ import annotations

import importlib.util
import socket
import threading
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.analysis.dev100_reviewer_audit import (
    AuditError,
    _ConnectAttempts,
    arm_offline_guard,
    disarmed_offline_guard,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
_ROOT_CONFTEST_PATH = REPO_ROOT / "tests" / "conftest.py"


def _load_root_conftest():
    """Load ``tests/conftest.py`` as its own module object (same pattern
    ``_module()`` helpers elsewhere in this test suite use for scripts),
    so this test can call its snapshot/restore helpers and inspect its
    autouse fixture directly -- distinct from pytest's own already-
    collected ``conftest`` module, hence the different module name."""

    spec = importlib.util.spec_from_file_location(
        "saea_root_conftest_under_test", _ROOT_CONFTEST_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ROOT_CONFTEST = _load_root_conftest()


def _loopback_listener() -> tuple[socket.socket, int]:
    """Bind a real TCP listener on 127.0.0.1 at an OS-assigned (collision-
    free) port, accept exactly one connection in a background thread, and
    return the listening socket plus the port it was handed."""

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    port = server.getsockname()[1]

    def _accept_once() -> None:
        try:
            connection, _ = server.accept()
            connection.close()
        except OSError:
            pass

    threading.Thread(target=_accept_once, daemon=True).start()
    return server, port


# ---------------------------------------------------------------------------
# 1: arm + disarm restores the exact originals, idempotently
# ---------------------------------------------------------------------------


def test_disarm_restores_the_exact_original_callables() -> None:
    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex
    original_create_connection = socket.create_connection

    guard = arm_offline_guard()
    assert socket.socket.connect is not original_connect
    assert socket.socket.connect_ex is not original_connect_ex
    assert socket.create_connection is not original_create_connection

    guard.disarm()
    assert socket.socket.connect is original_connect
    assert socket.socket.connect_ex is original_connect_ex
    assert socket.create_connection is original_create_connection


def test_disarm_is_idempotent() -> None:
    original_connect = socket.socket.connect

    guard = arm_offline_guard()
    guard.disarm()
    guard.disarm()  # second call must be a harmless no-op

    assert socket.socket.connect is original_connect


def test_disarm_on_a_never_armed_guard_is_a_harmless_noop() -> None:
    original_connect = socket.socket.connect

    never_armed = _ConnectAttempts()
    never_armed.disarm()

    assert socket.socket.connect is original_connect


# ---------------------------------------------------------------------------
# 2: disarming does not weaken the NEXT arm
# ---------------------------------------------------------------------------


def test_a_fresh_arm_after_a_disarm_still_refuses_and_counts() -> None:
    first_guard = arm_offline_guard()
    first_guard.disarm()

    second_guard = arm_offline_guard()
    try:
        with pytest.raises(AuditError, match="offline guard"):
            socket.create_connection(("127.0.0.1", 1))
        assert second_guard.count == 1
        assert first_guard.count == 0
    finally:
        second_guard.disarm()


# ---------------------------------------------------------------------------
# 3: disarmed_offline_guard() context-manager form
# ---------------------------------------------------------------------------


def test_disarmed_offline_guard_refuses_during_the_body_and_restores_after() -> None:
    original_connect = socket.socket.connect
    original_create_connection = socket.create_connection

    with disarmed_offline_guard() as attempts:
        assert socket.socket.connect is not original_connect
        with pytest.raises(AuditError, match="offline guard"):
            socket.create_connection(("127.0.0.1", 1))
        assert attempts.count == 1

    assert socket.socket.connect is original_connect
    assert socket.create_connection is original_create_connection


def test_disarmed_offline_guard_restores_even_on_exception() -> None:
    original_connect = socket.socket.connect

    class _Marker(Exception):
        pass

    with pytest.raises(_Marker):
        with disarmed_offline_guard():
            raise _Marker("boom")

    assert socket.socket.connect is original_connect


def test_armed_guard_refuses_socket_connect_method_not_only_create_connection() -> None:
    with disarmed_offline_guard() as attempts:
        probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            with pytest.raises(AuditError, match="offline guard"):
                probe.connect(("127.0.0.1", 1))
        finally:
            probe.close()
        assert attempts.count == 1
        assert attempts.targets == ["('127.0.0.1', 1)"]


# ---------------------------------------------------------------------------
# 4: the conftest.py autouse fixture closes the leak
# ---------------------------------------------------------------------------


def test_conftest_snapshot_restore_helpers_close_a_leaking_arm() -> None:
    """Drive the exact functions ``_restore_socket_attributes_after_every_
    test`` calls, around a body that arms the guard and (deliberately,
    simulating the historical bug) never disarms it -- proving the
    conftest fixture's own logic closes the leak, not merely
    ``_ConnectAttempts.disarm()`` in isolation."""

    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex
    original_create_connection = socket.create_connection

    snapshot = ROOT_CONFTEST._snapshot_socket_attributes()
    assert snapshot == (original_connect, original_connect_ex, original_create_connection)

    # The "leaking test body": arms the guard and never disarms -- exactly
    # a model-free main()'s own intended, permanent-for-this-process
    # semantics, which is precisely what leaked into later tests before
    # this fix.
    leaked_guard = arm_offline_guard()
    assert socket.socket.connect is not original_connect
    assert leaked_guard.count == 0

    # The fixture's teardown half, run exactly as it runs after any test
    # body returns.
    ROOT_CONFTEST._restore_socket_attributes(snapshot)

    assert socket.socket.connect is original_connect
    assert socket.socket.connect_ex is original_connect_ex
    assert socket.create_connection is original_create_connection


def test_the_actual_autouse_fixture_generator_restores_after_a_leaking_body() -> None:
    """Same scenario, but driven through the REAL ``@pytest.fixture``-
    decorated generator object from ``tests/conftest.py`` (via its
    ``__wrapped__`` raw function), not just the two helper functions --
    so a future edit that changes the fixture without updating the
    helpers is still caught."""

    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex
    original_create_connection = socket.create_connection

    fixture_callable = ROOT_CONFTEST._restore_socket_attributes_after_every_test
    raw_function = getattr(fixture_callable, "__wrapped__", fixture_callable)
    generator = raw_function()

    next(generator)  # advance to the fixture's `yield` (the setup half)

    leaked_guard = arm_offline_guard()
    assert socket.socket.connect is not original_connect
    assert leaked_guard.count == 0

    with pytest.raises(StopIteration):
        next(generator)  # advance past `yield` (the teardown half)

    assert socket.socket.connect is original_connect
    assert socket.socket.connect_ex is original_connect_ex
    assert socket.create_connection is original_create_connection


# ---------------------------------------------------------------------------
# 5: end-to-end proof -- a real loopback server connects after a restore
# ---------------------------------------------------------------------------


def test_loopback_server_connects_fine_after_a_disarm() -> None:
    guard = arm_offline_guard()
    with pytest.raises(AuditError, match="offline guard"):
        socket.create_connection(("127.0.0.1", 1))
    guard.disarm()

    server, port = _loopback_listener()
    try:
        connection = socket.create_connection(("127.0.0.1", port), timeout=5.0)
        connection.close()
    finally:
        server.close()


def test_loopback_server_connects_fine_after_the_conftest_fixture_restores() -> None:
    """The same end-to-end proof, but restoring through the conftest
    fixture's own snapshot/restore path rather than ``disarm()`` -- the
    scenario a real leaking test-then-next-test pair goes through."""

    snapshot = ROOT_CONFTEST._snapshot_socket_attributes()

    leaked_guard = arm_offline_guard()
    with pytest.raises(AuditError, match="offline guard"):
        socket.create_connection(("127.0.0.1", 1))
    assert leaked_guard.count == 1

    ROOT_CONFTEST._restore_socket_attributes(snapshot)

    server, port = _loopback_listener()
    try:
        connection = socket.create_connection(("127.0.0.1", port), timeout=5.0)
        connection.close()
    finally:
        server.close()
