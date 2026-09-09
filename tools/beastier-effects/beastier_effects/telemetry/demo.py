"""Synthetic telemetry that walks through every effect for bench testing."""

from __future__ import annotations

import math
import time
from typing import Optional

from .base import Telemetry

PHASES = (
    ("cruise", 4.0),
    ("rumble strip", 3.0),
    ("ABS braking", 3.0),
    ("understeer", 3.0),
    ("idle", 3.0),
    ("redline", 3.0),
)
CYCLE = sum(d for _, d in PHASES)


def phase_at(elapsed: float) -> tuple[str, float]:
    """Return (phase name, seconds into that phase) for a point in the cycle."""
    t = elapsed % CYCLE
    for name, duration in PHASES:
        if t < duration:
            return name, t
        t -= duration
    return PHASES[-1][0], 0.0


def sample(elapsed: float) -> Telemetry:
    name, local = phase_at(elapsed)
    t = Telemetry(active=True, rpm_max=7000.0, rpm_idle=900.0, cylinders=4,
                  throttle=0.3, brake=0.0, gear=3, surface_rumble_front=0.2)
    t.speed_mps = 25.0
    t.rpm = 3500.0
    if name == "cruise":
        t.surface_rumble_front = 0.25 + 0.15 * math.sin(local * 2.0)
    elif name == "rumble strip":
        t.rumble_front = 1.0 if (local % 1.0) < 0.6 else 0.0
    elif name == "ABS braking":
        t.brake = 0.9
        t.throttle = 0.0
        t.speed_mps = max(3.0, 25.0 - local * 6.0)
        t.slip_ratio_front = -0.6
        t.abs_active = True
    elif name == "understeer":
        t.slip_front = 0.8 + local * 0.3
        t.lateral_g = 1.1
    elif name == "idle":
        t.speed_mps = 0.0
        t.rpm = 900.0
        t.throttle = 0.0
    elif name == "redline":
        t.speed_mps = 40.0
        t.rpm = 6800.0
        t.throttle = 1.0
    t.wheel_speed_front_radps = t.speed_mps / 0.33
    return t


class DemoSource:
    name = "demo"

    def __init__(self, rate_hz: float = 60.0):
        self._period = 1.0 / rate_hz
        self._start = time.monotonic()
        self._next = self._start
        self.packets = 0

    def current_phase(self) -> str:
        return phase_at(time.monotonic() - self._start)[0]

    def poll(self) -> Optional[Telemetry]:
        now = time.monotonic()
        if now < self._next:
            return None
        self._next += self._period
        if now - self._next > self._period:  # fell behind, resync
            self._next = now
        self.packets += 1
        return sample(now - self._start)

    def close(self) -> None:
        pass
