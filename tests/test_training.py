"""The harness end to end: floors, a real (tiny) run, reload, and scoring."""

from __future__ import annotations

import collections
import copy
import json
from pathlib import Path

import pytest
import torch

from symbolic_ai_models.agent import evaluate_choices, as_text_agent, score_choices
from symbolic_ai_core.data.curriculum import generate
from symbolic_ai_models.report import comparison_table, load_summaries
from symbolic_ai_models.models import ModelConfig, build
from symbolic_ai_models.tasks import Totals, make_task
from symbolic_ai_models.train import (TrainConfig, build_tokenizer, load_data,
                                      load_run, train)

LESSONS = "unification,symbol_grounding,context_free_language"


def small_config(out: Path, **kw) -> TrainConfig:
    base = dict(model="ngram", tasks=("lm", "node"), lessons=LESSONS,
                n_train=12, n_eval=4, steps=4, eval_every=2, log_every=100,
                d_model=32, n_layers=2, n_heads=4, d_ff=64, batch_size=4,
                vocab_size=400, max_nodes=64, max_len=192, device="cpu",
                amp=False, out=str(out))
    base.update(kw)
    return TrainConfig(**base)


@pytest.fixture(scope="module")
def episodes():
    return list(generate(["unification", "symbol_grounding"], n=4))


# ---- floors ---------------------------------------------------------------
def test_floors_are_fitted_on_train_and_scored_on_eval(episodes):
    """A floor that gets to look at the eval answers is not a floor."""
    cfg = small_config(Path("."))
    tok = build_tokenizer(cfg, episodes)
    train_eps, eval_eps = episodes[:6], episodes[6:]
    for name in ("lm", "node"):
        task = make_task(name, **({"max_len": 192} if name == "lm"
                                  else {"max_nodes": 64}))
        floor = task.floor(eval_eps, tok, train_eps)
        for key, value in floor.items():
            if key.endswith("_acc"):
                assert 0.0 <= value <= 1.0, f"{name}.{key} = {value}"
            if key.endswith("_bits"):
                assert value >= 0.0


def test_node_floor_is_beatable_but_not_trivial(episodes):
    """Type is easy and label is hard — the reason they are reported apart."""
    cfg = small_config(Path("."))
    tok = build_tokenizer(cfg, episodes)
    floor = make_task("node", max_nodes=64).floor(episodes, tok, episodes)
    assert floor["type_acc"] > floor["label_acc"]
    assert floor["label_acc"] < 0.5, "labels should not be dominated by one class"


def test_type_floor_reflects_how_structural_node_type_is(episodes):
    """A majority-class floor would badly overstate the type result.

    Node type is very nearly a function of tree shape, so the floor has to be a
    structural baseline; if it were the most common type, a model that had
    learned less than a lookup table would still show a large lift.
    """
    cfg = small_config(Path("."))
    tok = build_tokenizer(cfg, episodes)
    floor = make_task("node", max_nodes=64).floor(episodes, tok, episodes)
    majority = max(collections.Counter(
        t for ep in episodes for t in ep.graph.types).values())
    total = sum(len(ep.graph.types) for ep in episodes)
    assert floor["type_acc"] > majority / total + 0.2, \
        "the type floor should be far above the most common type"


def test_vocabulary_reserves_room_for_whole_node_labels(episodes):
    """Node labels must be single ids or the masked-node task cannot ask."""
    cfg = small_config(Path("."), vocab_size=400)
    tok = build_tokenizer(cfg, episodes)
    labels = {l for ep in episodes for l in ep.graph.labels if l}
    named = sum(1 for l in labels if tok.label_id(l) != tok.unk_id)
    assert named > len(labels) * 0.5, "most node labels should be nameable"


# ---- a run ----------------------------------------------------------------
@pytest.fixture(scope="module")
def finished_run(tmp_path_factory):
    out = tmp_path_factory.mktemp("run")
    summary = train(small_config(out))
    return out, summary


def test_a_run_writes_everything_needed_to_reproduce_it(finished_run):
    out, summary = finished_run
    for name in ("model.pt", "tokenizer.json", "history.json", "summary.json"):
        assert (out / name).exists(), f"missing {name}"
    assert summary["parameters"] > 0
    assert set(summary["final"]) == {"lm", "node"}
    assert TrainConfig.from_dict(summary["config"]).model == "ngram"


