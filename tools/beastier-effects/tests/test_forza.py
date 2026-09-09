import struct

import pytest

from beastier_effects.telemetry.forza import DASH, SLED, parse_packet


def make_sled(**overrides):
    values = {
        "is_race_on": 1, "timestamp": 1234, "max_rpm": 7500.0, "idle_rpm": 800.0, "rpm": 4200.0,
        "acc": (2.0, 0.0, -1.0), "vel": (0.5, 0.0, 30.0), "angvel": (0.0, 0.1, 0.0),
        "ypr": (0.0, 0.0, 0.0), "susp": (0.5, 0.5, 0.5, 0.5),
        "slip_ratio": (0.05, 0.02, 0.1, 0.1), "wheel_rot": (90.0, 92.0, 91.0, 91.0),
        "rumble": (0, 0, 0, 0), "puddle": (0.0, 0.0, 0.0, 0.0),
        "surface": (0.1, 0.2, 0.0, 0.0), "slip_angle": (0.1, 0.1, 0.1, 0.1),
        "combined": (0.3, 0.4, 0.2, 0.2), "susp_m": (0.0, 0.0, 0.0, 0.0),
        "ordinal": 1, "car_class": 3, "pi": 500, "drivetrain": 1, "cylinders": 6,
    }
    values.update(overrides)
    v = values
    return SLED.pack(
        v["is_race_on"], v["timestamp"], v["max_rpm"], v["idle_rpm"], v["rpm"],
        *v["acc"], *v["vel"], *v["angvel"], *v["ypr"], *v["susp"], *v["slip_ratio"],
        *v["wheel_rot"], *v["rumble"], *v["puddle"], *v["surface"], *v["slip_angle"],
        *v["combined"], *v["susp_m"],
        v["ordinal"], v["car_class"], v["pi"], v["drivetrain"], v["cylinders"],
    )


def make_dash(speed=31.0, accel=200, brake=0, gear=4):
    return DASH.pack(
        0.0, 0.0, 0.0, speed, 100.0, 200.0, 80.0, 80.0, 80.0, 80.0, 0.0, 0.5, 100.0,
        0.0, 0.0, 0.0, 0.0, 2, 1, accel, brake, 0, 0, gear, 0, 0, 0,
    )


def test_struct_sizes_match_forza_documentation():
    assert SLED.size == 232
    assert DASH.size == 79


def test_sled_only_packet():
    t = parse_packet(make_sled())
    assert t is not None
    assert t.active is True
    assert t.rpm == 4200.0
    assert t.rpm_max == 7500.0
    assert t.cylinders == 6
    assert t.speed_mps == pytest.approx((0.5 ** 2 + 30.0 ** 2) ** 0.5)
    assert t.brake is None and t.throttle is None
    assert t.slip_front == pytest.approx(0.4)
    assert t.slip_rear == pytest.approx(0.2)
    assert t.slip_ratio_front == pytest.approx(0.02)
    assert t.surface_rumble_front == pytest.approx(0.2)
    assert t.wheel_speed_front_radps == pytest.approx(91.0)
    assert t.lateral_g == pytest.approx(2.0 / 9.81)
    assert t.rumble_front == 0.0


def test_rumble_and_negative_slip_ratio():
    t = parse_packet(make_sled(rumble=(1, 0, 0, 0), slip_ratio=(-0.7, -0.2, 0.0, 0.0)))
    assert t.rumble_front == pytest.approx(0.5)
    assert t.slip_ratio_front == pytest.approx(-0.7)


def test_motorsport_dash_packet_reads_pedals_and_speed():
    packet = make_sled() + make_dash(speed=31.0, accel=255, brake=51, gear=4)
    assert len(packet) == 311
    t = parse_packet(packet)
    assert t.speed_mps == pytest.approx(31.0)
    assert t.throttle == pytest.approx(1.0)
    assert t.brake == pytest.approx(0.2)
    assert t.gear == 4


def test_motorsport_2023_extended_dash_packet():
    packet = make_sled() + make_dash(speed=12.0) + bytes(20)
    assert len(packet) == 331
    t = parse_packet(packet)
    assert t.speed_mps == pytest.approx(12.0)


def test_horizon_dash_packet_has_12_byte_offset():
    packet = make_sled() + bytes(12) + make_dash(speed=45.0, brake=255)
    assert len(packet) == 323
    t = parse_packet(packet)
    assert t.speed_mps == pytest.approx(45.0)
    assert t.brake == pytest.approx(1.0)
    packet_h4 = packet + b"\0"
    assert parse_packet(packet_h4).speed_mps == pytest.approx(45.0)


def test_menu_packet_is_inactive():
    t = parse_packet(make_sled(is_race_on=0))
    assert t.active is False


def test_short_packet_is_ignored():
    assert parse_packet(b"\0" * 100) is None
