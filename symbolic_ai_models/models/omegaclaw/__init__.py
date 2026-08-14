"""The OmegaClaw substrate. Nothing here is registered; the subclasses are."""

from .base import CLAWS, Claim, Claw, OmegaClaw, Scan, Weighted
from .surface import SURFACE_CLAWS, TEXT_CLAWS, Surface, surface_of

__all__ = ["OmegaClaw", "Claim", "Claw", "Scan", "Weighted", "CLAWS",
           "SURFACE_CLAWS", "TEXT_CLAWS", "Surface", "surface_of"]
