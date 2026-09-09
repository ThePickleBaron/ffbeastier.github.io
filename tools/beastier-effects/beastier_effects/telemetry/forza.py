"""Forza "Data Out" UDP telemetry (Motorsport 7, Motorsport 2023, Horizon 4/5).

Packet layout is from the official Forza Motorsport Data Out documentation.
The Sled block is 232 bytes. Dash appends 79 bytes at offset 232 (Motorsport)
or at offset 244 (Horizon, which inserts 12 undocumented bytes).
"""

from __future__ import annotations

import math
import socket
import struct
from typing import Optional

from .base import Telemetry

SLED = struct.Struct(
    "<"
    "iI"        # IsRaceOn, TimestampMS
    "fff"       # EngineMaxRpm, EngineIdleRpm, CurrentEngineRpm
    "fff"       # Acceleration X Y Z
    "fff"       # Velocity X Y Z
    "fff"       # AngularVelocity X Y Z
    "fff"       # Yaw Pitch Roll
    "ffff"      # NormalizedSuspensionTravel FL FR RL RR
    "ffff"      # TireSlipRatio
    "ffff"      # WheelRotationSpeed
    "iiii"      # WheelOnRumbleStrip
    "ffff"      # WheelInPuddleDepth
    "ffff"      # SurfaceRumble
    "ffff"      # TireSlipAngle
    "ffff"      # TireCombinedSlip
    "ffff"      # SuspensionTravelMeters
    "iiiii"     # CarOrdinal, CarClass, CarPerformanceIndex, DrivetrainType, NumCylinders
)
assert SLED.size == 232

DASH = struct.Struct(
    "<"
    "fff"       # Position X Y Z
    "f"         # Speed (m/s)
    "f"         # Power
    "f"         # Torque
    "ffff"      # TireTemp
    "f"         # Boost
    "f"         # Fuel
    "f"         # DistanceTraveled
    "fff"       # BestLap, LastLap, CurrentLap
    "f"         # CurrentRaceTime
    "H"         # LapNumber
    "B"         # RacePosition
    "BBBBB"     # Accel, Brake, Clutch, HandBrake, Gear
    "bbb"       # Steer, NormalizedDrivingLine, NormalizedAIBrakeDifference
)
assert DASH.size == 79

SLED_LENGTH = SLED.size
DASH_OFFSETS = {
    SLED_LENGTH + DASH.size: SLED_LENGTH,            # 311: Motorsport 7 / 2023 dash
    SLED_LENGTH + DASH.size + 20: SLED_LENGTH,       # 331: Motorsport 2023 with tyre wear + track
    SLED_LENGTH + 12 + DASH.size: SLED_LENGTH + 12,  # 323: Horizon dash
    SLED_LENGTH + 12 + DASH.size + 1: SLED_LENGTH + 12,  # 324: Horizon 4 variant
}

# Sled field indices
_IS_RACE_ON = 0
_MAX_RPM, _IDLE_RPM, _RPM = 2, 3, 4
_ACC_X = 5
_VEL_X = 8
_SLIP_RATIO = 21
_WHEEL_ROT = 25
_ON_RUMBLE = 29
_SURFACE = 37
_COMBINED = 45
_NUM_CYL = 57

# Dash field indices
_D_SPEED = 3
_D_ACCEL, _D_BRAKE = 19, 20
_D_GEAR = 23


def parse_packet(data: bytes) -> Optional[Telemetry]:
    """Decode a Data Out packet. Returns None for packets that are too short."""
    if len(data) < SLED_LENGTH:
        return None
    s = SLED.unpack_from(data, 0)
    dash = None
    offset = DASH_OFFSETS.get(len(data))
    if offset is not None and len(data) >= offset + DASH.size:
        dash = DASH.unpack_from(data, offset)

    t = Telemetry()
    t.active = s[_IS_RACE_ON] == 1
    if dash is not None:
        t.speed_mps = abs(dash[_D_SPEED])
        t.throttle = dash[_D_ACCEL] / 255.0
        t.brake = dash[_D_BRAKE] / 255.0
        t.gear = dash[_D_GEAR]
    else:
        vx, vy, vz = s[_VEL_X:_VEL_X + 3]
        t.speed_mps = math.sqrt(vx * vx + vy * vy + vz * vz)
    t.rpm = s[_RPM]
    t.rpm_max = s[_MAX_RPM]
    t.rpm_idle = s[_IDLE_RPM]
    t.cylinders = s[_NUM_CYL] or None
    fl, fr, rl, rr = s[_WHEEL_ROT:_WHEEL_ROT + 4]
    t.wheel_speed_front_radps = (abs(fl) + abs(fr)) / 2.0
    combined = s[_COMBINED:_COMBINED + 4]
    t.slip_front = max(abs(combined[0]), abs(combined[1]))
    t.slip_rear = max(abs(combined[2]), abs(combined[3]))
    ratio = s[_SLIP_RATIO:_SLIP_RATIO + 4]
    t.slip_ratio_front = min(ratio[0], ratio[1])
    rumble = s[_ON_RUMBLE:_ON_RUMBLE + 4]
    t.rumble_front = (float(rumble[0] != 0) + float(rumble[1] != 0)) / 2.0
    surface = s[_SURFACE:_SURFACE + 4]
    t.surface_rumble_front = max(abs(surface[0]), abs(surface[1]))
    t.abs_active = None
    t.lateral_g = s[_ACC_X] / 9.81
    return t


class ForzaSource:
    """Non-blocking UDP listener. ``poll`` drains the socket and returns the newest packet."""

    name = "forza"

    def __init__(self, port: int = 5300, host: str = "0.0.0.0"):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((host, port))
        self._sock.setblocking(False)
        self.packets = 0

    def poll(self) -> Optional[Telemetry]:
        newest: Optional[bytes] = None
        while True:
            try:
                data, _ = self._sock.recvfrom(2048)
            except BlockingIOError:
                break
            except OSError:
                break
            newest = data
            self.packets += 1
        return parse_packet(newest) if newest is not None else None

    def close(self) -> None:
        self._sock.close()