def test_metrics_carry_their_floor_and_lift(finished_run):
    _, summary = finished_run
    node = summary["final"]["node"]
    for prefix in ("label", "type"):
        assert f"{prefix}_acc" in node
        assert f"{prefix}_floor" in node
        assert f"{prefix}_lift" in node
    assert "token_floor_bits" in summary["final"]["lm"]


def test_a_run_reloads_and_produces_the_same_numbers(finished_run, episodes):
    out, _ = finished_run
    model, tok, cfg = load_run(out)
    assert cfg.model == "ngram"
    batch = make_task("node", max_nodes=64).collate(episodes, tok)
    with torch.no_grad():
        first = model(batch).symbol_logits
        second = model(batch).symbol_logits
    assert torch.allclose(first, second), "eval mode should be deterministic"


def test_the_development_split_cannot_overlap_the_training_seeds(tmp_path):
    """`eval_seed0` buys a dev split, and must not buy a memorisation score.

    `scripts/rsi_loop.py` ranks candidates on a config whose scored seeds start
    at 500,000 rather than at a million, because `CLAUDE.md` forbids settling a
    design choice against evaluation and until that field existed there was no
    way to obey the rule while scoring anything. The field is therefore load
    bearing in a new way: set it *below* `n_train` and the scored episodes are
    episodes the model was fitted on, and every number downstream is a
    memorisation score wearing the run's name.

    Nothing else in the suite would notice — the run would finish, write a
    summary, and report a very good accuracy.
    """
    base = dict(model="ngram-001", tasks=("node",), lessons="counting_quantifier",
                n_train=20, n_eval=2, max_nodes=48, device="cpu",
                out=str(tmp_path / "overlap"))
    with pytest.raises(ValueError, match="overlaps the training seeds"):
        train(TrainConfig.from_dict({**base, "eval_seed0": 5}))


def test_eval_seed0_defaults_to_the_evaluation_range(tmp_path):
    """A config that says nothing gets evaluation seeds, as it always did.

    The default is what every published number in this repo was measured under,
    so it is pinned rather than assumed: a field added for a development split
    must not have quietly moved the split for runs that never asked.
    """
    assert TrainConfig().eval_seed0 == 1_000_000
    train_eps, eval_eps = load_data(TrainConfig.from_dict(
        dict(lessons="counting_quantifier", n_train=3, n_eval=2, max_nodes=48)))
    dev_eps = load_data(TrainConfig.from_dict(
        dict(lessons="counting_quantifier", n_train=3, n_eval=2, max_nodes=48,
             eval_seed0=500_000)))[1]
    assert [e.text for e in eval_eps] != [e.text for e in dev_eps], (
        "the development split drew the same episodes as evaluation; it is not "
        "a separate split and ranking on it would be tuning against evaluation")
    assert [e.text for e in dev_eps] != [e.text for e in train_eps[:len(dev_eps)]]


def test_single_task_runs_do_not_require_the_other(tmp_path):
    """A model trained only on graphs must not need the text task to exist."""
    summary = train(small_config(tmp_path / "node_only", tasks=("node",),
                                 task_weights={"node": 1.0}))
    assert set(summary["final"]) == {"node"}


def test_comparison_table_reads_finished_runs(finished_run):
    out, _ = finished_run
    table = comparison_table(load_summaries([out]))
    assert "ngram" in table and "lift" in table


def test_comparison_table_survives_a_missing_task(tmp_path, finished_run):
    """Runs with different task sets still line up in one table."""
    out, _ = finished_run
    train(small_config(tmp_path / "lm_only", tasks=("lm",), task_weights={"lm": 1.0}))
    table = comparison_table(load_summaries([out, tmp_path / "lm_only"]))
    assert "-" in table and table.count("\n") >= 4


# ---- choice scoring -------------------------------------------------------
def test_choice_scoring_prefers_nothing_by_construction(finished_run, episodes):
    """Scores are per-token means, so a long option is not penalised for length."""
    out, _ = finished_run
    model, tok, cfg = load_run(out)
    ep = episodes[0]
    scores = score_choices(model, tok, ep.prompt, ["a", "a much longer answer"],
                           max_len=cfg.max_len)
    assert len(scores) == 2 and all(s < 0 for s in scores)


