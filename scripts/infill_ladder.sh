#!/usr/bin/env bash
# The infilling ladder: rung 3 first, then the mask-rate curve, then subtrees.
#
# Rung 3 (`nodeans`) runs first on purpose. It is the rung that can *refute* the
# reframe — if completing the answer subtree also scores ~0 then generation is
# absent rather than mis-measured — and there is no point building the rest of
# the ladder before knowing that. See
# `notes/decisions/2026-08-14-the-infilling-ladder-preregistration.md`.
#
# Every arm is one `symbolic-ai-models sweep` over all 179 lessons with
# `configs/full179.toml` unchanged apart from the task and the mask rate, so the
# floors are refitted per arm by construction. `--resume` makes an interruption
# cost one model rather than the arm.
set -u

cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4

MODELS=corefer-001,ptrgen-001,routes-001,evidence-001,vsa_perm-002,ruleinduce-001,grammar-001,ngram-001,ctw-001,brill-001,omegaclaw_rank-001,omegaclaw_ctx-001
LOGS=${LOGS:-/tmp/infill-logs}
mkdir -p "$LOGS"

arm () {                    # arm <task> <mask-rate> <out-suffix>
  echo "=== $(date -Is)  task=$1 mask_rate=$2 -> runs/infill-$3"
  nice -n 10 uv run symbolic-ai-models sweep \
      --config configs/full179.toml \
      --tasks "$1" --mask-rate "$2" --models "$MODELS" \
      --out "runs/infill-$3" --resume \
      > "$LOGS/$3.log" 2>&1
  echo "    exit=$? $(date -Is)"
}

# rung 3 — the refutation, first
arm nodeans 0.15 ans          # mask_rate is ignored in answer mode

# rung 1 — the curve, in order, so an interruption still leaves a usable one.
# Cost rises with the rate (more masked nodes is more fitting and more scoring),
# so this also puts the cheap arms first.
arm node 0.15 node-r015       # also the bit-identity check against runs/full179
arm node 0.35 node-r035
arm node 0.60 node-r060
arm node 0.90 node-r090

# rung 2 — a constituent instead of scattered nodes, at matched budget.
#
# Only the two low rates. Not a budget cut: at 0.60 and 0.90 the two regimes
# **converge by arithmetic**. Scattered masking at 0.90 already leaves only 11.9%
# of hidden nodes with a visible parent and subtree masking leaves 10.8% — the
# holes are the same shape because almost everything is hidden either way. The
# contrast the rung exists to measure lives at the low rates, where scattered
# masking leaves runs of 1.2 nodes and subtree masking leaves 2.3.
arm nodesub 0.15 sub-r015
arm nodesub 0.35 sub-r035

echo "=== done $(date -Is)"
