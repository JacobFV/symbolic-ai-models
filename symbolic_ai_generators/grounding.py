"""What the grounding contract shares across domains, and what it cannot.

Three renderers now exist. The contract is the same in all of them -- the
structured answer is canonical, the paragraph is downstream, and unsupported or
contradictory assertions are caught mechanically -- but the solvency finding
concluded that *no line of code* transfers, only the idea.

That was drawn from two domains with different answer types. With a third, the
sharper statement is:

> **The contradiction check is reusable within an ANSWER TYPE, parameterised by
> the verdict wording. It is not reusable across answer types.**

A boolean verdict needs only the two phrases that assert it either way, which is
what :func:`boolean_contradiction` takes. A **set** verdict -- flood's vehicles --
needs per-element polarity and cannot use this at all, which is why flood keeps
its own.

The other two checks stay domain-specific by nature. Token grounding needs the
domain's entity and quantity vocabulary, and the middle relational check is
different every time: route **adjacency** in flood, **date** validity in
solvency, **capability** validity in scheduling.
"""

from __future__ import annotations

__all__ = ["boolean_contradiction"]


def boolean_contradiction(text: str, structured: bool, *,
                          yes: str, no: str) -> list[str]:
    """Complaints if ``text`` disagrees with a boolean ``structured`` verdict.

    ``yes`` and ``no`` are the phrases that assert the verdict either way. They
    are the only domain-specific part, which is the point: this is the whole of
    what transfers between two boolean-answer domains.
    """
    said_yes, said_no = yes in text, no in text
    if said_yes and said_no:
        return ["the paragraph asserts the verdict both ways"]
    if said_yes != bool(structured):
        return [f"paragraph asserts {yes!r} is "
                f"{'true' if said_yes else 'false'}, but the structured "
                f"verdict is {structured}"]
    return []