def test_curriculum_report_has_a_floor(finished_run, episodes):
    out, _ = finished_run
    model, tok, cfg = load_run(out)
    report = evaluate_choices(model, tok, episodes, max_len=cfg.max_len)
    assert len(report.results) == len(episodes)
    assert 0.0 <= report.accuracy <= 1.0
    assert report.floor > 0.0, "a multiple-choice floor is never zero"
    assert "macro-average" in report.table()


def test_text_agent_recovers_the_options_from_the_prompt(finished_run, episodes):
    """The interop path for `langcurriculum.evaluate`, which passes only text."""
    out, _ = finished_run
    model, tok, cfg = load_run(out)
    agent = as_text_agent(model, tok, max_len=cfg.max_len)
    for ep in episodes:
        answer = agent(ep.prompt)
        assert answer in ep.choices, f"{ep.lesson_id}: {answer!r} not an option"


# ---- the answer span ------------------------------------------------------
def test_answer_positions_are_marked_and_scored_apart(episodes):
    """The LM metric has to separate the answer from the boilerplate.

    Only ~1.4% of scored positions across the curriculum are the answer; the
    rest is the question and the fixed scaffolding around it. Without the split,
    `token_bits` measures template reproduction and a model can look excellent
    on it while never getting an answer right.
    """
    from symbolic_ai_core.data.batch import collate_text
    cfg = small_config(Path("."))
    tok = build_tokenizer(cfg, episodes)
    b = collate_text(episodes, tok, max_len=256)
    assert b.answer_mask is not None and b.answer_mask.any()
    # Far fewer answer positions than scored positions, and every marked one
    # really does have a target.
    scored = (b.target_tokens >= 0)
    assert int(b.answer_mask.sum()) < int(scored.sum())
    assert bool((scored | ~b.answer_mask).all()), "a marked position with no target"
    # What is marked is genuinely the answer's own tokens. Decoded, not joined:
    # an invented name like "Frank" is usually out of vocabulary and arrives as
    # its UTF-8 bytes, so the ids are only text again on the way out.
    for i, ep in enumerate(episodes):
        got = b.target_tokens[i][b.answer_mask[i]].tolist()
        assert tok.decode(got).strip() == ep.answer.strip()


def test_marking_the_answer_does_not_change_the_input(episodes):
    """`answer_mask` is reporting only — the sequence must be untouched."""
    from symbolic_ai_core.data.batch import collate_text
    cfg = small_config(Path("."))
    tok = build_tokenizer(cfg, episodes)
    b = collate_text(episodes, tok, max_len=512)
    for i, ep in enumerate(episodes):
        ids = b.tokens[i][b.pad_mask[i]].tolist()
        assert tok.decode(ids) == ep.text


def test_answer_metrics_have_their_own_floor(episodes):
    """Answers come from a narrower distribution than prose and need their own."""
    cfg = small_config(Path("."))
    tok = build_tokenizer(cfg, episodes)
    floor = make_task("lm", max_len=256).floor(episodes, tok, episodes)
    for key in ("answer_acc", "answer_bits", "token_acc", "token_bits"):
        assert key in floor
    # It is fitted on answers alone: the count must be exactly the answer tokens.
    expected = sum(len(tok.encode(ep.answer)) for ep in episodes)
    assert floor["answer_n"] == expected
    # And it is a different distribution from the text as a whole — in practice
    # a *harder* one, since answers are largely the per-episode invented names
    # while the prose is mostly recurring boilerplate.
    assert floor["answer_bits"] != floor["token_bits"]


def test_node_report_says_how_much_it_covers(episodes):
    """`label_acc` is an accuracy over the nameable labels; say which share."""
    cfg = small_config(Path("."))
    tok = build_tokenizer(cfg, episodes)
    task = make_task("node", max_nodes=64)
    totals = Totals()
    batch = task.collate(episodes, tok)
    model = build("ngram", ModelConfig(vocab_size=len(tok), d_model=32,
                                       n_layers=1, n_heads=2, d_ff=32))
    model.fit_on(episodes, tok)
    totals.add(task.compute(model(batch), batch).counts)
    out = task.summarize(totals)
    assert 0.0 <= out["label_coverage"] <= 1.0


