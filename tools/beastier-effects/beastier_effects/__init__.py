"""Beastier Effects: telemetry-driven extra force feedback for the FFBeast DIY wheel."""

from .config import EffectConfig, load_config
from .device import FakeWheelDevice, WheelDevice
from .engine import EffectEngine
from .protocol import DirectControl, DeviceState

__all__ = [
    "DeviceState",
    "DirectControl",
    "EffectConfig",
    "EffectEngine",
    "FakeWheelDevice",
    "WheelDevice",
    "load_config",
]
__version__ = "0.1.0"
