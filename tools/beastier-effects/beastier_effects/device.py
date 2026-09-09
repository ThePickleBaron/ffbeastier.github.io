"""HID transport for the FFBeast wheel vendor interface.

Two PyPI packages both import as ``hid``: ``hidapi`` (cython-hidapi, class
``hid.device``) and ``hid`` (pyhidapi, class ``hid.Device``). Both are handled.
``FakeWheelDevice`` records traffic for tests and dry runs.
"""

from __future__ import annotations

from typing import Any, Optional, Protocol

from .protocol import (
    REPORT_LENGTH,
    USB_VID,
    VENDOR_INTERFACE,
    WHEEL_PID_FS,
    DataCommand,
    DeviceState,
    DirectControl,
    EffectSettings,
    HardwareSettings,
    ReportType,
    command_report,
)


class WheelTransport(Protocol):
    def write(self, report: bytes) -> int: ...
    def read(self, length: int, timeout_ms: int) -> bytes: ...
    def get_feature_report(self, report_id: int, length: int) -> bytes: ...
    def close(self) -> None: ...


class _CythonHidapiTransport:
    """Adapter for the ``hidapi`` package (``hid.device``)."""

    def __init__(self, handle: Any):
        self._h = handle

    def write(self, report: bytes) -> int:
        return int(self._h.write(report))

    def read(self, length: int, timeout_ms: int) -> bytes:
        return bytes(self._h.read(length, timeout_ms))

    def get_feature_report(self, report_id: int, length: int) -> bytes:
        return bytes(self._h.get_feature_report(report_id, length))

    def close(self) -> None:
        self._h.close()


class _PyHidapiTransport:
    """Adapter for the ``hid`` package (``hid.Device``)."""

    def __init__(self, handle: Any):
        self._h = handle

    def write(self, report: bytes) -> int:
        return int(self._h.write(report))

    def read(self, length: int, timeout_ms: int) -> bytes:
        return bytes(self._h.read(length, timeout=timeout_ms))

    def get_feature_report(self, report_id: int, length: int) -> bytes:
        return bytes(self._h.get_feature_report(report_id, length))

    def close(self) -> None:
        self._h.close()


def find_wheel_path() -> Optional[bytes]:
    """Return the HID path of the wheel's vendor interface, or None."""
    import hid  # imported lazily so tests and dry runs do not need it

    for info in hid.enumerate(USB_VID, WHEEL_PID_FS):
        if info.get("interface_number") == VENDOR_INTERFACE:
            return info["path"]
    return None


def open_transport() -> WheelTransport:
    import hid

    path = find_wheel_path()
    if path is None:
        raise RuntimeError(
            "FFBeast wheel not found. Is it powered, calibrated and enumerated as a USB device?"
        )
    if hasattr(hid, "device"):
        handle = hid.device()
        handle.open_path(path)
        return _CythonHidapiTransport(handle)
    if hasattr(hid, "Device"):
        return _PyHidapiTransport(hid.Device(path=path))
    raise RuntimeError("unsupported 'hid' module; install the 'hidapi' package")


class WheelDevice:
    """High-level wrapper around the vendor interface."""

    def __init__(self, transport: WheelTransport):
        self._t = transport

    @classmethod
    def open(cls) -> "WheelDevice":
        return cls(open_transport())

    def send(self, report: bytes) -> int:
        if len(report) != REPORT_LENGTH:
            raise ValueError(f"report must be {REPORT_LENGTH} bytes, got {len(report)}")
        return self._t.write(report)

    def send_direct_control(self, control: DirectControl) -> int:
        return self.send(control.to_report())

    def send_command(self, command: DataCommand) -> int:
        return self.send(command_report(command))

    def reset_center(self) -> int:
        return self.send_command(DataCommand.RESET_CENTER)

    def read_state(self, timeout_ms: int = 100) -> Optional[DeviceState]:
        data = self._t.read(REPORT_LENGTH, timeout_ms)
        if not data:
            return None
        return DeviceState.from_report(data)

    def read_hardware_settings(self) -> HardwareSettings:
        data = self._t.get_feature_report(int(ReportType.HARDWARE_SETTINGS_FEATURE), REPORT_LENGTH)
        return HardwareSettings.from_feature_report(data)

    def read_effect_settings(self) -> EffectSettings:
        data = self._t.get_feature_report(int(ReportType.EFFECT_SETTINGS_FEATURE), REPORT_LENGTH)
        return EffectSettings.from_feature_report(data)

    def close(self) -> None:
        self._t.close()

    def __enter__(self) -> "WheelDevice":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


class FakeTransport:
    """In-memory transport that records writes and serves canned reads."""

    def __init__(self) -> None:
        self.writes: list[bytes] = []
        self.state_report: bytes = b""
        self.feature_reports: dict[int, bytes] = {}
        self.closed = False

    def write(self, report: bytes) -> int:
        self.writes.append(bytes(report))
        return len(report)

    def read(self, length: int, timeout_ms: int) -> bytes:
        return self.state_report[:length]

    def get_feature_report(self, report_id: int, length: int) -> bytes:
        return self.feature_reports.get(report_id, b"")[:length]

    def close(self) -> None:
        self.closed = True


class FakeWheelDevice(WheelDevice):
    """A ``WheelDevice`` backed by ``FakeTransport``; used by tests and ``--dry-run``."""

    def __init__(self) -> None:
        self.transport = FakeTransport()
        super().__init__(self.transport)

    @property
    def writes(self) -> list[bytes]:
        return self.transport.writes

    def last_control(self) -> Optional[DirectControl]:
        for report in reversed(self.writes):
            if report[1] == DataCommand.OVERRIDE_DATA:
                return DirectControl.from_report(report)
        return None
