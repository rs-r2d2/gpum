"""A GPU load generator for the hardware suite.

SC-010 asks for agreement with the vendor tool "under varying load", which needs load that
actually varies — an idle GPU agrees trivially at 0% and proves nothing. Nothing on a plain
driver install generates GPU work, so this compiles a small CUDA spin kernel with ``nvcc``.

**Compiled to PTX, not SASS.** ``-arch=compute_NN -code=compute_NN`` emits PTX only, which the
driver JIT-compiles for whatever architecture is actually present. A toolkit several
generations older than the card (CUDA 12.0 against a Blackwell part, here) therefore still
produces something that runs, where targeting SASS directly would fail to build.

Every failure path skips rather than fails: no ``nvcc``, no toolkit headers, a driver that
refuses the JIT. This is a test dependency of the hardware suite, not of the product.
"""

from __future__ import annotations

import contextlib
import pathlib
import shutil
import subprocess
import tempfile
import time
from collections.abc import Iterator

import pytest

_SOURCE = r"""
#include <cstdio>
#include <cstdlib>
#include <ctime>

__global__ void spin(float* out, long long iters) {
    float acc = threadIdx.x * 1e-3f;
    for (long long i = 0; i < iters; ++i) acc = acc * 1.0000001f + 1e-7f;
    if (acc == 12345.678f) out[0] = acc;
}

int main(int argc, char** argv) {
    // A self-imposed deadline: if the parent test dies without reaping us, the GPU does not
    // stay pinned at 100% forever.
    double budget = argc > 1 ? atof(argv[1]) : 60.0;
    time_t started = time(NULL);
    float* d;
    if (cudaMalloc(&d, sizeof(float)) != cudaSuccess) { printf("MALLOC_FAIL\n"); return 2; }
    while (difftime(time(NULL), started) < budget) {
        spin<<<512, 256>>>(d, 200000);
        cudaError_t e = cudaDeviceSynchronize();
        if (e != cudaSuccess) { printf("LAUNCH_FAIL %s\n", cudaGetErrorString(e)); return 3; }
    }
    cudaFree(d);
    return 0;
}
"""

_ARCH = "compute_75"
_binary: pathlib.Path | None = None
_build_failed = False


def _build() -> pathlib.Path:
    """Compile once per session; skip the whole suite's load tests if it cannot be built."""
    global _binary, _build_failed
    if _binary is not None:
        return _binary
    if _build_failed:
        pytest.skip("CUDA load generator could not be built earlier in this session")

    nvcc = shutil.which("nvcc")
    if nvcc is None:
        _build_failed = True
        pytest.skip("nvcc is not installed, so GPU load cannot be generated")

    tmp = pathlib.Path(tempfile.mkdtemp(prefix="gpum-loadgen-"))
    source = tmp / "spin.cu"
    source.write_text(_SOURCE)
    output = tmp / "spin"
    result = subprocess.run(
        [nvcc, f"-arch={_ARCH}", f"-code={_ARCH}", "-o", str(output), str(source)],
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    if result.returncode != 0 or not output.exists():
        _build_failed = True
        pytest.skip(f"nvcc could not build the load generator: {result.stderr.strip()[:400]}")

    _binary = output
    return output


@contextlib.contextmanager
def gpu_load(duration_s: float) -> Iterator[subprocess.Popen]:
    """Hold the GPU busy for the duration of the block.

    Verifies the kernel actually launched before yielding — a JIT failure exits immediately,
    and silently measuring an idle GPU while believing it loaded is the one outcome that would
    make SC-010 meaningless.
    """
    binary = _build()
    # A little slack past the requested duration, so the kernel does not stop before the caller.
    process = subprocess.Popen(
        [str(binary), str(duration_s + 15)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        time.sleep(2.0)
        if process.poll() is not None:
            out, err = process.communicate()
            pytest.skip(f"load kernel exited immediately: {out.strip()} {err.strip()}")
        yield process
    finally:
        process.terminate()
        with contextlib.suppress(subprocess.TimeoutExpired):
            process.wait(timeout=10)
        if process.poll() is None:
            process.kill()
            process.wait(timeout=10)
