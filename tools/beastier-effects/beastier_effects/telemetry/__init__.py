"""Telemetry sources. Each exposes ``poll()`` returning a :class:`Telemetry` or ``None``."""

from .base import Telemetry, TelemetrySource

__all__ = ["Telemetry", "TelemetrySource", "make_source", "SOURCE_NAMES"]

SOURCE_NAMES = ("forza", "assetto", "demo")


def make_source(name: str, port: int = 5300, host: str = "0.0.0.0", slip_scale: float = 1.0):
    if name == "forza":
        from .forza import ForzaSource

        return ForzaSource(port=port, host=host)
    if name == "assetto":
        from .assetto import AssettoSource

        return AssettoSource(slip_scale=slip_scale)
    if name == "demo":
        from .demo import DemoSource

        return DemoSource()
    raise ValueError(f"unknown telemetry source {name!r}; choose from {', '.join(SOURCE_NAMES)}")
