"""Proving the answer insensitive, instead of checking every candidate.

Enumerating the candidate worlds costs sixteen flow solves; proving the answer
cannot change costs one DFS per edge. Flood admits that because **deleting a link
is monotone** -- it removes routes and never creates them -- so a vehicle that
cannot qualify cannot be made to qualify, and only the qualifying ones need
proving.

Two certificates live here.

`certifies_insensitive` takes a world and asks whether any single link deletion
could change the answer. It **reads the roles** to build its graph, so on a world
whose depot was guessed it certifies the wrong question -- measured 2026-08-19,
that is exactly how a role error slipped past it.

`certifies_role_independent` consumes no guessed role: it requires every candidate
assignment the reader could not settle to certify, and requires them to agree.
Sound at 0 wrong over 123 answers, where the collapsed form let one through.

Moved here from ``scripts/`` on 2026-08-19: it had become load-bearing across
four findings while living in a script.
"""

from __future__ import annotations

from symbolic_ai_core.world import Quantity

__all__ = ["certifies_insensitive", "certifies_role_independent"]


def _read_world(world):
    """The pieces the certificate needs, straight off the claims."""
    links, limits, flooded = [], {}, set()
    mass, capacity, bridge_of = {}, {}, {}
    depot = needs = None
    demand = None
    for c in world.claims:
        p, q = c.predicate, c.roles.get("value")
        if p == "link":
            links.append(tuple(c.entities()))
        elif p == "bridge_on":
            bridge_of[c.roles["via"].id] = (c.roles["a"].id, c.roles["b"].id)
        elif p == "load_limit" and isinstance(q, Quantity):
            limits[c.roles["of"].id] = float(q.value)
        elif p == "flooded":
            flooded.add(c.roles["where"].id)
        elif p == "mass" and isinstance(q, Quantity):
            mass[c.roles["of"].id] = float(q.value)
        elif p == "capacity" and isinstance(q, Quantity):
            capacity[c.roles["of"].id] = float(q.value)
        elif p == "depot":
            depot = c.roles["where"].id
        elif p == "needs":
            needs = c.roles["where"].id
        elif p == "demand" and isinstance(q, Quantity):
            demand = float(q.value)
    edge_limit = {}
    for via, pair in bridge_of.items():
        if via in limits:
            edge_limit[frozenset(pair)] = limits[via]
    return {"links": links, "edge_limit": edge_limit, "flooded": flooded,
            "mass": mass, "capacity": capacity, "depot": depot,
            "needs": needs, "demand": demand}


def _connected(edges, a, b) -> bool:
    if a is None or b is None:
        return False
    adj: dict = {}
    for x, y in edges:
        adj.setdefault(x, []).append(y)
        adj.setdefault(y, []).append(x)
    seen, stack = {a}, [a]
    while stack:
        cur = stack.pop()
        if cur == b:
            return True
        for nxt in adj.get(cur, ()):
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    return False


def certifies_insensitive(world) -> bool:
    """True if no single link deletion can change any vehicle's status."""
    w = _read_world(world)
    if w["depot"] is None or w["needs"] is None or w["demand"] is None:
        return False
    if w["depot"] in w["flooded"] or w["needs"] in w["flooded"]:
        return False
    for vid, m in w["mass"].items():
        cap = w["capacity"].get(vid)
        if cap is None or cap < w["demand"]:
            continue                      # cannot qualify; monotone, so safe
        threshold = m + w["demand"]
        usable = [e for e in w["links"]
                  if e[0] not in w["flooded"] and e[1] not in w["flooded"]
                  and w["edge_limit"].get(frozenset(e), float("inf"))
                  >= threshold]
        if not _connected(usable, w["depot"], w["needs"]):
            continue                      # does not qualify; safe for free
        # qualifies: every single edge removal must leave it connected
        for i in range(len(usable)):
            rest = usable[:i] + usable[i + 1:]
            if not _connected(rest, w["depot"], w["needs"]):
                return False
    return True


def certifies_role_independent(text: str, solve, *, anchors=None) -> bool:
    """Insensitive under **every** role assignment the reader left open.

    `certifies_insensitive` builds its graph from the roles, so it inherits their
    errors: on a world whose depot is wrong it answers the right question about
    the wrong graph. This consumes no guess -- every candidate assignment must
    certify, and they must agree on the answer.

    Seed 83 is the worked example. Its two wrong-depot candidates certify and the
    **true** one does not, so requiring all of them refuses a case that agreement
    alone admits.

    Measured over 252 non-empty cases on the interleaved hard-distractor surface:
    0 wrong at 48.8% coverage, against 47.6% for the pairing that needs the role
    flag as a precondition. The coverage gain is marginal; what it buys is a
    check that needs no precondition.
    """
    from symbolic_ai_generators.flood.read_surface import \
        read_content_roles_worlds

    worlds = read_content_roles_worlds(text, anchors=anchors)
    answers = set()
    for w in worlds:
        if not certifies_insensitive(w):
            return False
        try:
            answers.add(solve(w)[0])
        except Exception:
            return False
    return len(answers) == 1
