#!/usr/bin/env bash
# The controls, added into the ladder's own directories with --resume.
#
# **`gparse-none` is the abstention row.** It does not override `node_votes`, so
# on a graph task it says nothing and its score *is* the shared back-off — the
# unigram plus the structural context prior. Without it a lift on `nodeans`
# cannot be told apart from the harness answering under the model's name, which
# is the failure `notes/lessons/2026-08-14-a-score-can-be-the-back-off-wearing-
# the-models-name.md` is about. Every arm gets one.
#
# **`vsa_perm_pure-002` is `vsa_perm-002` with `structural_fallback` off.** The
# repo's standing rule is to report a model number with and without the shared
# floor where one exists; this is that pair, for one pointer, at the two rates
# that matter most.
set -u

cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4
LOGS=${LOGS:-/tmp/infill-logs}
mkdir -p "$LOGS"

arm () {                    # arm <task> <mask-rate> <out-suffix> <models>
  echo "=== $(date -Is)  controls task=$1 mask_rate=$2 -> runs/infill-$3"
  nice -n 10 uv run symbolic-ai-models sweep \
      --config configs/full179.toml \
      --tasks "$1" --mask-rate "$2" --models "$4" \
      --out "runs/infill-$3" --resume \
      >> "$LOGS/$3.log" 2>&1
  echo "    exit=$? $(date -Is)"
}

ABSTAIN=gparse-none
PURE=gparse-none,vsa_perm_pure-002

arm nodeans 0.15 ans      "$PURE"
arm node    0.15 node-r015 "$PURE"
arm node    0.90 node-r090 "$PURE"
arm node    0.35 node-r035 "$ABSTAIN"
arm node    0.60 node-r060 "$ABSTAIN"
arm nodesub 0.15 sub-r015  "$ABSTAIN"
arm nodesub 0.35 sub-r035  "$ABSTAIN"

echo "=== controls done $(date -Is)"
