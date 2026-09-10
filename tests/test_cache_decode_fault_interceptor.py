"""Exercise the test-only decoder fault hook with a synthetic backend."""

import os
import subprocess
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
SUPPORT = ROOT / "tests" / "runtime_support"
INC = Path("/home/chao/llama-worktrees/featcache-require-hit/include")
pytestmark = pytest.mark.skipif(
    not (INC / "llama.h").is_file(),
    reason="requires the pinned local llama.cpp headers for the actual C ABI",
)


def comp(src, out, *args):
    subprocess.run(
        [
            "cc",
            "-std=c11",
            "-Wall",
            "-Wextra",
            "-Werror",
            str(src),
            *args,
            "-o",
            str(out),
        ],
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.fixture(scope="module")
def bins(tmp_path_factory):
    b = tmp_path_factory.mktemp("fault")
    lib = b / "libfault.so"
    caller = b / "caller"
    comp(
        SUPPORT / "llama_decode_fault.c",
        lib,
        "-shared",
        "-fPIC",
        f"-I{INC}",
        f"-I{INC.parent / 'ggml/include'}",
        "-ldl",
        "-pthread",
    )
    backend = b / "backend.c"
    backend.write_text("""#include <stdint.h>
#include <stdio.h>
#include "llama.h"
int32_t llama_decode(struct llama_context *c,struct llama_batch b){(void)c;(void)b;puts("backend");return 7;}
""")
    comp(
        backend,
        b / "libbackend.so",
        "-shared",
        "-fPIC",
        f"-I{INC}",
        f"-I{INC.parent / 'ggml/include'}",
    )
    src = b / "dummy.c"
    src.write_text("""#include <stdio.h>
#include "llama.h"
int main(void){struct llama_batch t={0},e={0};float x=1;e.embd=&x;printf("text=%d\\n",llama_decode(0,t));printf("embedding=%d\\n",llama_decode(0,e));printf("again=%d\\n",llama_decode(0,e));}
""")
    comp(
        src,
        caller,
        f"-I{INC}",
        f"-I{INC.parent / 'ggml/include'}",
        f"-L{b}",
        "-lbackend",
        f"-Wl,-rpath,{b}",
    )
    return lib, caller


def run(lib, caller, trigger=None):
    env = os.environ.copy()
    env["LD_PRELOAD"] = str(lib)
    if trigger is None:
        env.pop("SAEA_CACHE_DECODE_FAULT_TRIGGER", None)
    else:
        env["SAEA_CACHE_DECODE_FAULT_TRIGGER"] = str(trigger)
    return subprocess.run(
        [str(caller)], env=env, check=True, capture_output=True, text=True
    )


def test_passthrough(bins):
    lib, caller = bins
    r = run(lib, caller)
    assert r.stderr == ""
    assert r.stdout.count("backend") == 3


def test_one_failure_and_resume(bins, tmp_path):
    lib, caller = bins
    p = tmp_path / "trigger"
    p.touch()
    r = run(lib, caller, p)
    assert r.stdout.count("backend") == 2
    assert "embedding=-1" in r.stdout
    assert "again=7" in r.stdout
    assert r.stderr.count("SAEA_INJECTED_EMBEDDED_DECODE_FAILURE") == 1


def test_text_immune(bins, tmp_path):
    lib, caller = bins
    p = tmp_path / "trigger"
    p.touch()
    assert "text=7" in run(lib, caller, p).stdout


def test_relative_ignored(bins):
    lib, caller = bins
    e = os.environ.copy()
    e["LD_PRELOAD"] = str(lib)
    e["SAEA_CACHE_DECODE_FAULT_TRIGGER"] = "relative"
    r = subprocess.run([str(caller)], env=e, check=True, capture_output=True, text=True)
    assert r.stdout.count("backend") == 3
    assert r.stderr == ""


def test_absent_absolute_trigger_passes_through(bins, tmp_path):
    lib, caller = bins
    result = run(lib, caller, tmp_path / "absent")
    assert result.stdout.count("backend") == 3
    assert result.stderr == ""


def test_directory_is_not_a_trigger_file(bins, tmp_path):
    lib, caller = bins
    result = run(lib, caller, tmp_path)
    assert result.stdout.count("backend") == 3
    assert result.stderr == ""
