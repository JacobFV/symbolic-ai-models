#!/usr/bin/env bash
#
# Decode continuations from every finished run in a directory, for review by a
# person or by a large pretrained model.
#
# Sampling is outside the evaluation path on purpose: nothing it produces feeds
# a metric, and the counts printed at the end of each transcript have no floor
# attached. It is a window on what a model actually emits when it has to stand
# on its own output, which no aggregate will show you.
#
#   scripts/qualitative-sample.sh runs/both
#   scripts/qualitative-sample.sh runs/both --per-lesson 3 --sample --temperature 0.8
#   scripts/qualitative-sample.sh runs/both --lessons unification,palindrome
#
# Writes, under <runs-dir>/samples/:
#   <model>.txt    a readable transcript, prompts included
#   <model>.json   flat records for a reviewing model to grade
#   review.md      one prompt you can paste to a frontier model
#
set -euo pipefail

if [[ $# -lt 1 || "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'
    exit 0
fi

ROOT="$1"; shift
[[ -d "$ROOT" ]] || { echo "no such directory: $ROOT" >&2; exit 1; }

OUT="$ROOT/samples"
mkdir -p "$OUT"

# `uv run` if this is a uv checkout, otherwise trust the installed entry point.
if command -v uv >/dev/null 2>&1 && [[ -f pyproject.toml ]]; then
    CLI=(uv run symbolic-ai-models)
else
    CLI=(symbolic-ai-models)
fi

shopt -s nullglob
runs=("$ROOT"/*/summary.json)
if [[ ${#runs[@]} -eq 0 ]]; then
    echo "no finished runs in $ROOT (a run writes summary.json when it completes)" >&2
    exit 1
fi

echo "sampling ${#runs[@]} run(s) from $ROOT -> $OUT" >&2
for summary in "${runs[@]}"; do
    run="$(dirname "$summary")"
    name="$(basename "$run")"
    echo "  $name" >&2
    # A failure on one model must not take the batch down with it: `synth`
    # enumerates programs per position and can be very slow, and a run left
    # half-written by an interrupted sweep should simply be skipped.
    if ! "${CLI[@]}" sample "$run" --json "$OUT/$name.json" "$@" \
            > "$OUT/$name.txt" 2>"$OUT/$name.err"; then
        echo "    failed — see $OUT/$name.err" >&2
        continue
    fi
    rm -f "$OUT/$name.err"
    tail -3 "$OUT/$name.txt" | sed 's/^/    /' >&2
done

cat > "$OUT/review.md" <<'EOF'
# Qualitative review

Each JSON file in this directory holds continuations from one model. A record is:

    lesson_id      which curriculum lesson the episode came from
    prompt         what the model was shown
    gold           the answer the curriculum computed
    generated      what the model produced, decoded from the prompt alone
    choices        the answer set the prompt offered
    exact_match    generated == gold
    in_answer_set  generated is at least one of the options
    mean_logprob   the model's own confidence, per token

These are samples, not a benchmark. `exact_match` is already counted in the
transcripts and needs no help; what a reviewer is for is the part a number
cannot carry. Useful questions:

- When it is wrong, is it wrong in a *structured* way — right type of answer,
  wrong element — or is it emitting the prompt's boilerplate back?
- Does it ever produce something outside the answer set, and what does that
  look like?
- Do the failures cluster by lesson in a way the aggregate scores hide?
- Is confidence related to correctness at all, or is it flat?

Do not convert your reading into a score to be compared against the metrics in
`summary.json`. Those have floors; this does not.
EOF

echo "wrote transcripts, JSON and $OUT/review.md" >&2
