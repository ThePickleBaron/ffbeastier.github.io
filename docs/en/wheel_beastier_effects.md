---
layout: default
title: Telemetry effects
parent: Beastier build
grand_parent: FFBeast Wheel
nav_order: 5
---

- TOC
{:toc}

---

## What it is

**Beastier Effects** is a small open-source Python tool that lives in this repository under
[`tools/beastier-effects`](https://github.com/ThePickleBaron/ffbeastier.github.io/tree/main/tools/beastier-effects).
It reads game telemetry and sends extra forces to the wheel through the
[**custom USB protocol**](wheel_programming.html) that the firmware exposes on its vendor interface.

FFBeast ships a telemetry-driven effects app for flight controls (FFBeast Commander) but nothing equivalent for the wheel.
This fills that gap for the channels the wheel's direct-control report exposes:

| Wheel API field | Used for                                                                                       |
|-----------------|------------------------------------------------------------------------------------------------|
| `PeriodicForce` | Road texture, rumble strips, ABS pulsing, engine vibration. Not affected by firmware dampening. |
| `ForceDrop`     | Scales down the game's DirectX forces when the front tyres saturate (understeer) or lock.      |
| `ConstantForce` | Optional rear-slip counter-steer cue. Off by default until you verify the sign.                |
| `SpringForce`   | Not used. The game provides the spring via DirectX.                                            |

Direct control works in **Light** mode. The device state report and the direct-control report are documented as
available on both licenses.

## Supported telemetry sources

| Source    | How it reads                                       | Enable in game                                                                                     |
|-----------|----------------------------------------------------|----------------------------------------------------------------------------------------------------|
| `forza`   | UDP "Data Out", Sled or Dash format, 60 Hz         | Settings, Gameplay and HUD, UDP Race Telemetry: Data Out On, IP 127.0.0.1, port 5300, format Dash  |
| `assetto` | Shared memory `acpmf_physics` and `acpmf_graphics` | Nothing. Works for Assetto Corsa and Assetto Corsa Competizione.                                   |
| `demo`    | Synthetic data that sweeps every effect            | Nothing. For a bench test with the wheel, or `--dry-run` without it.                               |

Forza Horizon 4 and 5 use the same packet with a 12-byte offset and are handled automatically.

## Effects and what drives them

| Effect           | Trigger                                                      | Output                                                          | Default    |
|------------------|--------------------------------------------------------------|-----------------------------------------------------------------|------------|
| Road texture     | Forza `SurfaceRumble`, or speed for Assetto                  | Low-amplitude periodic at a frequency locked to wheel rotation  | on, subtle |
| Rumble strip     | Forza `WheelOnRumbleStrip` front wheels                      | Periodic burst whose frequency follows road speed               | on         |
| ABS              | Assetto `abs` in action, Forza front slip ratio under braking | 15 Hz pulse plus a small force drop                             | on         |
| Front lock-up    | Front slip ratio strongly negative under braking             | Force drop up to a limit                                        | on         |
| Understeer       | Front combined slip beyond threshold                         | Force drop proportional to how far past the peak the tyres are  | on         |
| Engine vibration | RPM near idle or near redline                                | Very low-amplitude periodic at firing frequency                 | on, tiny   |
| Oversteer cue    | Rear slip beyond threshold                                   | Constant force toward counter-steer                             | **off**    |

Every amplitude is passed through an attack/release envelope so effects never click on or off.
When the game reports "not on track" every channel decays to zero.

## Install

```bash
cd tools/beastier-effects
python -m pip install -e ".[hid]"
```

The `hid` extra pulls in `hidapi`. Python 3.11 or newer.

## Run

Bench test without the wheel connected:

```bash
python -m beastier_effects --source demo --dry-run
```

Bench test with the wheel, no game. The wheel should buzz gently and sweep effects:

```bash
python -m beastier_effects --source demo
```

Forza, after enabling Data Out to 127.0.0.1 port 5300:

```bash
python -m beastier_effects --source forza --port 5300
```

Assetto Corsa or ACC:

```bash
python -m beastier_effects --source assetto
```

Custom gains:

```bash
python -m beastier_effects --source forza --config my_effects.toml
```

Copy `effects.example.toml` and edit only the keys you want to change. The tool prints a one-line status every second
showing telemetry rate, active effects and the peak periodic amplitude so you can see clipping.

## Safety

- The first packet sent is all zeros and so is the last one on exit or Ctrl+C.
- The firmware itself falls back to normal mode when direct-control packets stop arriving.
- Every output is clamped to the protocol's range and to `total_gain` in the config.
- Start with `total_gain = 0.3`, confirm every effect feels right, then raise it.

{: .warning }
> This tool was written against the published protocol header and the vendor's reference C++ implementation, and its
> packet encoding is covered by unit tests. It has **not** yet been run against a physical wheel. Test with a low `total_gain`
> and be ready with Ctrl+C.
