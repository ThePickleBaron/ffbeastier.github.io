import math

import pytest

from beastier_effects.config import EffectConfig, config_from_dict
from beastier_effects.engine import EffectEngine, Envelope, ramp
from beastier_effects.telemetry.base import Telemetry

DT = 1.0 / 200.0


def run(engine, telemetry, seconds):
    frames = []
    for _ in range(int(seconds / DT)):
        frames.append(engine.update(telemetry, DT))
    return frames


def cruising(**kw):
    t = Telemetry(active=True, speed_mps=25.0, wheel_speed_front_radps=75.0,
                  rpm=3500.0, rpm_max=7000.0, rpm_idle=900.0, cylinders=4,
                  throttle=0.3, brake=0.0, surface_rumble_front=0.0)
    for k, v in kw.items():
        setattr(t, k, v)
    return t


def test_ramp():
    assert ramp(0.0, 0.85, 1.6) == 0.0
    assert ramp(1.6, 0.85, 1.6) == 1.0
    assert ramp(1.225, 0.85, 1.6) == pytest.approx(0.5)
    # reversed direction (lock-up: more negative is "more")
    assert ramp(-0.5, -0.5, -1.0) == 0.0
    assert ramp(-1.0, -0.5, -1.0) == 1.0
    assert ramp(-0.75, -0.5, -1.0) == pytest.approx(0.5)


def test_envelope_smooths_and_converges():
    env = Envelope(0.03, 0.08)
    first = env.step(1.0, DT)
    assert 0.0 < first < 1.0
    for _ in range(200):
        env.step(1.0, DT)
    assert env.value == pytest.approx(1.0, abs=1e-3)
    for _ in range(400):
        env.step(0.0, DT)
    assert env.value == pytest.approx(0.0, abs=1e-3)


def test_no_telemetry_means_zero_output():
    engine = EffectEngine(EffectConfig())
    frame = engine.update(None, DT)
    assert frame == frame.__class__()  # ZERO
    inactive = Telemetry(active=False, speed_mps=30.0, rumble_front=1.0)
    for f in run(engine, inactive, 0.5):
        assert f.periodic == 0.0 and f.force_drop == 0.0 and f.constant == 0.0


def test_rumble_strip_produces_bounded_periodic():
    cfg = EffectConfig()
    engine = EffectEngine(cfg)
    frames = run(engine, cruising(rumble_front=1.0), 1.0)
    peak = max(abs(f.periodic) for f in frames[-100:])
    expected = cfg.rumble.gain * cfg.total_gain
    assert 0.8 * expected <= peak <= expected + 1e-6
    assert all(-1.0 <= f.periodic <= 1.0 for f in frames)
    assert all(f.force_drop == 0.0 for f in frames)


def test_understeer_drops_force_proportionally():
    cfg = EffectConfig()
    engine = EffectEngine(cfg)
    us = cfg.understeer
    mid = (us.slip_start + us.slip_full) / 2.0
    frames = run(engine, cruising(slip_front=mid), 1.0)
    assert frames[-1].force_drop == pytest.approx(us.max_drop / 2.0, abs=0.01)
    frames = run(engine, cruising(slip_front=5.0), 1.0)
    assert frames[-1].force_drop == pytest.approx(us.max_drop, abs=0.01)


def test_total_drop_is_capped():
    cfg = EffectConfig()
    engine = EffectEngine(cfg)
    t = cruising(slip_front=5.0, brake=1.0, slip_ratio_front=-1.5, abs_active=True)
    frames = run(engine, t, 1.5)
    assert frames[-1].force_drop == pytest.approx(cfg.max_total_drop, abs=0.01)


def test_abs_falls_back_to_slip_ratio_when_game_has_no_abs_flag():
    cfg = EffectConfig()
    engine = EffectEngine(cfg)
    t = cruising(brake=0.8, slip_ratio_front=-0.5, abs_active=None)
    run(engine, t, 0.5)
    assert engine.status.effects["abs"] > 0.0
    t2 = cruising(brake=0.0, slip_ratio_front=-0.5, abs_active=None)
    run(engine, t2, 1.0)
    assert engine.status.effects["abs"] == pytest.approx(0.0, abs=1e-3)


def test_texture_uses_surface_rumble_when_present_and_speed_fallback_otherwise():
    cfg = EffectConfig()
    engine = EffectEngine(cfg)
    run(engine, cruising(surface_rumble_front=1.0), 1.0)
    with_surface = engine.status.effects["texture"]
    assert with_surface == pytest.approx(cfg.texture.gain, abs=1e-3)

    engine = EffectEngine(cfg)
    run(engine, cruising(surface_rumble_front=None, speed_mps=30.0), 1.0)
    fallback = engine.status.effects["texture"]
    assert fallback == pytest.approx(cfg.texture.gain * cfg.texture.fallback_fraction, abs=1e-3)

    engine = EffectEngine(cfg)
    run(engine, cruising(surface_rumble_front=1.0, speed_mps=0.5), 1.0)
    assert engine.status.effects["texture"] == pytest.approx(0.0, abs=1e-3)


def test_engine_vibration_only_near_idle_or_redline():
    cfg = EffectConfig()
    engine = EffectEngine(cfg)
    run(engine, cruising(rpm=3500.0), 1.0)
    assert engine.status.effects["engine"] == pytest.approx(0.0, abs=1e-4)
    run(engine, cruising(rpm=900.0, speed_mps=0.0), 1.0)
    assert engine.status.effects["engine"] == pytest.approx(cfg.engine.gain, abs=1e-3)
    run(engine, cruising(rpm=7000.0), 1.0)
    assert engine.status.effects["engine"] == pytest.approx(cfg.engine.gain, abs=1e-3)


def test_oversteer_is_off_by_default_and_signed_when_enabled():
    engine = EffectEngine(EffectConfig())
    run(engine, cruising(slip_rear=3.0, lateral_g=1.0), 0.5)
    assert engine.status.constant == 0.0

    cfg = config_from_dict({"oversteer": {"enabled": True, "gain": 0.5}})
    engine = EffectEngine(cfg)
    frames = run(engine, cruising(slip_rear=3.0, lateral_g=1.0), 1.0)
    assert frames[-1].constant == pytest.approx(-0.5 * cfg.total_gain, abs=0.01)
    frames = run(engine, cruising(slip_rear=3.0, lateral_g=-1.0), 1.0)
    assert frames[-1].constant == pytest.approx(0.5 * cfg.total_gain, abs=0.01)

    cfg = config_from_dict({"oversteer": {"enabled": True, "gain": 0.5, "sign": -1}})
    engine = EffectEngine(cfg)
    frames = run(engine, cruising(slip_rear=3.0, lateral_g=1.0), 1.0)
    assert frames[-1].constant == pytest.approx(0.5 * cfg.total_gain, abs=0.01)


def test_periodic_is_a_clean_sine_at_rumble_frequency():
    cfg = config_from_dict({"texture": {"enabled": False}, "engine": {"enabled": False},
                            "rumble": {"spacing_m": 1.0, "min_hz": 1.0, "max_hz": 100.0}})
    engine = EffectEngine(cfg)
    t = cruising(rumble_front=1.0, speed_mps=20.0)  # 20 Hz
    run(engine, t, 1.0)
    frames = run(engine, t, 1.0)
    signal = [f.periodic for f in frames]
    zero_crossings = sum(1 for a, b in zip(signal, signal[1:]) if (a < 0) != (b < 0))
    assert 38 <= zero_crossings <= 42
