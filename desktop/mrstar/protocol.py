"""Packets recovered from the user-provided Mr Star APK (com.frok.mrstar).

These are APK-derived formats, not proof that every feature works on every firmware.
"""
from dataclasses import dataclass
from datetime import datetime
import colorsys


def _byte(value, name):
    value = int(value)
    if not 0 <= value <= 255:
        raise ValueError(f"{name} must be between 0 and 255")
    return value


def _hsv_payload(hex_colour):
    value = hex_colour.strip().lstrip('#')
    if len(value) != 6:
        raise ValueError('Expected #RRGGBB')
    r, g, b = (int(value[i:i+2], 16) / 255 for i in (0, 2, 4))
    h, s, _ = colorsys.rgb_to_hsv(r, g, b)
    hue = round(h * 360) % 360
    saturation = round(s * 1000)
    return (hue >> 8, hue & 255, saturation >> 8, saturation & 255, 0, 0)


def colour_frame(value):
    return bytes((0xBC, 0x04, 0x06, *_hsv_payload(value), 0x55))


def microphone_colour_frame(value):
    """Host microphone colour (VoiceUtils uses opcode 0x09)."""
    return bytes((0xBC, 0x09, 0x06, *_hsv_payload(value), 0x55))


def brightness_frame(level):
    level = max(0, min(1000, int(level)))
    return bytes((0xBC, 0x05, 0x06, level >> 8, level & 255, 0, 0, 0, 0, 0x55))


def power_frame(on):
    return bytes((0xBC, 0x01, 0x01, int(bool(on)), 0x55))


def pixel_count_frame(count):
    count = max(8, min(300, int(count)))
    return bytes((0xBC, 0x03, 0x02, count >> 8, count & 255, 0x55))


def channel_order_frame(position):
    position = int(position)
    if not 0 <= position < 6:
        raise ValueError('Channel order index must be 0–5')
    return bytes((0xBC, 0x02, 0x01, position + 1, 0x55))


def effect_frame(effect_id):
    effect_id = int(effect_id)
    if not 1 <= effect_id <= 65534:
        raise ValueError('Effect ID out of range')
    # Match ModeFragment: unusual divisor 255, not 256.
    return bytes((0xBC, 0x06, 0x02, effect_id // 255, effect_id % 255, 0x55))


def effect_speed_frame(speed):
    speed = int(speed)
    if not 1 <= speed <= 100:
        raise ValueError('Effect speed must be 1–100')
    return bytes((0xBC, 0x08, 0x01, speed, 0x55))


def effect_direction_frame(forward):
    # Android switch checked=True sends 0, unchecked sends 1.
    return bytes((0xBC, 0x07, 0x01, 0 if forward else 1, 0x55))


def microphone_source_frame(device_microphone):
    # Android's "Device mic" = 1; "Phone mic" = 0.
    return bytes((0xBC, 0x0F, 0x01, 1 if device_microphone else 0, 0x55))


MICROPHONE_MODES = {'Classic': 1, 'Soft': 2, 'Dynamic': 3, 'Disco': 4}


def microphone_mode_frame(mode):
    if mode not in MICROPHONE_MODES:
        raise ValueError('Unknown microphone mode')
    return bytes((0xBC, 0x11, 0x01, MICROPHONE_MODES[mode], 0x55))


def microphone_sensitivity_frame(level):
    level = int(level)
    if not 0 <= level <= 100:
        raise ValueError('Sensitivity must be 0–100')
    return bytes((0xBC, 0x12, 0x01, level, 0x55))


def clock_frame(now=None):
    """Exact 12-byte frame used by TimerUtils; weekday follows 0x55."""
    now = now or datetime.now()
    return bytes((0xBC, 0x0B, 0x07, now.year >> 8, now.year & 255,
                  now.month, now.day, now.hour, now.minute, now.second,
                  0x55, now.isoweekday()))


def timer_read_frame():
    return bytes.fromhex('BC 0C 01 01 55')


def weekday_mask(days, enabled=True):
    """Monday is bit 0; Sunday is bit 6. Bit 7 is Android's disabled flag."""
    if len(days) != 7:
        raise ValueError('Provide seven weekday flags, Monday first')
    mask = sum((1 << index) for index, selected in enumerate(days) if selected)
    return mask | (0x00 if enabled else 0x80)


def timer_frame(kind, enabled, days, hour, minute):
    if kind not in ('on', 'off'):
        raise ValueError("Timer kind must be 'on' or 'off'")
    hour, minute = int(hour), int(minute)
    if not 0 <= hour < 24 or not 0 <= minute < 60:
        raise ValueError('Invalid schedule time')
    return bytes((0xBC, 0x0D, 0x06, 0x01, 1 if kind == 'on' else 0,
                  int(bool(enabled)), weekday_mask(days, enabled), hour, minute, 0x55))


@dataclass(frozen=True)
class TimerState:
    kind: str
    enabled: bool
    weekdays: tuple
    hour: int
    minute: int


def parse_timer_notification(data):
    """Parse the 0x0D timer notification described in TimerFragment.

    Returns None for unrelated/invalid notifications. Does not modify hardware.
    """
    if len(data) < 9 or data[0] != 0xBC or data[1] != 0x0D or data[3] != 0x01:
        return None
    if data[4] not in (0, 1) or data[5] not in (0, 1):
        return None
    if data[7] >= 24 or data[8] >= 60:
        return None
    return TimerState('on' if data[4] == 1 else 'off', bool(data[5]),
                      tuple(bool(data[6] & (1 << i)) for i in range(7)),
                      data[7], data[8])
