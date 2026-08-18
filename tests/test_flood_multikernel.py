"""The first task in this repo that three kernels solve and none of them can.

This is the gate the architecture note set: at least two kernels operating on
overlapping profiles of one entity, one kernel's output changing another's
through explicit coupling, every output arising from one flow DAG, and a task
that cannot be answered by copying from the text.

The agreement number is measured against a **brute-force oracle that shares no
code with the kernels**. An oracle built from the same machinery would agree by
construction, which is the same defect as a floor fitted with the model's own
features.
"""

from __future__ import annotations

import pytest

from symbolic_ai_core.flow import Context, FlowError, compile_flow
from symbolic_ai_generators.flood import generate, solution_by_search
from symbolic_ai_generators.flood.flow import build_flow, solve

pytest.importorskip("clingo")
pytest.importorskip("z3")

#: Small enough to stay a unit test, large enough that agreement is not luck.
SEEDS = range(24)


@pytest.fixture(scope="module")
def cases():
    return [generate(s) for s in SEEDS]


# --- the gate -------------------------------------------------------------
def test_the_whole_task_is_one_acyclic_flow_graph(cases):
    compiled = compile_flow(build_flow(cases[0].world))
    assert compiled.order[0] == "world"
    assert set(compiled.order) == {"world", "reach", "world2", "routes",
                                   "loads", "fused"}


def test_the_world_it_reasons_about_is_cyclic(cases):
    """The thing the flow DAG refuses and the world IR exists to hold."""
    c = cases[0]
    ring = {tuple(sorted((c.regions[i], c.regions[(i + 1) % len(c.regions)])))
            for i in range(len(c.regions))}
    assert ring <= set(c.links), "the road network is not a ring"
    assert c.world.neighbours(c.regions[0]), "no relations to traverse"


def test_three_kernels_run_and_each_does_something_the_others_cannot(cases):
    _, outs, _ = solve(cases[0].world)
    dl = outs["projection_datalog"].value
    asp = outs["projection_asp"].value
    assert dl["kernel"] == "datalog@1" and asp["kernel"] == "asp@1"
    # datalog discards exactly what SMT is for
    assert any("Quantity" in d["why"] for d in dl["discarded"]), (
        "the relational projection kept the load limits, so SMT is redundant")
    assert outs["load_report"].value["n_smt_calls"] > 0


def test_kernels_share_profiles_on_one_entity(cases):
    """A vehicle carries scene.body for the physical view and logic.constraint
    for the solver view, on one identity, without duplication."""
    truck = cases[0].world.entity("truck_0")
    assert truck.has("scene.body", "logic.constraint")
    assert truck.profiles() == ("logic.constraint", "scene.body")


def test_the_coupling_is_real_datalog_to_asp(cases):
    """Removing datalog's contribution changes ASP's answer set, which is what
    'one kernel's output changes another kernel's result' means."""
    changed = 0
    for c in cases:
        full, _, _ = solve(c.world)
        ablated, _, _ = solve(c.world, ignore_flooding=True)
        changed += full != ablated
    assert changed > 0, "routing over raw links gave the same answer every time"


def test_the_coupling_is_real_asp_to_smt(cases):
    """The SMT constraints are built from ASP's routes: keeping only the first
    route changes the answer, so the route set is load-bearing."""
    changed = sum(solve(c.world)[0] != solve(c.world, first_route_only=True)[0]
                  for c in cases)
    assert changed > 0


# --- the number -----------------------------------------------------------
def test_the_flow_agrees_with_an_independent_brute_force_oracle(cases):
    disagree = [(c.seed, solve(c.world)[0], c.answer) for c in cases
                if solve(c.world)[0] != c.answer]
    assert not disagree, disagree


def test_the_oracle_shares_no_code_with_the_kernels(cases):
    """Guards the test above from being a tautology."""
    import inspect

    from symbolic_ai_generators.flood import world as W
    src = inspect.getsource(W.solution_by_search) + inspect.getsource(W._routes)
    for forbidden in ("clingo", "z3", "datalog", "get_kernel", "evaluate("):
        assert forbidden not in src, f"the oracle reaches for {forbidden}"


