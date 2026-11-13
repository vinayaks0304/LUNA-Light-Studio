"""Portable saved-colour palette format for LUNA's existing QSettings store.

This module intentionally has no Qt or BLE dependency. It never sends commands to
hardware; applying a swatch goes through MainWindow._set_colour as usual.
"""

import json
import re

_HEX = re.compile(r"^#?[0-9a-fA-F]{6}$")
MAX_NAME_LENGTH = 36


def normalise_hex(value):
    """Return canonical #RRGGBB or None for an invalid colour."""
    if not isinstance(value, str) or not _HEX.fullmatch(value):
        return None
    return "#" + value.lstrip("#").upper()


def clean_name(value, fallback):
    """Keep saved names readable, even if settings were manually edited."""
    if not isinstance(value, str):
        return fallback
    value = " ".join(value.split())[:MAX_NAME_LENGTH].strip()
    return value or fallback


def load_palette(value):
    """Read version-one JSON safely; skip malformed/duplicate entries."""
    if not isinstance(value, str):
        return []
    try:
        data = json.loads(value)
    except (ValueError, TypeError):
        return []
    if not isinstance(data, list):
        return []
    entries = []
    seen = set()
    for item in data:
        if not isinstance(item, dict):
            continue
        colour = normalise_hex(item.get("hex"))
        if colour is None or colour in seen:
            continue
        name = clean_name(item.get("name"), colour)
        entries.append({"name": name, "hex": colour})
        seen.add(colour)
    return entries


def dump_palette(entries):
    """Return a stable, human-readable JSON string for QSettings."""
    return json.dumps(load_palette(json.dumps(entries, ensure_ascii=False)),
                      ensure_ascii=False, separators=(",", ":"))
