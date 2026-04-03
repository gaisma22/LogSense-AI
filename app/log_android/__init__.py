# app/log_android/__init__.py
# Clean namespace initializer for the Android logging subsystem.

from .adb_device import (
    adb_exists,
    adb_path,
    list_devices,
    get_device_info,
    get_device_props,
)

from .adb_stream import (
    stream_logcat,
)

__all__ = [
    "adb_exists",
    "adb_path",
    "list_devices",
    "get_device_info",
    "get_device_props",
    "stream_logcat",
]