def test_every_ablation_is_worse_than_the_whole(cases):
    def acc(**kw):
        return sum(solve(c.world, **kw)[0] == c.answer for c in cases) / len(cases)

    full = acc()
    assert full == 1.0
    assert acc(ignore_bridge_limits=True) < full
    assert acc(ignore_flooding=True) < full
    assert acc(first_route_only=True) < full


def test_the_best_floor_is_well_below_the_flow(cases):
    """The strongest non-reasoning rule available: capacity plus the laden mass
    against the *most permissive* bridge, ignoring the network entirely."""
    def floor(c):
        return tuple(sorted(
            v for v, (m, cap) in c.vehicles.items()
            if cap >= c.demand_kg and m + c.demand_kg <= max(c.bridges.values())))

    hit = sum(floor(c) == c.answer for c in cases) / len(cases)
    assert hit < 0.75, f"the floor scores {hit}; the task has little in it"


# --- what the text does and does not say ---------------------------------
def test_the_report_never_states_the_answer(cases):
    for c in cases:
        for vid in c.vehicles:
            assert f"{vid} can" not in c.report
            assert f"dispatch {vid}" not in c.report.lower()
        assert "can_serve" not in c.report


def test_the_deciding_facts_are_in_different_paragraphs(cases):
    """No single paragraph contains flooding, limits and masses together."""
    for c in cases[:4]:
        for para in c.report.split("\n\n"):
            has_flood = "closed" in para
            has_limit = "posted at" in para
            has_mass = "unladen mass" in para
            assert sum((has_flood, has_limit, has_mass)) <= 1


# --- honesty of the trace -------------------------------------------------
def test_the_trace_prices_every_node_and_says_how(cases):
    _, _, ctx = solve(cases[0].world, ctx=Context())
    assert len(ctx.trace.runs) == 6
    assert ctx.trace.total_usd > 0.0
    assert ctx.trace.unpriced == 0
    # The three kernel-bearing nodes price themselves from the kernels they ran;
    # the three plumbing nodes carry only a CPU floor, and the trace says which
    # is which so a total can never quietly mix them.
    assert ctx.trace.cpu_only == 3
    self_priced = {r.node for r in ctx.trace.runs if r.priced_from == "node"}
    assert self_priced == {"reach", "routes", "loads"}


def test_cpu_and_wall_are_recorded_separately_per_node(cases):
    _, _, ctx = solve(cases[0].world, ctx=Context())
    assert all(r.cpu_ns > 0 and r.wall_ns > 0
               for r in ctx.trace.runs if not r.skipped and not r.cached)


def test_pricing_can_be_turned_off_for_self_reported_costs_only(cases):
    ctx = Context(price_cpu=False)
    solve(cases[0].world, ctx=ctx)
    assert ctx.trace.unpriced == 3, (
        "with CPU pricing off, the plumbing nodes must read as unpriced rather "
        "than free")


def test_re_running_the_same_case_hits_the_cache(cases):
    ctx = Context()
    solve(cases[0].world, ctx=ctx)
    n = len(ctx.trace.runs)
    solve(cases[0].world, ctx=ctx)
    second = ctx.trace.runs[n:]
    assert all(r.cached for r in second), "an unchanged graph recomputed"


def test_generation_is_a_pure_function_of_its_seed():
    a, b = generate(7), generate(7)
    assert a.world.to_dict() == b.world.to_dict()
    assert a.report == b.report and a.answer == b.answer


def test_the_oracle_is_not_degenerate(cases):
    sizes = {len(c.answer) for c in cases}
    assert len(sizes) >= 3, f"the answer takes only {sizes}; no signal"


# --- the reader, and what fidelity the pipeline needs ---------------------
def test_the_template_reader_recovers_the_world_exactly(cases):
    """Everything the fidelity curve says rests on p=0 being lossless."""
    from symbolic_ai_generators.flood.read import read_report

    for c in cases:
        got, _, _ = solve(read_report(c.report))
        assert tuple(got) == tuple(c.answer), c.seed


