import struct
from pathlib import Path

import pytest

from beastier_effects.config import EffectConfig, config_from_dict, load_config
from beastier_effects.device import FakeWheelDevice
from beastier_effects.protocol import REPORT_LENGTH, DataCommand, DirectControl, ReportType


def test_fake_device_records_direct_control_and_commands():
    dev = FakeWheelDevice()
    dev.send_direct_control(DirectControl(periodic=0.5))
    dev.reset_center()
    assert len(dev.writes) == 2
    assert all(len(w) == REPORT_LENGTH for w in dev.writes)
    assert dev.last_control() == DirectControl(periodic=0.5)
    assert dev.writes[1][:2] == bytes((ReportType.GENERIC_INPUT_OUTPUT, DataCommand.RESET_CENTER))
    dev.close()
    assert dev.transport.closed


def test_device_rejects_wrong_length():
    dev = FakeWheelDevice()
    with pytest.raises(ValueError):
        dev.send(b"\xa3\x10")


def test_fake_device_reads_state_and_settings():
    dev = FakeWheelDevice()
    dev.transport.state_report = (bytes([0xA3]) + struct.pack("<BBBBBhh", 0, 26, 1, 1, 0, 1000, -2000)).ljust(65, b"\0")
    state = dev.read_state()
    assert state.position == pytest.approx(0.1)
    assert state.torque == pytest.approx(-0.2)
    dev.transport.feature_reports[ReportType.HARDWARE_SETTINGS_FEATURE] = (
        bytes([ReportType.HARDWARE_SETTINGS_FEATURE])
        + struct.pack("<HHBBBBBBBBBBbbB", 30000, 20, 5, 1, 0, 2, 5, 50, 40, 10, 0, 1, 1, 1, 15)
    ).ljust(65, b"\0")
    assert dev.read_hardware_settings().encoder_cpr == 30000


def test_config_defaults_and_overrides():
    cfg = config_from_dict({"total_gain": 0.3, "rumble": {"gain": 0.5, "enabled": False}})
    assert cfg.total_gain == 0.3
    assert cfg.rumble.gain == 0.5
    assert cfg.rumble.enabled is False
    assert cfg.texture == EffectConfig().texture


def test_config_rejects_unknown_keys_and_wrong_types():
    with pytest.raises(ValueError, match="unknown config key 'rumbel'"):
        config_from_dict({"rumbel": {}})
    with pytest.raises(ValueError, match="'abs.hz' must be float"):
        config_from_dict({"abs": {"hz": "fast"}})
    with pytest.raises(ValueError, match="'oversteer.sign' must be an integer"):
        config_from_dict({"oversteer": {"sign": True}})


def test_example_toml_loads_and_equals_defaults():
    example = Path(__file__).resolve().parents[1] / "effects.example.toml"
    cfg = load_config(example)
    assert cfg == EffectConfig()
