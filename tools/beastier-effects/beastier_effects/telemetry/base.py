"""Game-independent telemetry frame and source interface."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol


@dataclass
class Telemetry:
    """One normalized telemetry sample.

    Slip values follow the Forza convention: 0 is full grip, magnitudes above
    1 mean the tyre is past its peak. ``slip_ratio_front`` is signed; negative
    means the wheel turns slower than the road (braking, lock-up).
    Fields that a source cannot provide are ``None`` so effects can fall back.
    """

    active: bool = False
    speed_mps: float = 0.0
    wheel_speed_front_radps: Optional[float] = None
    rpm: float = 0.0
    rpm_max: float = 0.0
    rpm_idle: float = 0.0
    cylinders: Optional[int] = None
    throttle: Optional[float] = None
    brake: Optional[float] = None
    gear: Optional[int] = None
    slip_front: float = 0.0
    slip_rear: float = 0.0
    slip_ratio_front: float = 0.0
    rumble_front: float = 0.0
    surface_rumble_front: Optional[float] = None
    abs_active: Optional[bool] = None
    lateral_g: float = 0.0


class TelemetrySource(Protocol):
    name: str

    def poll(self) -> Optional[Telemetry]:
        """Return the newest sample since the last call, or None if nothing arrived."""

    def close(self) -> None: ...
