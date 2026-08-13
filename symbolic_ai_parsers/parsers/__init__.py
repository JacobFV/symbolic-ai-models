"""Importing this package registers every parser."""

from . import bracket, legacy, prior, retrieve, template  # noqa: F401

__all__ = ["bracket", "legacy", "prior", "retrieve", "template"]
