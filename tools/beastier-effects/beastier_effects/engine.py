"""Turns telemetry into a DirectControl frame, one call per output tick."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from .config import EffectConfig
from .protocol import DirectControl, clamp
from .telemetry.base import Telemetry

TWO_PI = 2.0 * math.pi
DEFAULT_TYRE_RADIUS_M = 0.33


def ramp(value: float, start: float, full: float) -> float:
    """0 at ``start``, 1 at ``full``, linear between, works for either direction."""
    if full == start:
        return 1.0 if (value >= start if full > start else value <= start) else 0.0
    return clamp((value - start) / (full - start), 0.0, 1.0)


class Envelope:
    """First-order attack/release smoother so amplitudes never step."""

    def __init__(self, attack_s: float, release_s: float):
        self.attack_s = attack_s
        self.release_s = release_s
        self.value = 0.0

    def step(self, target: float, dt: float) -> float:
        tau = self.attack_s if target > self.value else self.release_s
        if tau <= 0.0 or dt <= 0.0:
            self.value = target
        else:
            alpha = 1.0 - math.exp(-dt / tau)
            self.value += (target - self.value) * alpha
        return self.value


class Oscillator:
    def __init__(self) -> None:
        self.phase = 0.0

    def sample(self, freq_hz: float, dt: float) -> float:
        self.phase = (self.phase + TWO_PI * freq_hz * dt) % TWO_PI
        return math.sin(self.phase)


@dataclass
class EngineStatus:
    """What the engine did on the last tick, for the CLI status line."""

    active: bool = False
    periodic_peak: float = 0.0
    force_drop: float = 0.0
    constant: float = 0.0
    effects: dict[str, float] = field(default_factory=dict)


class EffectEngine:
    def __init__(self, cfg: EffectConfig):
        self.cfg = cfg
        self._env = {
            name: Envelope(cfg.attack_s, cfg.release_s)
            for name in ("texture", "rumble", "abs", "engine", "drop", "oversteer")
        }
        self._osc = {name: Oscillator() for name in ("texture", "rumble", "abs", "engine")}
        self.status = EngineStatus()

    def _wheel_hz(self, t: Telemetry) -> float:
        if t.wheel_speed_front_radps is not None and t.wheel_speed_front_radps > 0.0:
            return t.wheel_speed_front_radps / TWO_PI
        return t.speed_mps / (TWO_PI * DEFAULT_TYRE_RADIUS_M)

    def update(self, t: Optional[Telemetry], dt: float) -> DirectControl:
        cfg = self.cfg
        active = t is not None and t.active
        if t is None:
            t = Telemetry()
        periodic = 0.0
        drop_target = 0.0
        constant_target = 0.0
        effects: dict[str, float] = {}

        # Road texture
        tex = cfg.texture
        amp = 0.0
        freq = tex.min_hz
        if active and tex.enabled and t.speed_mps >= tex.speed_floor_mps:
            if t.surface_rumble_front is not None:
                amp = tex.gain * clamp(t.surface_rumble_front * tex.surface_scale, 0.0, 1.0)
            else:
                amp = tex.gain * tex.fallback_fraction * clamp(
                    t.speed_mps / tex.fallback_full_speed_mps, 0.0, 1.0)
            freq = clamp(self._wheel_hz(t) * tex.bumps_per_rev, tex.min_hz, tex.max_hz)
        level = self._env["texture"].step(amp, dt)
        periodic += level * self._osc["texture"].sample(freq, dt)
        effects["texture"] = level

        # Rumble strip
        rum = cfg.rumble
        amp = 0.0
        freq = rum.min_hz
        if active and rum.enabled and t.rumble_front > 0.0:
            amp = rum.gain * clamp(t.rumble_front, 0.0, 1.0)
            freq = clamp(t.speed_mps / rum.spacing_m, rum.min_hz, rum.max_hz)
        level = self._env["rumble"].step(amp, dt)
        periodic += level * self._osc["rumble"].sample(freq, dt)
        effects["rumble"] = level

        # ABS
        ab = cfg.abs
        amp = 0.0
        braking = t.brake is not None and t.brake >= ab.brake_threshold
        if active and ab.enabled:
            abs_on = t.abs_active if t.abs_active is not None else (
                braking and t.slip_ratio_front <= ab.slip_ratio_threshold)
            if abs_on:
                amp = ab.gain
                drop_target += ab.force_drop
        level = self._env["abs"].step(amp, dt)
        periodic += level * self._osc["abs"].sample(ab.hz, dt)
        effects["abs"] = level

        # Lock-up
        lk = cfg.lockup
        if active and lk.enabled and t.brake is not None and t.brake >= lk.brake_threshold:
            d = lk.max_drop * ramp(t.slip_ratio_front, lk.slip_ratio_start, lk.slip_ratio_full)
            drop_target += d
            effects["lockup"] = d

        # Understeer
        us = cfg.understeer
        if active and us.enabled:
            d = us.max_drop * ramp(t.slip_front, us.slip_start, us.slip_full)
            drop_target += d
            effects["understeer"] = d

        # Engine vibration
        en = cfg.engine
        amp = 0.0
        freq = en.min_hz
        if active and en.enabled and t.rpm > 0.0 and t.rpm_max > 0.0:
            idle = t.rpm_idle if t.rpm_idle > 0.0 else 0.12 * t.rpm_max
            idle_level = 1.0 - ramp(t.rpm, idle, idle * (1.0 + en.idle_band))
            red_level = ramp(t.rpm, t.rpm_max * (1.0 - en.redline_band), t.rpm_max)
            amp = en.gain * max(idle_level, red_level)
            cyl = t.cylinders or en.default_cylinders
            freq = clamp(t.rpm / 60.0 * cyl / 2.0, en.min_hz, en.max_hz)
        level = self._env["engine"].step(amp, dt)
        periodic += level * self._osc["engine"].sample(freq, dt)
        effects["engine"] = level

        # Oversteer cue (opt in)
        ov = cfg.oversteer
        if active and ov.enabled:
            level = ov.gain * ramp(t.slip_rear, ov.slip_start, ov.slip_full)
            direction = -1.0 if t.lateral_g > 0.0 else 1.0 if t.lateral_g < 0.0 else 0.0
            constant_target = ov.sign * direction * level
            effects["oversteer"] = level

        drop = self._env["drop"].step(clamp(drop_target, 0.0, cfg.max_total_drop), dt)
        constant = self._env["oversteer"].step(constant_target, dt)

        periodic = clamp(periodic * cfg.total_gain, -1.0, 1.0)
        constant = clamp(constant * cfg.total_gain, -1.0, 1.0)

        self.status = EngineStatus(active=active, periodic_peak=sum(
            v for k, v in effects.items() if k in ("texture", "rumble", "abs", "engine")) * cfg.total_gain,
            force_drop=drop, constant=constant, effects=effects)
        return DirectControl(spring=0.0, constant=constant, periodic=periodic, force_drop=drop)
