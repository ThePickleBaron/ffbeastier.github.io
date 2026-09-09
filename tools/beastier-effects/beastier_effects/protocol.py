"""Byte-level encoding of the FFBeast wheel vendor HID protocol.

Layout follows ``wheel_api.h`` shipped in the RC.26.1.1 wheel package and the
vendor's reference ``wheel_api.cpp``. Every report written to the device is
``REPORT_LENGTH`` bytes: one report id byte followed by a 64 byte payload.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from enum import IntEnum

USB_VID = 1115
WHEEL_PID_FS = 22999
VENDOR_INTERFACE = 0

REPORT_LENGTH = 65
FORCE_SCALE = 10000
FORCE_DROP_SCALE = 100


class ReportType(IntEnum):
    HARDWARE_SETTINGS_FEATURE = 0x21
    EFFECT_SETTINGS_FEATURE = 0x22
    FIRMWARE_LICENSE_FEATURE = 0x25
    GPIO_SETTINGS_FEATURE = 0xA1
    ADC_SETTINGS_FEATURE = 0xA2
    GENERIC_INPUT_OUTPUT = 0xA3


class DataCommand(IntEnum):
    REBOOT = 0x01
    SAVE_SETTINGS = 0x02
    DFU_MODE = 0x03
    RESET_CENTER = 0x04
    OVERRIDE_DATA = 0x10
    FIRMWARE_ACTIVATION_DATA = 0x13
    SETTINGS_FIELD_DATA = 0x14


class SettingsField(IntEnum):
    DIRECT_X_CONSTANT_DIRECTION = 0
    DIRECT_X_SPRING_STRENGTH = 1
    DIRECT_X_CONSTANT_STRENGTH = 2
    DIRECT_X_PERIODIC_STRENGTH = 3
    TOTAL_EFFECT_STRENGTH = 4
    MOTION_RANGE = 5
    SOFT_STOP_STRENGTH = 6
    SOFT_STOP_RANGE = 7
    STATIC_DAMPENING_STRENGTH = 8
    SOFT_STOP_DAMPENING_STRENGTH = 9
    DYNAMIC_DAMPENING_STRENGTH = 10
    FORCE_ENABLED = 11
    DEBUG_TORQUE = 12
    AMPLIFIER_GAIN = 13
    CALIBRATION_MAGNITUDE = 15
    CALIBRATION_SPEED = 16
    POWER_LIMIT = 17
    BRAKING_LIMIT = 18
    POSITION_SMOOTHING = 19
    SPEED_BUFFER_SIZE = 20
    ENCODER_DIRECTION = 21
    FORCE_DIRECTION = 22
    POLE_PAIRS = 23
    ENCODER_CPR = 24
    P_GAIN = 25
    I_GAIN = 26
    EXTENSION_MODE = 27
    PIN_MODE = 28
    BUTTON_MODE = 29
    SPI_MODE = 30
    SPI_LATCH_MODE = 31
    SPI_LATCH_DELAY = 32
    SPI_CLK_PULSE_LENGTH = 33
    ADC_MIN_DEAD_ZONE = 34
    ADC_MAX_DEAD_ZONE = 35
    ADC_TO_BUTTON_LOW = 36
    ADC_TO_BUTTON_HIGH = 37
    ADC_SMOOTHING = 38
    ADC_INVERT = 39
    RESET_CENTER_ON_Z0 = 41
    INTEGRATED_SPRING_STRENGTH = 43


_SETTING_FORMATS = {
    "int8": "<b",
    "uint8": "<B",
    "int16": "<h",
    "uint16": "<H",
    "float": "<f",
}

_DIRECT_CONTROL = struct.Struct("<hhhB")
_DEVICE_STATE = struct.Struct("<BBBBBhh")
_HARDWARE_SETTINGS = struct.Struct("<HHBBBBBBBBBBbbB")
_EFFECT_SETTINGS = struct.Struct("<HHHBBBBbBBB")


def clamp(value: float, low: float, high: float) -> float:
    return low if value < low else high if value > high else value


def to_force_units(value: float) -> int:
    """Map a normalized -1..1 force to the protocol's signed 16-bit range."""
    return int(round(clamp(value, -1.0, 1.0) * FORCE_SCALE))


def from_force_units(value: int) -> float:
    return value / FORCE_SCALE


def generic_report(command: DataCommand, payload: bytes = b"") -> bytes:
    """Build a 65 byte generic input/output report."""
    body = bytes((int(ReportType.GENERIC_INPUT_OUTPUT), int(command))) + payload
    if len(body) > REPORT_LENGTH:
        raise ValueError(f"payload too long: {len(body) - 2} bytes")
    return body.ljust(REPORT_LENGTH, b"\0")


