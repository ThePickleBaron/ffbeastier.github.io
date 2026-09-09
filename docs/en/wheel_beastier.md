---
layout: default
title: Beastier build
parent: FFBeast Wheel
has_children: true
nav_order: 2
---

- TOC
{:toc}

---

{: .note }
> This section is specific to the **FFBeastier** fork. It documents one concrete build on top of the upstream
> FFBeast wheel firmware: a hoverboard motor, an **ODESC V4.2 (56V)** controller and a **2500 PPR push-pull shaft encoder**.
> Everything upstream still applies. Read the upstream [**Reference assembly**](wheel_assembly.html) first.

## What is different from the reference build

| Item        | Upstream reference build    | Beastier build                                        | Why                                                                                   |
|-------------|-----------------------------|-------------------------------------------------------|---------------------------------------------------------------------------------------|
| Controller  | MKS XDrive single axis      | **ODESC V4.2, 56V version**                           | Compact, full-body heat sink, BOOT button for DFU, 2 ohm 50 W brake resistor included  |
| Encoder     | MT6701 magnetic, 4096 CPR   | **38 mm optical shaft encoder, 2500 PPR = 10000 CPR** | 2.4x the resolution, no magnet alignment problems, no dead zone                       |
| Motor       | 6.5 inch hoverboard         | 6.5 inch hoverboard                                   | Same                                                                                  |
| Mount       | SK16 holders on 16 mm shaft | Already built                                         | Same idea                                                                             |

## Why this encoder is a realism upgrade

The firmware computes speed from encoder counts for the dampening and friction effects.
Upstream notes that below **6000 CPR** the speed estimate gets noisy and you must add
[**speed sample buffer**](ffbeast_setup_controller.html#speed-sample-buffer-size), which adds latency.
At **10000 CPR** the buffer can stay at its minimum, so dampening reacts faster and feels cleaner.
A 2500 PPR optical encoder also has no magnetic dead zone and is not sensitive to magnet centering,
which upstream flags as the main weakness of the cheap magnetic option.

If you drive the encoder through a belt or gear step-up the effective CPR grows by the ratio.
See [**Encoders**](wheel_beastier_encoders.html) for the limits.

## Pages in this section

1. [**Wiring**](wheel_beastier_wiring.html): ODESC V4.2 pinout, push-pull encoder wiring, PSU and brake resistor.
2. [**Encoders**](wheel_beastier_encoders.html): how the 2500 PPR unit compares with the other encoders you may have on the shelf, and how to mount a shaft encoder on a hoverboard motor.
3. [**Setup**](wheel_beastier_setup.html): flashing RC.26.1.1, first power-up, and the exact values to type into FFBeast Setup for this hardware.
4. [**Tuning**](wheel_beastier_tuning.html): settings for realism, peak performance and efficiency, in that order.
5. [**Telemetry effects**](wheel_beastier_effects.html): the open-source companion tool in this repo that adds road texture, kerbs, ABS and grip-loss cues from game telemetry over the wheel's USB API.

## Bill of materials for the electronics

| Part                                                                  | Qty | Notes                                                                        |
|-----------------------------------------------------------------------|-----|------------------------------------------------------------------------------|
| ODESC V4.2 single axis, **56V** version                               | 1   | Comes with 50 W 2 ohm brake resistor and GH1.25 cable set                    |
| 38 mm / 6 mm shaft incremental encoder, 2500 PPR, push-pull, 5-26 V   | 1   | Power it from the ODESC **5V** pin only. See wiring page.                    |
| PSU 24 V, 10 A or more                                                | 1   | 19.5 V laptop brick also works. See PSU notes on the wiring page.            |
| Encoder mount: belt or direct coupling                                | 1   | Printable options listed on the encoders page                                |
| XT60 or similar DC connector                                          | 1   | Keep polarity obvious. Reverse polarity kills the board and your license.    |
| Inline fuse 15-20 A on the PSU positive lead                          | 1   | Cheap insurance for a 70 A capable board                                     |
| USB-C cable, data capable                                             | 1   | ODESC V4.2 uses USB-C                                                        |
