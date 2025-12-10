"""Helpers to write Ectocore/Zeptocore-compatible `.wav.info` files.

This module mirrors the on-device structs defined in ``lib/sampleinfo.h`` and
the writer in ``core/src/zeptocore/zeptocorebinary.go``. Packing is
little-endian and matches the exact byte layout used by the firmware.
"""
from __future__ import annotations

import io
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Sequence


@dataclass
class InfoFlags:
    bpm: int
    play_mode: int = 0
    one_shot: bool = True
    tempo_match: bool = True
    oversampling: bool = False
    num_channels: int = 0  # 0=mono, 1=stereo
    version: int = 1
    reserved: int = 0
    splice_trigger: int = 24
    splice_variable: bool = False


@dataclass
class InfoContent:
    size_bytes: int
    flags: InfoFlags
    slice_starts: Sequence[int]
    slice_stops: Sequence[int]
    slice_types: Sequence[int]
    transients: List[List[int]] = field(default_factory=lambda: [[], [], []])


SAMPLEINFOPACK_SIZE = 4 + 4 + 2 + 1
MAX_TRANSIENTS = 16

# Byte layout (little-endian), mirroring SampleInfoPack in lib/sampleinfo.h:
# 0-3   : uint32 size (PCM data bytes)
# 4-7   : uint32 flags (bit-packed bpm/playmode/oneshot/tempo_match/oversampling/
#          num_channels/version/reserved)
# 8-9   : uint16 splice_info (bits 0-14 trigger, bit 15 variable)
# 10    : uint8 slice_num
# 11..  : slice_start[int32] * slice_num
#          slice_stop[int32] * slice_num
#          slice_type[int8]  * slice_num
#          (if version>=1) uint16 transient counts[3] + uint16 transient payloads


def _pack_flags(flags: InfoFlags) -> int:
    bpm = max(0, min(flags.bpm, 510))
    play_mode = max(0, min(flags.play_mode, 7))
    one_shot = 1 if flags.one_shot else 0
    tempo_match = 1 if flags.tempo_match else 0
    oversampling = 1 if flags.oversampling else 0
    num_channels = 1 if flags.num_channels else 0
    version = max(0, min(flags.version, 0x7F))
    reserved = max(0, min(flags.reserved, 0x1FF))

    packed = bpm
    packed |= play_mode << 9
    packed |= one_shot << 12
    packed |= tempo_match << 13
    packed |= oversampling << 14
    packed |= num_channels << 15
    packed |= version << 16
    packed |= reserved << 23
    return packed


def _pack_splice(flags: InfoFlags) -> int:
    trigger = max(0, min(flags.splice_trigger, 0x7FFF))
    variable = 1 if flags.splice_variable else 0
    return trigger | (variable << 15)


def _normalize_transients(levels: Iterable[Iterable[int]]) -> List[List[int]]:
    """Clamp and normalize transient arrays to firmware expectations.

    The firmware writes each bank as ``uint16`` counts followed by non-zero
    positions divided by 16 (see ``SampleInfoPack.WriteToFile`` in
    ``zeptocorebinary.go``). Values above ``0xFFFF`` become ``0`` after scaling
    and any zeros are omitted from the count.
    """

    normalized: List[List[int]] = []
    for level in levels:
        clamped = []
        for raw in level:
            value = int(raw)
            if value <= 0:
                continue
            scaled = value // 16
            if scaled > 0xFFFF:
                scaled = 0
            if scaled == 0:
                continue
            clamped.append(scaled)
            if len(clamped) >= MAX_TRANSIENTS:
                break
        normalized.append(clamped)

    # Ensure exactly three banks to mirror the C arrays.
    while len(normalized) < 3:
        normalized.append([])
    return normalized[:3]


def _calculate_size(content: InfoContent, normalized_transients: Sequence[Sequence[int]]) -> int:
    """Compute on-disk byte size for the header + payload (not WAV size)."""

    slice_num = len(content.slice_starts)
    base = SAMPLEINFOPACK_SIZE + slice_num * (4 + 4 + 1)
    if content.flags.version >= 1:
        counts_len = 3 * 2  # three uint16 counts
        payload_len = sum(len(t) for t in normalized_transients) * 2
        base += counts_len + payload_len
    return base


def build_payload(content: InfoContent) -> bytes:
    slice_num = len(content.slice_starts)
    if not (len(content.slice_starts) == len(content.slice_stops) == len(content.slice_types)):
        raise ValueError("slice arrays must have the same length")
    if slice_num > 255:
        raise ValueError("slice_num must fit in uint8 (max 255)")

    transients = _normalize_transients(content.transients)

    expected_struct_size = _calculate_size(content, transients)
    flags_val = _pack_flags(content.flags)
    splice_val = _pack_splice(content.flags)

    buf = io.BytesIO()
    buf.write(struct.pack("<I", int(content.size_bytes)))
    buf.write(struct.pack("<I", flags_val))
    buf.write(struct.pack("<H", splice_val))
    buf.write(struct.pack("<B", slice_num))

    for v in content.slice_starts:
        buf.write(struct.pack("<i", int(v)))
    for v in content.slice_stops:
        buf.write(struct.pack("<i", int(v)))
    for v in content.slice_types:
        buf.write(struct.pack("<b", int(v)))

    if content.flags.version >= 1:
        for level in transients:
            buf.write(struct.pack("<H", len(level)))
        for level in transients:
            for item in level:
                buf.write(struct.pack("<H", item))

    payload = buf.getvalue()
    if len(payload) != expected_struct_size:
        raise ValueError(
            f"payload size {len(payload)} does not match expected struct size {expected_struct_size}"
        )
    return payload


def write_info(path: Path, content: InfoContent) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = build_payload(content)
    path.write_bytes(payload)

