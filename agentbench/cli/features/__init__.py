"""Registered command features exposed by the AgentBench CLI."""

from .base import CommandFeature
from .certify import FEATURE as CERTIFY_FEATURE
from .run import FEATURE as RUN_FEATURE
from .view import FEATURE as VIEW_FEATURE

FEATURES: tuple[CommandFeature, ...] = (
    RUN_FEATURE,
    VIEW_FEATURE,
    CERTIFY_FEATURE,
)

__all__ = ["FEATURES", "CommandFeature"]
