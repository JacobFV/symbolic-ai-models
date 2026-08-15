#!/usr/bin/env bash
# The `005` sweep: one model per process, resumable.
#
# One process per model, deliberately. Long single-process jobs on this box are
# killed at ~20 minutes and take the process group with them --
# `scripts/wals_perlang.py` records the four dead runs that taught it -- and
# `--resume` then means an interruption costs one model rather than eighteen.
#
# The reference rows are re-run *into the same directory* rather than cited from
# `runs/vsa_reach`. They should reproduce their published numbers to three
# decimals, and a row that does not is a harness change that has to be found
# before any -005 number is read.
set -u
cd "$(dirname "$0")/.."
OUT="${OUT:-runs/metta005}"

MODELS=(
  # the harness check, first, because nothing else may be read until it passes
  metta_tuple-005 metta_tuple_pure-005
  # the reference rows, same config, same floors, same eval seeds
  vsa_sum-004 vsa_sum_pure-004 vsa_hks-004 vsa_hks_pure-004
  vsa_perm-002 vsa_perm_pure-002 corefer-001
  # the experiment
  metta-005 metta_pure-005
  metta_gated-005 metta_gated_pure-005
  metta_shuf-005 metta_shuf_pure-005
  metta_perm-005 metta_perm_pure-005
  metta_type-005 metta_type_pure-005
)

for m in "${MODELS[@]}"; do
  if [ -f "$OUT/$m/summary.json" ]; then
    echo "== skip $m (already complete)"
    continue
  fi
  echo "== $m"
  uv run symbolic-ai-models sweep --config configs/full179.toml \
      --out "$OUT" --models "$m" --resume 2>&1 | tail -4
done
echo "== all done"