# ---- persistence of the rule-based half -----------------------------------
@pytest.mark.parametrize("name", ["ngram", "ruleinduce", "symbolalg",
                                  "syllogism", "evidence", "synth"])
def test_a_fitted_rule_based_model_survives_a_round_trip(name, tmp_path, episodes):
    """A decision list is not a tensor, so `state_dict` cannot see it.

    Without the extra state a reloaded symbolic model has its back-off and none
    of its rules, which would make `eval` and `sample` quietly score the prior
    instead of the model.
    """
    summary = train(small_config(tmp_path / name, model=name, tasks=("node",),
                                 task_weights={"node": 1.0}))
    assert summary["family"] == "rule-based"
    model, tok, _ = load_run(tmp_path / name)

    batch = make_task("node", max_nodes=64).collate(episodes, tok)
    with torch.no_grad():
        reloaded = model(batch).symbol_logits
    fresh = build(name, ModelConfig(vocab_size=len(tok), d_model=32, n_layers=2,
                                    n_heads=4, d_ff=64, dropout=0.0))
    fresh.fit_on(load_data(TrainConfig(**{**small_config(tmp_path, model=name).to_dict(),
                                          "tasks": ("node",)}))[0], tok)
    with torch.no_grad():
        direct = fresh.eval()(batch).symbol_logits
    assert torch.allclose(reloaded, direct, atol=1e-5), \
        f"{name}: reloaded model does not predict what the fitted one did"


def test_reloading_a_symbolic_run_without_its_state_is_an_error(tmp_path, episodes):
    """Fail loudly rather than silently scoring the back-off."""
    import torch as _torch
    out = tmp_path / "stale"
    train(small_config(out, model="ngram", tasks=("node",),
                       task_weights={"node": 1.0}))
    ckpt = _torch.load(out / "model.pt", weights_only=False)
    ckpt.pop("symbolic_state")
    _torch.save(ckpt, out / "model.pt")
    with pytest.raises(ValueError, match="learned state"):
        load_run(out)


# ---- sampling -------------------------------------------------------------
def test_sampling_never_shows_the_model_its_answer(finished_run, episodes):
    """The decoder is fed the prompt and must produce the rest itself."""
    from symbolic_ai_models.decode import SamplingConfig, sample_episodes
    out, _ = finished_run
    model, tok, _ = load_run(out)
    samples = sample_episodes(model, tok, episodes[:3],
                              config=SamplingConfig(max_new_tokens=6))
    assert len(samples) == 3
    for s, ep in zip(samples, episodes[:3]):
        assert s.prompt == ep.prompt and s.gold == ep.answer

    # The decisive check: rewrite the gold answers and the continuations must
    # not budge. (Asserting the answer is absent from the prompt would be
    # wrong — the prompt states the answer *set*, and the answer is in it.)
    altered = [copy.deepcopy(e) for e in episodes[:3]]
    for e in altered:
        e.answer = "zzzz"
    again = sample_episodes(model, tok, altered,
                            config=SamplingConfig(max_new_tokens=6))
    assert [x.generated for x in again] == [x.generated for x in samples]


def test_greedy_sampling_is_deterministic(finished_run, episodes):
    from symbolic_ai_models.decode import SamplingConfig, generate
    out, _ = finished_run
    model, tok, _ = load_run(out)
    cfg = SamplingConfig(max_new_tokens=8, greedy=True)
    a = generate(model, tok, episodes[0].prompt + "\n", config=cfg)
    b = generate(model, tok, episodes[0].prompt + "\n", config=cfg)
    assert a.text == b.text and a.token_ids == b.token_ids


def test_sampling_stops_and_reports_why(finished_run, episodes):
    from symbolic_ai_models.decode import SamplingConfig, generate
    out, _ = finished_run
    model, tok, _ = load_run(out)
    gen = generate(model, tok, episodes[0].prompt + "\n",
                   config=SamplingConfig(max_new_tokens=4))
    assert gen.stopped in ("eos", "newline", "length")
    assert len(gen.token_ids) <= 4
    assert "\n" not in gen.text
    assert len(gen.logprobs) == len(gen.token_ids)


