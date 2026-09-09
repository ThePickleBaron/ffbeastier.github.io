import struct

import pytest

from beastier_effects.protocol import (
    REPORT_LENGTH,
    DataCommand,
    DeviceState,
    DirectControl,
    EffectSettings,
    HardwareSettings,
    ReportType,
    SettingsField,
    command_report,
    setting_report,
    to_force_units,
)


def test_direct_control_report_layout_matches_vendor_header():
    report = DirectControl(spring=0.5, constant=-0.25, periodic=1.0, force_drop=0.33).to_report()
    assert len(report) == REPORT_LENGTH
    assert report[0] == ReportType.GENERIC_INPUT_OUTPUT == 0xA3
    assert report[1] == DataCommand.OVERRIDE_DATA == 0x10
    spring, constant, periodic, drop = struct.unpack_from("<hhhB", report, 2)
    assert (spring, constant, periodic, drop) == (5000, -2500, 10000, 33)
    assert report[9:] == bytes(REPORT_LENGTH - 9)


def test_direct_control_clamps_out_of_range_values():
    report = DirectControl(spring=7.0, constant=-9.0, periodic=0.0, force_drop=3.0).to_report()
    spring, constant, periodic, drop = struct.unpack_from("<hhhB", report, 2)
    assert (spring, constant, periodic, drop) == (10000, -10000, 0, 100)


def test_direct_control_round_trip():
    original = DirectControl(spring=0.1234, constant=-0.5, periodic=0.9999, force_drop=0.42)
    decoded = DirectControl.from_report(original.to_report())
    assert decoded.spring == pytest.approx(0.1234, abs=1e-4)
    assert decoded.constant == pytest.approx(-0.5, abs=1e-4)
    assert decoded.periodic == pytest.approx(0.9999, abs=1e-4)
    assert decoded.force_drop == pytest.approx(0.42, abs=1e-2)


def test_to_force_units_rounding():
    assert to_force_units(0.00006) == 1
    assert to_force_units(-0.00006) == -1
    assert to_force_units(0.00004) == 0
    assert to_force_units(0.0) == 0


def test_command_reports():
    for cmd, byte in ((DataCommand.REBOOT, 1), (DataCommand.SAVE_SETTINGS, 2),
                      (DataCommand.DFU_MODE, 3), (DataCommand.RESET_CENTER, 4)):
        report = command_report(cmd)
        assert len(report) == REPORT_LENGTH
        assert report[:2] == bytes((0xA3, byte))
        assert not any(report[2:])


def test_data_carrying_commands_are_rejected_as_bare_commands():
    with pytest.raises(ValueError):
        command_report(DataCommand.OVERRIDE_DATA)


def test_setting_report_layout_matches_vendor_header():
    report = setting_report(SettingsField.ENCODER_CPR, 10000, "uint16")
    assert report[:4] == bytes((0xA3, 0x14, 24, 0))
    assert struct.unpack_from("<H", report, 4)[0] == 10000

    report = setting_report(SettingsField.PIN_MODE, 4, "uint8", index=3)
    assert report[:5] == bytes((0xA3, 0x14, 28, 3, 4))

    report = setting_report(SettingsField.ENCODER_DIRECTION, -1, "int8")
    assert report[4] == 0xFF

    report = setting_report(SettingsField.MOTION_RANGE, 900, "uint16")
    assert struct.unpack_from("<H", report, 4)[0] == 900


def test_setting_report_rejects_bad_kind_and_index():
    with pytest.raises(ValueError):
        setting_report(SettingsField.POWER_LIMIT, 1, "double")
    with pytest.raises(ValueError):
        setting_report(SettingsField.PIN_MODE, 1, "uint8", index=300)


def test_device_state_parse():
    payload = bytes([0xA3]) + struct.pack("<BBBBBhh", 0, 26, 1, 1, 1, -5000, 2500)
    payload = payload.ljust(REPORT_LENGTH, b"\0")
    state = DeviceState.from_report(payload)
    assert str(state.version) == "RC.26.1.1"
    assert state.is_registered is True
    assert state.position == pytest.approx(-0.5)
    assert state.torque == pytest.approx(0.25)


def test_hardware_settings_parse():
    body = struct.pack("<HHBBBBBBBBBBbbB", 10000, 20, 5, 1, 0, 2, 5, 50, 10, 10, 0, 1, 1, -1, 15)
    data = bytes([ReportType.HARDWARE_SETTINGS_FEATURE]) + body
    hw = HardwareSettings.from_feature_report(data.ljust(REPORT_LENGTH, b"\0"))
    assert hw.encoder_cpr == 10000
    assert hw.pole_pairs == 15
    assert hw.force_enabled is True
    assert hw.force_direction == -1
    with pytest.raises(ValueError):
        HardwareSettings.from_feature_report(bytes([0x22]) + body)


def test_effect_settings_parse():
    body = struct.pack("<HHHBBBBbBBB", 900, 10, 40, 100, 0, 12, 70, 1, 100, 100, 100)
    data = bytes([ReportType.EFFECT_SETTINGS_FEATURE]) + body
    fx = EffectSettings.from_feature_report(data.ljust(REPORT_LENGTH, b"\0"))
    assert fx.motion_range == 900
    assert fx.soft_stop_strength == 70
    assert fx.directx_constant_direction == 1
