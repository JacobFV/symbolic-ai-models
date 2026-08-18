"""Kernels: specialised reasoners behind one narrow typed contract.

There is **no universal inference language here.** The world IR is universal-ish
and every kernel gets a *projection* of it — datalog, ASP, SMT, Lean, e-graphs
and the physics engines each see the subset of the world their language can
express, in their own syntax. See
``notes/decisions/2026-08-18-the-kernel-stack-is-a-set-of-projections.md``.

Two typed maps per kernel:

* ``P_K : World -> L_K`` — the projection, which **declares what it discarded**.
* ``R_K : L_K -> WorldDelta`` — the result, as claims and a delta.

The discard record is what makes the arrangement honest. A projection is lossy
by construction: an ASP projection of a world holding a covariance matrix and
continuous geometry cannot represent either, and the dangerous failure is not a
crash but a silent success — an answer about a fragment, read as an answer about
the world. So a kernel may not assert a claim whose support it discarded, and
:func:`symbolic_ai_kernels.abi.check_entitlement` enforces it.
"""

from __future__ import annotations

from .abi import (Discard, Kernel, KernelCost, KernelManifest, KernelRequest,
                  KernelResult, KernelUnavailable, Projection, SEMANTICS,
                  check_entitlement, get_kernel, kernel_ids, register_kernel,
                  KERNELS, KERNEL_MODULES)

__all__ = ["Discard", "Kernel", "KernelCost", "KernelManifest", "KernelRequest",
           "KernelResult", "KernelUnavailable", "Projection", "SEMANTICS",
           "check_entitlement", "get_kernel", "kernel_ids", "register_kernel",
           "KERNELS", "KERNEL_MODULES"]