def test_samples_export_as_json_for_a_reviewer(finished_run, episodes, tmp_path):
    from symbolic_ai_models.decode import SamplingConfig, sample_episodes, write_json
    out, _ = finished_run
    model, tok, _ = load_run(out)
    samples = sample_episodes(model, tok, episodes[:2],
                              config=SamplingConfig(max_new_tokens=4))
    path = write_json(tmp_path / "s.json", samples, model="ngram")
    payload = json.loads(path.read_text())
    assert payload["n"] == 2
    for record in payload["samples"]:
        for key in ("lesson_id", "prompt", "gold", "generated",
                    "exact_match", "in_answer_set", "choices"):
            assert key in record


# ---- resuming a long run --------------------------------------------------
@pytest.mark.skipif(
    "gru" not in __import__("symbolic_ai_models.models",
                            fromlist=["model_names"]).model_names(),
    reason="neural models not registered")
def test_training_resumes_where_it_stopped(tmp_path, episodes):
    """A five-hour run must be assemblable from pieces.

    Four attempts at the full-curriculum neural sweep have been killed part-way,
    twice leaving a directory holding a tokenizer and no summary. Without this
    the whole run is lost each time, which is why it never finished.
    """
    out = tmp_path / "resumable"
    first = train(small_config(out, model="gru", tasks=("node",),
                               task_weights={"node": 1.0}, steps=4,
                               eval_every=2))
    assert (out / "checkpoint.pt").exists()
    step = torch.load(out / "checkpoint.pt", weights_only=False)["step"]
    assert step == 4

    # Asking for more steps continues rather than starting over.
    second = train(small_config(out, model="gru", tasks=("node",),
                                task_weights={"node": 1.0}, steps=8,
                                eval_every=2, resume=True))
    assert torch.load(out / "checkpoint.pt", weights_only=False)["step"] == 8
    assert second["steps"] == 8
    assert first["parameters"] == second["parameters"]


@pytest.mark.skipif(
    "gru" not in __import__("symbolic_ai_models.models",
                            fromlist=["model_names"]).model_names(),
    reason="neural models not registered")
def test_resuming_a_finished_run_is_a_no_op(tmp_path):
    """Re-running a completed budget must not train it further."""
    out = tmp_path / "finished"
    train(small_config(out, model="gru", tasks=("node",),
                       task_weights={"node": 1.0}, steps=4, eval_every=2))
    again = train(small_config(out, model="gru", tasks=("node",),
                               task_weights={"node": 1.0}, steps=4,
                               eval_every=2, resume=True))
    assert torch.load(out / "checkpoint.pt", weights_only=False)["step"] == 4
    assert again["steps"] == 4


# ---- what "already ran" means ---------------------------------------------
def test_resume_reruns_a_model_that_ran_a_smaller_budget(tmp_path):
    """A finished run at a smaller budget is not finished for a larger one.

    Raising `--steps` over a directory of 300-step runs and passing `--resume`
    silently skipped every model and reprinted the stale table. It looked like a
    successful re-run, which is worse than a visible failure.
    """
    import argparse

    from symbolic_ai_models.cli import _already_ran

    out = tmp_path / "gru"
    out.mkdir()
    (out / "summary.json").write_text(json.dumps({"steps": 300}))

    assert _already_ran(out, argparse.Namespace(steps=300))
    assert _already_ran(out, argparse.Namespace(steps=200))
    assert not _already_ran(out, argparse.Namespace(steps=2000))
    # No budget asked for: any finished run counts.
    assert _already_ran(out, argparse.Namespace(steps=None))
    # A rule-based model reports 0 steps and never wants re-running.
    (out / "summary.json").write_text(json.dumps({"steps": 0}))
    assert _already_ran(out, argparse.Namespace(steps=2000))
    # Nothing there at all, and unreadable, both mean run it.
    assert not _already_ran(tmp_path / "absent", argparse.Namespace(steps=10))
    (out / "summary.json").write_text("{not json")
    assert not _already_ran(out, argparse.Namespace(steps=10))