def test_dropping_a_domain_fact_hurts_more_than_dropping_a_constraint(cases):
    """The prediction that failed, pinned. Constraints are often non-binding;
    a vehicle whose mass went missing can no longer be named at all."""
    from symbolic_ai_generators.flood.read import corrupt, read_report

    worlds = [read_report(c.report) for c in cases]

    def acc(kind):
        hit = 0
        for i, (c, w) in enumerate(zip(cases, worlds)):
            try:
                got, _, _ = solve(corrupt(w, seed=i, rate=0.35, kinds=[kind]))
            except Exception:
                got = ()
            hit += tuple(got) == tuple(c.answer)
        return hit / len(cases)

    domain = min(acc("mass"), acc("capacity"))
    constraint = min(acc("flooded"), acc("load_limit"))
    assert domain < constraint, (
        f"domain facts {domain:.2f} were not more damaging than constraints "
        f"{constraint:.2f}; the mechanism in the finding does not hold here")


def test_the_pipeline_degrades_to_the_trivial_floor_and_not_below(cases):
    from symbolic_ai_generators.flood.read import corrupt, read_report

    worlds = [read_report(c.report) for c in cases]
    hit = 0
    for i, (c, w) in enumerate(zip(cases, worlds)):
        try:
            got, _, _ = solve(corrupt(w, seed=i, rate=0.9))
        except Exception:
            got = ()
        hit += tuple(got) == tuple(c.answer)
    trivial = sum(c.answer == () for c in cases) / len(cases)
    assert hit / len(cases) <= trivial + 0.1, (
        "heavy corruption scored above the always-none floor, so the "
        "corruption is doing something other than removing information")


def test_precision_errors_hurt_less_than_recall_errors(cases):
    """The prediction that failed. A wrong number leaves the vehicle in the
    domain; a missed sentence removes it."""
    from symbolic_ai_generators.flood.read import corrupt, misread, read_report

    worlds = [read_report(c.report) for c in cases]

    def acc(fn):
        hit = 0
        for i, (c, w) in enumerate(zip(cases, worlds)):
            try:
                got, _, _ = solve(fn(i, w))
            except Exception:
                got = ()
            hit += tuple(got) == tuple(c.answer)
        return hit / len(cases)

    recall = acc(lambda i, w: corrupt(w, seed=i, rate=0.20))
    precision = acc(lambda i, w: misread(w, seed=i, rate=0.20))
    assert precision > recall, (
        f"precision {precision:.2f} did not beat recall {recall:.2f}; the "
        f"domain-vs-constraint mechanism does not hold here")


def test_the_conservative_penalty_grows_with_connectivity(cases):
    """The mechanism that survived, and it is not the one first proposed.

    Single-viable-route fragility was the first explanation and its own control
    killed it: the conservative-vs-permissive gap is *nil* at zero chords, where
    every qualifying vehicle sits on exactly one route, and largest at six,
    where almost none does. What actually moves is the answer's size -- a
    conservative error can only damage a positive, and there are more of them in
    a better-connected world.

    Bridges are pinned so the sweep does not also sweep how many limits there
    are to misread; that confound ate the first version of this result.
    """
    from symbolic_ai_generators.flood.read import misread, read_report

    def gap(chords):
        cs = [generate(s, n_chords=chords, n_bridges=4)
              for s in range(len(cases))]
        ws = [read_report(c.report) for c in cs]

        def acc(direction):
            hit = 0
            for i, (c, w) in enumerate(zip(cs, ws)):
                try:
                    got, _, _ = solve(misread(w, seed=i, rate=0.20,
                                              direction=direction))
                except Exception:
                    got = ()
                hit += tuple(got) == tuple(c.answer)
            return hit / len(cs)

        return acc("permissive") - acc("conservative"), cs

    wide, wide_cases = gap(6)
    narrow, narrow_cases = gap(0)
    assert wide > narrow, (
        f"the gap did not grow with connectivity ({narrow:.3f} -> {wide:.3f}); "
        f"the surviving mechanism does not hold here")
    assert (sum(len(c.answer) for c in wide_cases)
            > sum(len(c.answer) for c in narrow_cases)), (
        "the quantity the mechanism rests on -- more positives when better "
        "connected -- did not move")


