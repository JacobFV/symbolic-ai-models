"""The harness end to end: floors, a real (tiny) run, reload, and scoring."""

from __future__ import annotations

import collections
import json
from pathlib import Path

import pytest
import torch

from symbolic_ai_models.agent import evaluate_choices, as_text_agent, score_choices
from symbolic_ai_models.data.curriculum import generate
from symbolic_ai_models.report import comparison_table, load_summaries
from symbolic_ai_models.models import ModelConfig, build
from symbolic_ai_models.tasks import Totals, make_task
from symbolic_ai_models.train import TrainConfig, build_tokenizer, load_run, train

LESSONS = "unification,symbol_grounding,context_free_language"


def small_config(out: Path, **kw) -> TrainConfig:
    base = dict(model="rgt", tasks=("lm", "node"), lessons=LESSONS,
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
    assert TrainConfig.from_dict(summary["config"]).model == "rgt"


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
    assert cfg.model == "rgt"
    batch = make_task("node", max_nodes=64).collate(episodes, tok)
    with torch.no_grad():
        first = model(batch).symbol_logits
        second = model(batch).symbol_logits
    assert torch.allclose(first, second), "eval mode should be deterministic"


def test_single_task_runs_do_not_require_the_other(tmp_path):
    """A model trained only on graphs must not need the text task to exist."""
    summary = train(small_config(tmp_path / "node_only", tasks=("node",),
                                 task_weights={"node": 1.0}))
    assert set(summary["final"]) == {"node"}


def test_comparison_table_reads_finished_runs(finished_run):
    out, _ = finished_run
    table = comparison_table(load_summaries([out]))
    assert "rgt" in table and "lift" in table


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
    from symbolic_ai_models.data.batch import collate_text
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
    from symbolic_ai_models.data.batch import collate_text
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