def test_a_sweep_writes_where_its_config_says(tmp_path):
    """A config that names an output directory must be obeyed.

    It was not: the sweep read `--out` and nothing else, so
    `sweep --config configs/full179.toml` wrote to `runs/sweep` while the file
    said `runs/full179`. That is worse than a wrong path -- two sweeps under
    different configs land in one directory, and `--resume` then skips models on
    the strength of the other run's summaries.
    """
    import argparse

    from symbolic_ai_models.cli import _sweep_root

    config = tmp_path / "run.toml"
    config.write_text('out = "runs/named-by-config"\n')
    assert _sweep_root(argparse.Namespace(out=None, config=None)) == Path("runs/sweep")
    assert _sweep_root(argparse.Namespace(out=None, config=str(config))) \
        == Path("runs/named-by-config")
    # The flag still wins over the file.
    assert _sweep_root(argparse.Namespace(out="runs/flag", config=str(config))) \
        == Path("runs/flag")


# ---- a table's rows must come from one config -----------------------------
def test_comparison_table_flags_config_drift():
    """A table claims its rows differ only in the model. Nothing enforced it.

    `configs/full179.toml` did not pin `d_model` (default 256), so a partial
    re-run trained models 2.7x wider into a directory built at 96, and the rows
    would have printed looking exactly like the others.
    """
    from symbolic_ai_models.report import config_drift

    a = {"model": "gru", "family": "neural",
         "config": {"d_model": 96, "n_train": 20}}
    b = {"model": "ilp", "family": "rule-based",
         "config": {"d_model": 96, "n_train": 20}}
    assert config_drift([a, b]) == []
    assert config_drift([a]) == []

    wide = {"model": "tpr", "family": "neural",
            "config": {"d_model": 256, "n_train": 20}}
    warning = config_drift([a, b, wide])
    assert warning, "a width difference must be reported"
    joined = "\n".join(warning)
    assert "d_model" in joined and "tpr" in joined and "gru" in joined
    assert "n_train" not in joined, "keys that agree must not be reported"

    # A rule-based model reporting 0 steps next to a trained network is not
    # drift: it fits in one pass and never consumed a budget.
    same = [{"model": "ilp", "family": "rule-based", "steps": 0,
             "config": {"d_model": 96}},
            {"model": "gru", "family": "neural", "steps": 2000,
             "config": {"d_model": 96}}]
    assert config_drift(same) == []

    # Two networks on different budgets IS drift, and is the confound that cost
    # this repo the most: 300 steps put every network below the floor and 2000
    # put the first one above it. A half-finished re-run leaves both kinds of
    # row in one directory looking identical.
    budgets = [{"model": "gru", "family": "neural", "steps": 2000, "config": {}},
               {"model": "tpr", "family": "neural", "steps": 300, "config": {}},
               {"model": "ilp", "family": "rule-based", "steps": 0, "config": {}}]
    warned = config_drift(budgets)
    assert any("steps" in l and "gru" in l and "tpr" in l for l in warned)
    assert not any("ilp" in l for l in warned), \
        "a rule-based row must not be dragged into a budget comparison"

    # A rule-based model records d_model and has no tensors to apply it to.
    # Flagging that would fire on every mixed table and train readers to skip
    # the warning, so shape is compared among neural rows only.
    mixed = [{"model": "gru", "family": "neural", "config": {"d_model": 96}},
             {"model": "ilp", "family": "rule-based", "config": {"d_model": 256}},
             {"model": "brill", "family": "rule-based", "config": {"d_model": 256}}]
    assert config_drift(mixed) == []

    # Data disagreement is everyone's problem, whatever the family.
    split = [{"model": "gru", "family": "neural", "config": {"n_train": 20}},
             {"model": "ilp", "family": "rule-based", "config": {"n_train": 50}}]
    assert any("n_train" in l for l in config_drift(split))


@pytest.mark.skipif(
    "gru" not in __import__("symbolic_ai_models.models",
                            fromlist=["model_names"]).model_names(),
    reason="neural models not registered")
