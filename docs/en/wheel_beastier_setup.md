---
layout: default
title: Setup
parent: Beastier build
grand_parent: FFBeast Wheel
nav_order: 3
---

- TOC
{:toc}

---

This is the shortest path from a bare ODESC V4.2 to a working wheel with this hardware.
The upstream pages remain the reference: [**Firmware flashing**](software_firmware_flashing.html),
[**Controller settings**](ffbeast_setup_controller.html), [**License**](ffbeast_setup_license.html).

## 1. Download

Grab the current wheel package from this repo's [**Downloads**](downloads_wheel.html) page:
**RC.26.1.1.Full**. It contains:

| Path                                                   | What it is                              |
|--------------------------------------------------------|-----------------------------------------|
| `ffbeast-wheel-hex/ffbeast-wheel-odrive-RC.26.1.1.hex` | Firmware for the ODESC                  |
| `ffbeast-wheel-ui/ffbeast-wheel-setup-RC.26.1.1.exe`   | FFBeast Setup app                       |
| `ffbeast-wheel-api-lib/`                               | C++ USB API used by the telemetry tool  |

Install [**STM32CubeProgrammer**](https://www.st.com/en/development-tools/stm32cubeprog.html#get-software).

## 2. Flash (ODESC V4.2 has a BOOT button)

1. Connect USB-C to the PC. Leave the PSU **off**.
2. Press and **hold BOOT**.
3. Switch the PSU **on** while holding BOOT. The board enumerates as an STM32 DFU device.
4. In STM32CubeProgrammer: method **USB**, Refresh, Connect.
5. **Full chip erase** on a fresh board.
6. Open the `.hex`, Download, wait for the verify, Disconnect.
7. Press **RESET**, or power-cycle. The board now shows up as an **FFBeast Wheel** USB device.

{: .important }
> Pressing RESET alone does not enter DFU on this board. It must be a power cycle with BOOT held, exactly as upstream says.

## 3. First power-up checklist

Before enabling force, with the wheel attached and nothing in the way:

- PSU polarity checked twice, fuse in the positive lead.
- Brake resistor on AUX.
- Encoder on 5V/GND/A/B, powered from the 5V pin.
- Motor phases on A/B/C, Hall wires unconnected and insulated.
- Nothing loose near the motor. It will move on its own during calibration.

## 4. Values for this hardware in FFBeast Setup

Open **FFBeast Setup**, tab **Controller**.

| Setting                  | Value                                   | Reason                                                                                    |
|--------------------------|-----------------------------------------|-------------------------------------------------------------------------------------------|
| Pole pairs               | **15**                                  | Standard 6.5 inch hoverboard motor. Count magnets and halve it if unsure.                 |
| Encoder CPR              | **10000** direct, or 10000 x belt ratio | 2500 PPR x 4. See the [**encoders**](wheel_beastier_encoders.html) page for belt ratios. |
| Calibration              | **Start as the center**                 | Wheel has no hard stops.                                                                  |
| Calibration magnitude    | **5**                                   | Upstream starting value for wheels. Raise in steps of 1 only if calibration fails.        |
| Calibration speed        | default                                 |                                                                                           |
| Power limit              | **10** for the first run                | Raise later. See [**tuning**](wheel_beastier_tuning.html).                                |
| Braking resistor limit   | **10**                                  | Raise if the PSU trips during fast flicks.                                                |
| Speed sample buffer size | **1** (minimum)                         | 10000 CPR is above the 6000 CPR noise threshold. Only raise if dampening buzzes.          |
| Position smoothing       | **0**                                   | Optical encoder is clean. Smoothing only adds lag.                                        |
| Enable force             | checked                                 |                                                                                           |
| Debug force              | unchecked                               | Only for direction checks with VkbJoyTester.                                              |

Press **Save and reboot**. The wheel twitches once to find the phase order and then holds.

## 5. Direction checks

1. **Joystick direction.** Open [**VkbJoyTester**](downloads_utils.html). Turn the wheel right. The X marker must move right. If not, tick **Invert joystick output**.
2. **Force direction.** Set Motion range to 40 and Power limit to 10. Turn to the soft stop. It must push back toward center. If it pulls further out, tick **Invert force output**.
3. Restore Motion range to your normal value (900 is a sane default for road cars, 540 for GT, 1080 for trucks).
4. Press **Reset center** with the wheel straight. Save.

## 6. Activate

Tab **License**: select **Wheel**, leave the key blank, press **Activate**. This is **Light** mode, which covers
everything on this page and everything in the [**tuning**](wheel_beastier_tuning.html) page except the items marked *Pro*.
When the wheel is finished and has run for a while without incident, buy the
[**Premium license**](shop_wheel_license.html). The license is bound to the chip serial and cannot be replaced if the board dies,
so leave it until the wiring is proven.

## 7. Verify the encoder count

With **Debug force** unchecked, watch the position value in the setup app. Turn the wheel exactly ten full turns
and back. If the readout does not return to its start within a count or two, revisit the
[**wiring**](wheel_beastier_wiring.html#if-position-jumps-or-counts-drift) notes.
