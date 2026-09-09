---
layout: default
title: Tuning
parent: Beastier build
grand_parent: FFBeast Wheel
nav_order: 4
---

- TOC
{:toc}

---

The firmware is closed and its terms forbid modification, so all the realism, performance and efficiency you can
add lives in four places: **settings**, **game FFB settings**, **hardware**, and **host-side software** that talks to
the wheel over its USB API. This page covers the first three. The [**telemetry effects**](wheel_beastier_effects.html)
page covers the fourth.

## Realism

Realism on a direct drive wheel is mostly the *absence* of things: no filtering, no fake weight, no latency.

| Setting (FFBeast Setup, Effects tab) | Recommended       | Why                                                                                          |
|--------------------------------------|-------------------|----------------------------------------------------------------------------------------------|
| Total effect strength                | 100               | Scale forces in the **game**, not in the device. Device-side scaling throws away resolution. |
| Static dampening                     | **5-15**          | Just enough to stop oscillation when you let go. Every extra point masks small road detail.  |
| Soft stop strength / range           | 60-80 / 10-15 deg | Firm and short. Long soft stops feel like rubber.                                            |
| Soft stop dampening                  | 30-50             | Stops the wheel bouncing off the stop.                                                       |
| Integrated spring                    | 0                 | Only for games with no FFB at all.                                                           |
| DirectX spring / constant / periodic | 100 / 100 / 100   | Let the game decide the mix.                                                                 |
| Dynamic dampening (*Pro*)            | low, 10-20        | Speed-dependent damping that lets the wheel be light at speed and calm when parked.          |

| Setting (Controller tab)  | Recommended    | Why                                                                                       |
|---------------------------|----------------|-------------------------------------------------------------------------------------------|
| Speed sample buffer size  | minimum        | 10000 CPR does not need it. Each step of buffer is added latency on dampening.            |
| Position smoothing        | 0              | Optical encoder is already clean.                                                         |
| Motion range              | match the car  | 900 road, 540 GT, 360-450 formula, 1080 trucks. Set per game where the game supports it.  |

In-game: set FFB gain so peak forces just avoid clipping. Assetto Corsa and ACC show a clipping meter.
Most DD owners run **0 minimum force**, **0 damper**, **low or 0 road/kerb "enhancement"** because the motor
already reproduces the physics. Add the extras back with the telemetry tool only where the game's own FFB is thin.

## Performance

Peak force is set by current into the motor. Upstream measured about **10.9 Nm** for a 20 mm stator,
**12.7 Nm** for 25 mm and **15 Nm** for 30 mm, all at 15 A. The ODESC can supply far more than the motor
can turn into torque without overheating, so the limit is thermal.

1. Raise **Power limit** in steps of 5-10. After each step do two minutes of hard driving. Touch the motor shell.
2. Stop where the shell is hot but you can still hold it (roughly 60 C). That is your ceiling for continuous use.
3. If the PSU shuts down under load before that, the PSU is the limit. Raise **Braking resistor limit** first
   (regen trips often masquerade as overload trips), then consider a bigger PSU.
4. A small 12 V fan on the motor shell buys a surprising amount of headroom. Hoverboard motors are sealed and rely on the tyre for cooling.

Transient sharpness improves with bus voltage because current ramps faster into the winding inductance.
24 V is a clear step up from 19.5 V. 36 V is a smaller step. Above that the regen risk on a 56 V board outweighs the gain.

## Efficiency

Efficiency here means less heat and fewer PSU trips for the same feel.

- **Braking resistor limit** as low as it goes without PSU trips. Everything above that is wasted heat.
- **Static dampening** low. Damping is torque you pay for constantly.
- **Power limit** at the value you actually use, not the maximum. Clipping is heat that adds nothing.
- **Motor choice** matters more than any setting. A 30 mm stator motor at 60 percent power runs cooler and feels better than a 20 mm motor at 100 percent. Weigh your motor: 2.9 kg suggests 30 mm, 2.3 kg suggests 20 mm.
- Use the **Enable effects** GPIO mode (*Pro*) on a switch so the motor is de-energised when you leave the rig.

## Hardware that improves feel for free

- **Rigidity.** Any flex between the motor mount and the rim reads as a spring in series with the FFB. Tighten the SK16 holders and brace the frame.
- **Rim mass.** A heavy rim adds inertia the motor must fight. Pick a light rim if you are chasing detail.
- **Coupling backlash.** Belt over gear. Direct over belt. Backlash reads as a dead zone on every direction change.
- **Encoder concentricity.** Verify by watching belt tension over a full turn.