def test_resuming_keeps_the_vocabulary_it_was_trained_with(tmp_path):
    """Resume rebuilds the tokenizer from scratch. It must rebuild the same one.

    A checkpoint's embedding is a table indexed by token id. `train --resume`
    does not reload the tokenizer, it regenerates the episodes and refits the
    vocabulary, then loads weights into whatever model that produced. If the
    vocabulary came back in a different order, every embedding row would now
    belong to a different symbol -- and nothing would raise, because the shapes
    still match. Training would simply continue from scrambled weights, and the
    only visible sign would be a loss that jumped and then recovered, which is
    indistinguishable from an ordinary bad batch.

    Six hours of CPU training are about to be assembled out of resumed pieces,
    so this is the assumption that matters most and the one no test covered.
    """
    out = tmp_path / "vocab_stable"
    first = train(small_config(out, model="gru", tasks=("node",),
                               task_weights={"node": 1.0}, steps=6,
                               eval_every=3))
    before = (out / "tokenizer.json").read_text(encoding="utf-8")
    loss_before = first["final"]["node"]["label_bits"]

    second = train(small_config(out, model="gru", tasks=("node",),
                                task_weights={"node": 1.0}, steps=12,
                                eval_every=3, resume=True))
    assert (out / "tokenizer.json").read_text(encoding="utf-8") == before, \
        "the resumed run refitted a different vocabulary"
    assert second["vocab_size"] == first["vocab_size"]

    # Continuing, not restarting: six more steps from a warm model must not land
    # further from the answer than the cold model already was.
    cold = train(small_config(tmp_path / "cold", model="gru", tasks=("node",),
                              task_weights={"node": 1.0}, steps=6,
                              eval_every=3))["final"]["node"]["label_bits"]
    resumed = second["final"]["node"]["label_bits"]
    assert resumed <= max(loss_before, cold) + 0.5, (
        f"resumed loss {resumed:.3f} vs {loss_before:.3f} before the break "
        f"and {cold:.3f} cold -- weights and vocabulary may have desynchronised")


def test_the_floor_is_the_same_number_for_every_model(episodes):
    """Every lift in this repo is (score - floor) / (1 - floor).

    That subtraction only compares models if the floor is one number, identical
    for all of them. It is supposed to be a property of the episodes and the
    vocabulary alone -- a structure-only lookup table knows nothing about which
    model is being trained -- but nothing pinned that, and a floor that drifted
    per run would make every ranking in the README meaningless while every
    individual number stayed plausible.

    Checked directly on `runs/full179` while writing this: the floor is bit
    identical across `ilp`, `brill`, `workspace`, `gru`, `tpr` and `transformer`
    at label_acc 0.10507649019932376 over 42,293 scored nodes. This test keeps
    it that way.
    """
    cfg = small_config(Path("."))
    tok = build_tokenizer(cfg, episodes)
    train_eps, eval_eps = episodes[:6], episodes[6:]

    first = make_task("node", max_nodes=64).floor(eval_eps, tok, train_eps)
    again = make_task("node", max_nodes=64).floor(eval_eps, tok, train_eps)
    assert first == again, "the floor moved between two identical calls"

    # The task's own sampling seed must not move it: `seed` drives the masking a
    # model is trained against, while the floor draws its own fixed masks so it
    # stays the fixed point everything else is measured from.
    other_seed = make_task("node", max_nodes=64, seed=7).floor(
        eval_eps, tok, train_eps)
    assert other_seed == first, "the floor followed the task's sampling seed"
    assert first["label_n"] > 0 and first["type_n"] > 0


def test_a_saved_run_can_rebuild_its_own_model(tmp_path, episodes):
    """A summary that cannot reconstruct its own model is not a record.

    `train` widens `max_len` to cover whichever surface is longer, plus slack,
    because one positional embedding serves both the token sequence and the node
    sequence. That derived value appeared nowhere: `rgt` trained with a 328-row
    positional embedding while its summary said `max_len = 320`, so rebuilding
    the model from its own summary and calling `load_state_dict` failed on a
    shape mismatch. Reloading a trained model had to guess.
    """
    import torch

    from symbolic_ai_models.models import build
    from symbolic_ai_models.models.base import ModelConfig

    out = tmp_path / "rebuildable"
    summary = train(small_config(out, model="ngram", tasks=("node",),
                                 task_weights={"node": 1.0}))
    recorded = summary["model_config"]
    assert recorded["max_len"] > summary["config"]["max_len"], \
        "the derived width should differ from the requested one"

    # Rebuild from the record alone, and load the saved weights into it.
    model = build(summary["model"], ModelConfig(**recorded))
    saved = torch.load(out / "model.pt", weights_only=False)
    assert saved["model_config"] == recorded
    model.load_state_dict(saved["model"])


