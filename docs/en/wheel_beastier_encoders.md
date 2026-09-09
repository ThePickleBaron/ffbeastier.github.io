---
layout: default
title: Encoders
parent: Beastier build
grand_parent: FFBeast Wheel
nav_order: 2
---

- TOC
{:toc}

---

The firmware only cares about one thing: clean A/B quadrature pulses at 3.3-5 V logic levels
and the correct **CPR** typed into FFBeast Setup. The rest is mounting and electrical detail.
This page ranks the usual candidates so you can pick from what you already own.

## The rules that decide it

1. **CPR = 4 x PPR.** Enter CPR in the setup app. The field is a 16-bit integer, so the effective CPR must stay **below 65535**.
2. **More CPR is better up to a point.** Upstream recommends at least 1000 CPR direct-coupled and says 6000 CPR or less needs speed buffering. Above roughly 10000 CPR the gains are small.
3. **Output stage decides the wiring.** Push-pull and voltage output connect directly. NPN open-collector needs pull-ups. Line driver needs only its + outputs. All must be powered from 5 V unless they are 3.3 V native.
4. **No backlash in the coupling.** A geared encoder that skips a tooth loses its center. A belt is forgiving. A direct coupling is best.

## Comparison of common candidates

| Encoder                                    | CPR (direct) | Output                | External parts                          | Mounting on a hoverboard motor                       | Verdict                                                                                   |
|--------------------------------------------|--------------|-----------------------|-----------------------------------------|------------------------------------------------------|-------------------------------------------------------------------------------------------|
| **38 mm 2500 PPR push-pull (this build)**  | **10000**    | Push-pull             | None                                    | Belt, gear or shaft coupling required                | **Best resolution per dollar. Use it.**                                                   |
| 38 mm 1000/1024 PPR push-pull or voltage   | 4000/4096    | Push-pull / voltage   | None                                    | Same                                                 | Fine. Similar to MT6701 resolution, more robust mounting.                                 |
| 38 mm 600 PPR NPN (LPD3806 style)          | 2400         | NPN open-collector    | 2.2-4.7 k pull-ups to 5 V on A and B    | Same                                                 | Works, but low CPR. Needs speed buffer. Only with a belt step-up.                         |
| Omron E6B2-CWZ6C (NPN)                     | 4 x PPR      | NPN open-collector    | Pull-ups as above                       | Same                                                 | Reliable. Wire the pull-ups.                                                              |
| Omron E6B2-CWZ3E (voltage output)          | 4 x PPR      | Voltage               | None                                    | Same                                                 | Reliable. Direct connect.                                                                 |
| Omron E6B2-CWZ1X (line driver)             | 4 x PPR      | RS-422 differential   | None; use A+ and B+ only                | Same                                                 | Works on A+/B+ at 5 V. Leave A- and B- open.                                              |
| CUI AMT102/103                             | up to 8192   | Push-pull, 5 V        | None                                    | Sleeve fits 2-8 mm shafts, needs a fixed shaft end   | Upstream favorite for joysticks. Awkward on a hoverboard motor whose axle is stationary.  |
| CUI AMT10E2/10E3                           | up to 20480  | Push-pull, 5 V        | None                                    | Same as above                                        | Best resolution. Same mounting caveat.                                                    |
| MT6701 magnetic board                      | 4096         | ABZ, 3.3/5 V          | None                                    | Magnet on the axle end, board on a bracket           | Cheapest. Sensitive to magnet centering. The reference build uses it.                     |
| MT6825 magnetic                            | 16384        | ABZ                   | None                                    | Same                                                 | Better than MT6701 if you can mount it precisely.                                         |
| TLE5012B magnetic                          | 16384        | ABZ                   | None                                    | Same                                                 | **Avoid.** Programmed dead zone feels like backlash.                                      |
| Motor Hall sensors                         | 90           | Open-collector        | Pull-ups                                | Built in                                             | **Not usable.** Far too coarse.                                                           |

{: .important }
> If you have both the 2500 PPR unit and a magnetic board, run the 2500 PPR unit.
> The only reason to fall back to the magnetic board is a mounting problem you cannot solve.

## Mounting a shaft encoder on a hoverboard motor

A hoverboard motor is an out-runner. The **axle is stationary** and the **shell rotates**.
A shaft encoder therefore cannot be pushed straight onto the axle. You have three options.

### Belt step-up (recommended)

A large GT2 pulley bolted to the rotating shell drives a small pulley on the encoder shaft.
The encoder body sits on a bracket fixed to the frame.

- Community model: [**Hoverboard FFBeast / OpenFFBoard encoder mount, belt or gear**](https://www.printables.com/model/981504-hoverboard-ffbeast-openffboard-ffb-sim-wheel-encod) by datapagan. The description recommends a **348 mm GT2 6 mm closed-loop belt** and notes that the shell lip must be filed flush so the belt clears it.
- Companion pulley: [**120-tooth GT2 pulley for 6.5 inch hoverboard motor**](https://www.printables.com/model/568306-120-tooth-gt2-pulley-for-65-hoverboard-motor).
- Ratio math from that page: **effective CPR = PPR x 4 x (big teeth / small teeth)**.

| Small pulley | Ratio with 120 T | Effective CPR from 2500 PPR | Fits 16-bit field?   |
|--------------|------------------|-----------------------------|----------------------|
| 20 T         | 6.0              | 60000                       | Yes, barely          |
| 30 T         | 4.0              | 40000                       | Yes                  |
| **40 T**     | **3.0**          | **30000**                   | **Yes, comfortable** |
| 60 T         | 2.0              | 20000                       | Yes                  |

{: .warning }
> Do not exceed a 6:1 step-up with this encoder. 2500 x 4 x 6.5 = 65000 is the edge of the CPR field and leaves no margin.
> Also check the encoder's **maximum shaft speed** (about 6000 rpm on these units). A 6:1 step-up at a 300 rpm wheel flick is 1800 rpm at the encoder. Fine, but do not go silly.

### Gear drive

Same idea with a printed ring gear on the shell and a pinion on the encoder. The datapagan page reports that
a motor that is not perfectly concentric makes gears skip teeth, which loses encoder steps and the center position.
Belt is safer unless your shell runs dead true.

### Direct coupling on the wheel side

Bolt the encoder to a bracket that is fixed to the **rotating** hub, couple its shaft to the stationary axle stub with a
flexible coupler, and route the cable through a slip ring. This gives a true 1:1 with zero backlash but the cable
management is the hard part. Community mounts with slip rings exist:
[**erikm's encoder and slip ring mount v2**](https://www.printables.com/model/1326250-encoder-and-slip-ring-mount-for-ffbeast-wheel-v2).

### Whatever you choose

- Keep the encoder shaft **parallel** to the motor axis. Angular misalignment shows up as a once-per-rev force ripple.
- Check concentricity by turning the wheel slowly and watching belt tension or gear mesh through a full rotation.
- Verify the count: set CPR, turn the wheel exactly 10 times, confirm the position readout returns to where it started.
