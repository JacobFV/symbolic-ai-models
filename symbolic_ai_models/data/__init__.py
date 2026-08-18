"""Deprecated. The episode types moved to :mod:`symbolic_ai_core.data`.

``Episode``, ``TermGraph``, ``SymbolTokenizer`` and the batch/curriculum plumbing are
shared by every package here — 24 of the 25 cross-package imports were one of
those three types — so they now live in ``symbolic_ai_core`` and this package
holds re-export shims at the old paths.

Kept rather than deleted because ``symbolic_ai_agents`` on the ``omegaclaw``
branch was written against ``symbolic_ai_models.data.*`` and would otherwise
break on merge. Import from :mod:`symbolic_ai_core.data` in anything new. Each
shim re-exports its module's ``__all__`` and nothing private; ``python -m
symbolic_ai_core.data.fingerprint`` is the fingerprint entry point.
"""