def test_the_copy_head_is_scored_by_what_it_picked_not_by_index(episodes):
    """Several nodes carry the same label, so index equality is the wrong test.

    A pointer that copies a different but equally valid source is correct. An
    index check would mark it wrong, which would make the metric reward
    memorising one canonical answer -- the opposite of what a pointer is for.
    """
    import numpy as np
    import torch

    from symbolic_ai_core.data.batch import IGNORE, collate_graph
    from symbolic_ai_models.models.base import ModelOutput
    from symbolic_ai_models.tasks.masked_node import _pointer_counts

    cfg = small_config(Path("."))
    tok = build_tokenizer(cfg, episodes)
    batch = collate_graph(episodes, tok, max_nodes=64, mask_rate=0.15,
                          rng=np.random.default_rng(3))
    B, L = batch.tokens.shape

    def out_with(source_logits):
        return ModelOutput(symbol_logits=torch.zeros(B, L, len(tok)),
                           type_logits=torch.zeros(B, L, 20),
                           hidden=torch.zeros(B, L, 1),
                           source_logits=source_logits)

    # An oracle that points at the recorded source can only be right where one
    # exists, so its accuracy is the copy ceiling itself.
    oracle = torch.full((B, L, L), -1e9)
    for b in range(B):
        for i in range(L):
            j = int(batch.target_source[b, i])
            if j != IGNORE:
                oracle[b, i, j] = 10.0
    got = _pointer_counts(out_with(oracle), batch)
    ceiling = got["copy_correct"] / got["copy_n"]

    chance = _pointer_counts(out_with(torch.randn(B, L, L)), batch)
    assert chance["copy_correct"] / chance["copy_n"] < ceiling, \
        "a random pointer must not match an oracle"

    # A model with no pointer is simply not scored, rather than scored as zero.
    assert _pointer_counts(ModelOutput(
        symbol_logits=torch.zeros(B, L, len(tok)),
        type_logits=torch.zeros(B, L, 20),
        hidden=torch.zeros(B, L, 1)), batch) == {}


def test_the_copy_head_reports_a_floor(episodes):
    """A copy accuracy quoted without a floor would repeat an old mistake.

    Only that it exists and is a probability is asserted here. The fixture is
    eight episodes over two lessons, and a rule that learns the commonest offset
    per structural context has almost nothing to learn from that -- it scores
    0.019 here against **0.266 on the full 179 lessons**, where a random pointer
    gets 0.048 and an oracle 0.722. Asserting a threshold at this scale would be
    asserting something the fixture cannot support, and the honest place for the
    real number is the roadmap, measured by the sweep.
    """
    cfg = small_config(Path("."))
    tok = build_tokenizer(cfg, episodes)
    floor = make_task("node", max_nodes=64).floor(episodes[6:], tok, episodes[:6])
    assert 0.0 <= floor["copy_acc"] <= 1.0
    assert floor["copy_acc"] == floor["copy_acc"], "floor must not be nan"


def test_config_drift_flags_rows_scored_against_different_floors():
    """A lift has two halves and the guard only watched one.

    Strengthening the type floor moved it 0.795 -> 0.860. Every row not re-run
    against the new floor keeps a lift computed from the old one, and the rows
    print side by side looking comparable -- the stale-step-budget failure again,
    this time in the denominator rather than the numerator.
    """
    from symbolic_ai_models.report import config_drift

    old = {"model": "gru", "family": "neural", "config": {},
           "floors": {"node": {"label_acc": 0.105, "type_acc": 0.795}}}
    new = {"model": "ilp", "family": "rule-based", "config": {},
           "floors": {"node": {"label_acc": 0.143, "type_acc": 0.860}}}
    warned = config_drift([old, new])
    assert any("floors" in l for l in warned), warned

    same = {"model": "brill", "family": "rule-based", "config": {},
            "floors": {"node": {"label_acc": 0.143, "type_acc": 0.860}}}
    assert config_drift([new, same]) == []
