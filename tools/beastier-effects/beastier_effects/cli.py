"""Command line entry point: ``python -m beastier_effects --source forza``."""

from __future__ import annotations

import argparse
import sys
import time
from typing import Optional

from .config import load_config
from .device import FakeWheelDevice, WheelDevice
from .engine import EffectEngine
from .protocol import ZERO_CONTROL
from .telemetry import SOURCE_NAMES, make_source
from .telemetry.base import Telemetry

SPIN_MARGIN_S = 0.0015


class _TimerResolution:
    """Ask Windows for 1 ms timer resolution so a 200 Hz loop is achievable."""

    def __enter__(self) -> "_TimerResolution":
        self._winmm = None
        if sys.platform == "win32":
            import ctypes

            self._winmm = ctypes.WinDLL("winmm")
            self._winmm.timeBeginPeriod(1)
        return self

    def __exit__(self, *exc: object) -> None:
        if self._winmm is not None:
            self._winmm.timeEndPeriod(1)


def wait_until(deadline: float) -> None:
    """Sleep coarsely, then spin for the last moment so the period is accurate."""
    while True:
        remaining = deadline - time.perf_counter()
        if remaining <= 0:
            return
        if remaining > SPIN_MARGIN_S:
            time.sleep(remaining - SPIN_MARGIN_S)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="beastier-effects",
        description="Telemetry-driven extra effects for the FFBeast DIY wheel.",
    )
    p.add_argument("--source", choices=SOURCE_NAMES, default="demo",
                   help="telemetry source (default: demo)")
    p.add_argument("--port", type=int, default=5300, help="UDP port for --source forza")
    p.add_argument("--host", default="0.0.0.0", help="bind address for --source forza")
    p.add_argument("--slip-scale", type=float, default=1.0,
                   help="multiplier on Assetto wheelSlip before thresholds")
    p.add_argument("--config", help="TOML file with effect overrides")
    p.add_argument("--rate", type=float, help="output rate in Hz (overrides config)")
    p.add_argument("--dry-run", action="store_true",
                   help="do not open the wheel; print what would be sent")
    p.add_argument("--duration", type=float, default=0.0,
                   help="stop after this many seconds (0 = run until Ctrl+C)")
    p.add_argument("--quiet", action="store_true", help="suppress the per-second status line")
    return p


def format_status(elapsed: float, tel_rate: float, engine: EffectEngine, active: bool) -> str:
    st = engine.status
    parts = [f"{elapsed:6.1f}s", f"tel {tel_rate:5.1f}Hz", "on-track" if active else "idle   ",
             f"periodic pk {st.periodic_peak:4.2f}", f"drop {st.force_drop:4.2f}"]
    if st.constant:
        parts.append(f"const {st.constant:+.2f}")
    live = [f"{k}={v:.2f}" for k, v in st.effects.items() if v > 0.005]
    if live:
        parts.append(" ".join(live))
    return " | ".join(parts)


def run(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    if args.rate:
        cfg.rate_hz = args.rate
    engine = EffectEngine(cfg)
    source = make_source(args.source, port=args.port, host=args.host, slip_scale=args.slip_scale)

    device: WheelDevice
    if args.dry_run:
        device = FakeWheelDevice()
        print("dry run: no wheel opened")
    else:
        device = WheelDevice.open()
        print("wheel opened")

    period = 1.0 / cfg.rate_hz
    latest: Optional[Telemetry] = None
    last_packet_at = 0.0
    packets_window = 0
    window_start = time.perf_counter()
    start = window_start
    next_tick = start
    last = start
    device.send_direct_control(ZERO_CONTROL)
    try:
        while True:
            now = time.perf_counter()
            sample = source.poll()
            if sample is not None:
                latest = sample
                last_packet_at = now
                packets_window += 1
            if latest is not None and now - last_packet_at > cfg.telemetry_timeout_s:
                latest = None
            dt = now - last
            last = now
            control = engine.update(latest, dt)
            device.send_direct_control(control)

            if not args.quiet and now - window_start >= 1.0:
                rate = packets_window / (now - window_start)
                print(format_status(now - start, rate, engine, latest is not None and latest.active))
                window_start = now
                packets_window = 0
            if args.duration and now - start >= args.duration:
                break
            next_tick += period
            if time.perf_counter() - next_tick > period:
                next_tick = time.perf_counter()  # fell behind, resync instead of bursting
            wait_until(next_tick)
    except KeyboardInterrupt:
        print("\nstopping")
    finally:
        try:
            device.send_direct_control(ZERO_CONTROL)
        finally:
            device.close()
            source.close()
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        with _TimerResolution():
            return run(args)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