def test_being_admitted_is_less_redundant_than_being_blocked(cases):
    """The count the refuted mechanism rested on. Kept because the count is
    real and is still the reason PERMISSIVE errors are mild; what it does not
    explain is why conservative errors are harsh."""
    import statistics

    from symbolic_ai_generators.flood.world import _routes

    viable, blocking = [], []
    for c in cases:
        routes = list(_routes(c.regions, c.links, c.flooded, c.depot,
                              c.demand_site))
        for v, (mass, cap) in c.vehicles.items():
            if cap < c.demand_kg:
                continue
            laden = mass + c.demand_kg
            ok = blocks = 0
            for path in routes:
                lims = [c.bridges[tuple(sorted(e))]
                        for e in zip(path, path[1:])
                        if tuple(sorted(e)) in c.bridges]
                if all(laden <= l for l in lims):
                    ok += 1
                else:
                    blocks += sum(laden > l for l in lims)
            (viable if ok else blocking).append(ok or blocks)

    assert viable and blocking
    assert statistics.median(viable) <= statistics.median(blocking), (
        "a qualifying vehicle had more redundancy than a blocked one, so the "
        "conservative-worse-than-permissive result has no mechanism")


# --- routing: what skipping the solvers is worth --------------------------
def test_the_gate_is_lossless(cases):
    """Both gates are provably sufficient, so routing must not change a single
    answer. The first version of this test failed at 39/300 and found a real
    bug: the cheap arm defaulted `reachable=True` and answered on unreachable
    worlds."""
    for c in cases:
        base, _, _ = solve(c.world, ctx=Context())
        routed, _, _ = solve(c.world, ctx=Context(), routed=True)
        assert base == routed, c.seed


def test_the_gate_actually_fires_sometimes(cases):
    """A gate that never fires is lossless for the wrong reason."""
    fired = sum(solve(c.world, ctx=Context(), routed=True)[1]["decision"]
                .value["chosen"] == ["cheap"] for c in cases)
    assert fired > 0, "the escalation never took the cheap arm"


def test_the_skipped_branch_carries_the_reason(cases):
    """A router's decision belongs in the trace, not in a predicate somewhere."""
    for c in cases:
        _, outs, ctx = solve(c.world, ctx=Context(), routed=True)
        chosen = outs["decision"].value["chosen"]
        skipped = {r.node for r in ctx.trace.runs if r.skipped}
        if chosen == ["cheap"]:
            assert {"routes", "loads"} <= skipped
        else:
            assert "cheap" in skipped
        assert all(r.note for r in ctx.trace.runs if r.skipped)


def test_routing_never_costs_more_than_it_saves(cases):
    """The gate is arithmetic over facts already on the table. If it were not
    cheaper than what it gates, routing would be a loss."""
    base = sum(solve(c.world, ctx=Context())[2].trace.total_usd for c in cases)
    routed = sum(solve(c.world, ctx=Context(), routed=True)[2].trace.total_usd
                 for c in cases)
    assert routed < base


def test_cheap_and_incapable_is_not_a_point_on_the_cost_curve(cases):
    """The measured form of the argument symbolic_ai_core/cost.py was written
    after: a cost saving that costs capability is a LOSS on $/solved-above-floor,
    however large the saving."""
    floor = 0.440

    def arm(**kw):
        hit = usd = 0.0
        for c in cases:
            ans, _, ctx = solve(c.world, ctx=Context(), **kw)
            hit += tuple(ans) == tuple(c.answer)
            usd += ctx.trace.total_usd
        acc = hit / len(cases)
        return acc, usd / len(cases)

    full_acc, full_usd = arm()
    cut_acc, cut_usd = arm(ignore_bridge_limits=True)

    # The precondition is asserted STRUCTURALLY, not by timing. An earlier
    # version used `cut_usd < full_usd`, which is true and small enough that CPU
    # measurement under load inverts it -- it passed alone and failed in a full
    # run. The ablation skipping solver work is countable and does not move.
    calls = [outs["load_report"].value["n_smt_calls"]
             for outs in (solve(c.world, ctx=Context())[1] for c in cases)]
    cut_calls = [outs["load_report"].value["n_smt_calls"]
                 for outs in (solve(c.world, ctx=Context(),
                                    ignore_bridge_limits=True)[1]
                              for c in cases)]
    assert sum(cut_calls) <= sum(calls), "the ablation did not skip any work"
    assert cut_acc < full_acc

    # This one IS robust to timing: the cheap arm's lift is ~5.8x smaller, and
    # it still runs datalog and ASP, so its cost cannot fall by the factor that
    # would be needed to win.
    assert (cut_usd / max(cut_acc - floor, 1e-9)) > (full_usd / (full_acc - floor)), (
        "the cheaper arm won on $/solved-above-floor, which would make the "
        "north star reward incapability")
