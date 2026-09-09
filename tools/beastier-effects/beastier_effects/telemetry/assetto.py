"""Assetto Corsa / Assetto Corsa Competizione shared-memory telemetry (Windows).

Only the leading part of ``SPageFilePhysics`` is mapped. Both games share that
prefix, so one reader serves AC and ACC. Layout from the widely used
``sim_info.py`` (Rombik) with ``_pack_ = 4``.
"""

from __future__ import annotations

import ctypes
from ctypes import c_float, c_int32
from typing import Optional

from .base import Telemetry

AC_LIVE = 2


class PhysicsPrefix(ctypes.Structure):
    _pack_ = 4
    _fields_ = [
        ("packetId", c_int32),
        ("gas", c_float),
        ("brake", c_float),
        ("fuel", c_float),
        ("gear", c_int32),
        ("rpms", c_int32),
        ("steerAngle", c_float),
        ("speedKmh", c_float),
        ("velocity", c_float * 3),
        ("accG", c_float * 3),
        ("wheelSlip", c_float * 4),
        ("wheelLoad", c_float * 4),
        ("wheelsPressure", c_float * 4),
        ("wheelAngularSpeed", c_float * 4),
        ("tyreWear", c_float * 4),
        ("tyreDirtyLevel", c_float * 4),
        ("tyreCoreTemperature", c_float * 4),
        ("camberRAD", c_float * 4),
        ("suspensionTravel", c_float * 4),
        ("drs", c_float),
        ("tc", c_float),
        ("heading", c_float),
        ("pitch", c_float),
        ("roll", c_float),
        ("cgHeight", c_float),
        ("carDamage", c_float * 5),
        ("numberOfTyresOut", c_int32),
        ("pitLimiterOn", c_int32),
        ("abs", c_float),
    ]


class GraphicsPrefix(ctypes.Structure):
    _pack_ = 4
    _fields_ = [
        ("packetId", c_int32),
        ("status", c_int32),
        ("session", c_int32),
    ]


class StaticPrefix(ctypes.Structure):
    _pack_ = 4
    _fields_ = [
        ("_smVersion", ctypes.c_wchar * 15),
        ("_acVersion", ctypes.c_wchar * 15),
        ("numberOfSessions", c_int32),
        ("numCars", c_int32),
        ("carModel", ctypes.c_wchar * 33),
        ("track", ctypes.c_wchar * 33),
        ("playerName", ctypes.c_wchar * 33),
        ("playerSurname", ctypes.c_wchar * 33),
        ("playerNick", ctypes.c_wchar * 33),
        ("sectorCount", c_int32),
        ("maxTorque", c_float),
        ("maxPower", c_float),
        ("maxRpm", c_int32),
        ("maxFuel", c_float),
        ("suspensionMaxTravel", c_float * 4),
        ("tyreRadius", c_float * 4),
    ]


def telemetry_from_structs(phys: PhysicsPrefix, status: int, max_rpm: int,
                           tyre_radius_front: float, slip_scale: float = 1.0) -> Telemetry:
    """Pure mapping used by the live reader and by tests."""
    t = Telemetry()
    t.active = status == AC_LIVE
    t.speed_mps = abs(phys.speedKmh) / 3.6
    ws = phys.wheelAngularSpeed
    t.wheel_speed_front_radps = (abs(ws[0]) + abs(ws[1])) / 2.0
    t.rpm = float(phys.rpms)
    t.rpm_max = float(max_rpm)
    t.rpm_idle = 0.0
    t.throttle = float(phys.gas)
    t.brake = float(phys.brake)
    t.gear = int(phys.gear) - 1  # AC: 0 = reverse, 1 = neutral, 2 = first
    slip = phys.wheelSlip
    t.slip_front = max(abs(slip[0]), abs(slip[1])) * slip_scale
    t.slip_rear = max(abs(slip[2]), abs(slip[3])) * slip_scale
    if t.speed_mps > 1.0 and tyre_radius_front > 0.0:
        ratios = [(abs(ws[i]) * tyre_radius_front - t.speed_mps) / t.speed_mps for i in (0, 1)]
        t.slip_ratio_front = max(-2.0, min(ratios))
    t.rumble_front = 0.0
    t.surface_rumble_front = None
    t.abs_active = phys.abs > 0.0 and phys.brake > 0.05
    t.lateral_g = float(phys.accG[0])
    return t


class AssettoSource:
    name = "assetto"

    def __init__(self, slip_scale: float = 1.0):
        import mmap

        self._slip_scale = slip_scale
        self._phys_map = mmap.mmap(-1, ctypes.sizeof(PhysicsPrefix), "acpmf_physics")
        self._gfx_map = mmap.mmap(-1, ctypes.sizeof(GraphicsPrefix), "acpmf_graphics")
        self._static_map = mmap.mmap(-1, ctypes.sizeof(StaticPrefix), "acpmf_static")
        self._phys = PhysicsPrefix.from_buffer(self._phys_map)
        self._gfx = GraphicsPrefix.from_buffer(self._gfx_map)
        self._static = StaticPrefix.from_buffer(self._static_map)
        self._last_packet = -1
        self.packets = 0

    def poll(self) -> Optional[Telemetry]:
        packet = int(self._phys.packetId)
        if packet == self._last_packet:
            return None
        self._last_packet = packet
        self.packets += 1
        radius = self._static.tyreRadius
        front_radius = (float(radius[0]) + float(radius[1])) / 2.0
        return telemetry_from_structs(self._phys, int(self._gfx.status), int(self._static.maxRpm),
                                      front_radius, self._slip_scale)

    def close(self) -> None:
        # ctypes views must be dropped before the maps can close
        del self._phys, self._gfx, self._static
        self._phys_map.close()
        self._gfx_map.close()
        self._static_map.close()
