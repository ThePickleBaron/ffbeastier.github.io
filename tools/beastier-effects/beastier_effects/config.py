"""Effect configuration with defaults and TOML overrides."""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any


@dataclass
class TextureConfig:
    """Road texture: a periodic tied to wheel rotation."""

    enabled: bool = True
    gain: float = 0.06
    bumps_per_rev: float = 6.0
    min_hz: float = 6.0
    max_hz: float = 60.0
    speed_floor_mps: float = 2.0
    surface_scale: float = 1.0
    fallback_fraction: float = 0.5
    fallback_full_speed_mps: float = 30.0


@dataclass
class RumbleConfig:
    """Rumble strips / kerbs under the front wheels."""

    enabled: bool = True
    gain: float = 0.35
    spacing_m: float = 0.12
    min_hz: float = 10.0
    max_hz: float = 80.0


@dataclass
class AbsConfig:
    enabled: bool = True
    gain: float = 0.25
    hz: float = 15.0
    force_drop: float = 0.15
    slip_ratio_threshold: float = -0.35
    brake_threshold: float = 0.15


@dataclass
class LockupConfig:
    enabled: bool = True
    slip_ratio_start: float = -0.5
    slip_ratio_full: float = -1.0
    max_drop: float = 0.5
    brake_threshold: float = 0.15


@dataclass
class UndersteerConfig:
    enabled: bool = True
    slip_start: float = 0.85
    slip_full: float = 1.6
    max_drop: float = 0.45


@dataclass
class EngineConfig:
    enabled: bool = True
    gain: float = 0.02
    idle_band: float = 0.15
    redline_band: float = 0.10
    min_hz: float = 10.0
    max_hz: float = 70.0
    default_cylinders: int = 4


@dataclass
class OversteerConfig:
    """Counter-steer cue from rear slip. Off until the sign is verified on the rig."""

    enabled: bool = False
    gain: float = 0.2
    slip_start: float = 0.9
    slip_full: float = 1.8
    sign: int = 1


@dataclass
class EffectConfig:
    total_gain: float = 0.5
    max_total_drop: float = 0.7
    attack_s: float = 0.03
    release_s: float = 0.08
    rate_hz: float = 200.0
    telemetry_timeout_s: float = 0.5
    texture: TextureConfig = field(default_factory=TextureConfig)
    rumble: RumbleConfig = field(default_factory=RumbleConfig)
    abs: AbsConfig = field(default_factory=AbsConfig)
    lockup: LockupConfig = field(default_factory=LockupConfig)
    understeer: UndersteerConfig = field(default_factory=UndersteerConfig)
    engine: EngineConfig = field(default_factory=EngineConfig)
    oversteer: OversteerConfig = field(default_factory=OversteerConfig)


def _apply(target: Any, data: dict[str, Any], path: str = "") -> None:
    known = {f.name: f for f in fields(target)}
    for key, value in data.items():
        if key not in known:
            raise ValueError(f"unknown config key {path + key!r}")
        current = getattr(target, key)
        if is_dataclass(current):
            if not isinstance(value, dict):
                raise ValueError(f"{path + key!r} must be a table")
            _apply(current, value, path + key + ".")
        else:
            expected = type(current)
            if expected is float and isinstance(value, int) and not isinstance(value, bool):
                value = float(value)
            if expected is int and isinstance(value, bool):
                raise ValueError(f"{path + key!r} must be an integer")
            if not isinstance(value, expected):
                raise ValueError(
                    f"{path + key!r} must be {expected.__name__}, got {type(value).__name__}"
                )
            setattr(target, key, value)


def config_from_dict(data: dict[str, Any]) -> EffectConfig:
    cfg = EffectConfig()
    _apply(cfg, data)
    return cfg


def load_config(path: str | Path | None) -> EffectConfig:
    if path is None:
        return EffectConfig()
    import tomllib

    with open(path, "rb") as fh:
        return config_from_dict(tomllib.load(fh))


def config_to_dict(cfg: EffectConfig) -> dict[str, Any]:
    return dataclasses.asdict(cfg)