def command_report(command: DataCommand) -> bytes:
    if command in (DataCommand.OVERRIDE_DATA, DataCommand.SETTINGS_FIELD_DATA,
                   DataCommand.FIRMWARE_ACTIVATION_DATA):
        raise ValueError(f"{command.name} carries data and is not a bare command")
    return generic_report(command)


def setting_report(field: SettingsField, value: float | int, kind: str, index: int = 0) -> bytes:
    """Build a settings-field write. ``kind`` is one of int8/uint8/int16/uint16/float."""
    try:
        fmt = _SETTING_FORMATS[kind]
    except KeyError as exc:
        raise ValueError(f"unknown setting kind {kind!r}") from exc
    if not 0 <= index <= 255:
        raise ValueError("index must fit in one byte")
    payload = bytes((int(field), index)) + struct.pack(fmt, value)
    return generic_report(DataCommand.SETTINGS_FIELD_DATA, payload)


@dataclass(frozen=True)
class DirectControl:
    """Host-side force override. All forces are normalized -1..1, drop is 0..1."""

    spring: float = 0.0
    constant: float = 0.0
    periodic: float = 0.0
    force_drop: float = 0.0

    def to_report(self) -> bytes:
        payload = _DIRECT_CONTROL.pack(
            to_force_units(self.spring),
            to_force_units(self.constant),
            to_force_units(self.periodic),
            int(round(clamp(self.force_drop, 0.0, 1.0) * FORCE_DROP_SCALE)),
        )
        return generic_report(DataCommand.OVERRIDE_DATA, payload)

    @classmethod
    def from_report(cls, report: bytes) -> "DirectControl":
        if len(report) < 2 + _DIRECT_CONTROL.size:
            raise ValueError("report too short")
        if report[0] != ReportType.GENERIC_INPUT_OUTPUT or report[1] != DataCommand.OVERRIDE_DATA:
            raise ValueError("not a direct control report")
        spring, constant, periodic, drop = _DIRECT_CONTROL.unpack_from(report, 2)
        return cls(from_force_units(spring), from_force_units(constant),
                   from_force_units(periodic), drop / FORCE_DROP_SCALE)


ZERO_CONTROL = DirectControl()


@dataclass(frozen=True)
class FirmwareVersion:
    release_type: int
    major: int
    minor: int
    patch: int

    def __str__(self) -> str:
        kind = {0: "RC", 1: "RELEASE"}.get(self.release_type, str(self.release_type))
        return f"{kind}.{self.major}.{self.minor}.{self.patch}"


@dataclass(frozen=True)
class DeviceState:
    version: FirmwareVersion
    is_registered: bool
    position: float
    torque: float

    @classmethod
    def from_report(cls, data: bytes, has_report_id: bool = True) -> "DeviceState":
        offset = 1 if has_report_id else 0
        if len(data) < offset + _DEVICE_STATE.size:
            raise ValueError("state report too short")
        rt, major, minor, patch, registered, position, torque = _DEVICE_STATE.unpack_from(data, offset)
        return cls(FirmwareVersion(rt, major, minor, patch), bool(registered),
                   from_force_units(position), from_force_units(torque))


@dataclass(frozen=True)
class HardwareSettings:
    encoder_cpr: int
    integral_gain: int
    proportional_gain: int
    force_enabled: bool
    debug_torque: bool
    amplifier_gain: int
    calibration_magnitude: int
    calibration_speed: int
    power_limit: int
    braking_limit: int
    position_smoothing: int
    speed_buffer_size: int
    encoder_direction: int
    force_direction: int
    pole_pairs: int

    @classmethod
    def from_feature_report(cls, data: bytes) -> "HardwareSettings":
        if len(data) < 1 + _HARDWARE_SETTINGS.size:
            raise ValueError("hardware settings report too short")
        if data[0] != ReportType.HARDWARE_SETTINGS_FEATURE:
            raise ValueError("wrong report id for hardware settings")
        f = _HARDWARE_SETTINGS.unpack_from(data, 1)
        return cls(f[0], f[1], f[2], bool(f[3]), bool(f[4]), f[5], f[6], f[7], f[8],
                   f[9], f[10], f[11], f[12], f[13], f[14])


@dataclass(frozen=True)
class EffectSettings:
    motion_range: int
    static_dampening: int
    soft_stop_dampening: int
    total_effect_strength: int
    integrated_spring: int
    soft_stop_range: int
    soft_stop_strength: int
    directx_constant_direction: int
    directx_spring: int
    directx_constant: int
    directx_periodic: int

    @classmethod
    def from_feature_report(cls, data: bytes) -> "EffectSettings":
        if len(data) < 1 + _EFFECT_SETTINGS.size:
            raise ValueError("effect settings report too short")
        if data[0] != ReportType.EFFECT_SETTINGS_FEATURE:
            raise ValueError("wrong report id for effect settings")
        return cls(*_EFFECT_SETTINGS.unpack_from(data, 1))
