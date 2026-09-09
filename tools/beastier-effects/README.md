# Beastier Effects

Telemetry-driven extra force feedback for the [FFBeast DIY wheel](https://ffbeast.github.io/docs/en/wheel.html).

The wheel firmware exposes a vendor HID interface with a direct-control report
(`SpringForce`, `ConstantForce`, `PeriodicForce`, `ForceDrop`). This tool reads game
telemetry and drives that report at 200 Hz to add:

- road texture locked to wheel rotation
- rumble strips and kerbs
- ABS pulsing and front lock-up force drop
- understeer force drop as the front tyres pass their peak
- subtle engine vibration near idle and redline
- an optional rear-slip counter-steer cue (off by default)

Sources: Forza Motorsport / Horizon (UDP Data Out), Assetto Corsa and ACC (shared memory),
and a built-in demo sweep.

Full documentation lives on the site:
[Telemetry effects](https://thepicklebaron.github.io/ffbeastier.github.io/docs/en/wheel_beastier_effects.html).

## Quick start

```bash
python -m pip install -e ".[hid]"
python -m beastier_effects --source demo --dry-run       # no wheel needed
python -m beastier_effects --source demo                 # wheel on the bench
python -m beastier_effects --source forza --port 5300
python -m beastier_effects --source assetto
```

Copy `effects.example.toml`, change what you like, pass it with `--config`.

## Tests

```bash
python -m pip install -e ".[dev]"
python -m pytest
```

The tests cover the byte layout of every report against the vendor's `wheel_api.h`,
the Forza packet decoder for Sled and Dash variants, and the effect engine's behaviour.
No hardware is needed to run them.

## Status

Written against the RC.26.1.1 protocol header and the vendor's reference C++ implementation.
Not yet verified against a physical wheel. Start with `total_gain = 0.3`.

## Protocol notes

- VID 1115, PID 22999, vendor interface 0.
- Every write is 65 bytes: report id `0xA3`, data command byte, payload, zero padding.
- Direct control payload is `<hhhB`: spring, constant, periodic in units of 1/10000, drop in percent.
- State reads arrive as interrupt reports: report id, 4 version bytes, registered flag, position `h`, torque `h`.
