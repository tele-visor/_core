"""Helpers to write Ectocore/Zeptocore-compatible `.wav.info` files.

Derived from `lib/sampleinfo.h` bitfields. Only used inside `testfiles/`.
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
    flags: InfoFlags
    slice_starts: Sequence[int]
    slice_stops: Sequence[int]
    slice_types: Sequence[int]
    transients: List[List[int]] = field(default_factory=lambda: [[], [], []])


SAMPLEINFOPACK_SIZE = 4 + 4 + 2 + 1
MAX_TRANSIENTS = 16


def _pack_flags(flags: InfoFlags) -> int:
    bpm = max(0, min(flags.bpm, 511))
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


def _clamp_transients(transients: Iterable[int]) -> List[int]:
    seq = [max(0, min(int(v), 0xFFFF)) for v in transients][:MAX_TRANSIENTS]
    return seq


def _calculate_size(content: InfoContent) -> int:
    slice_num = len(content.slice_starts)
    base = SAMPLEINFOPACK_SIZE + slice_num * (4 + 4 + 1)
    if content.flags.version >= 1:
        transient_sizes = sum(len(t) for t in content.transients)
        base += 6 + transient_sizes * 2
    return base


def build_payload(content: InfoContent) -> bytes:
    slice_num = len(content.slice_starts)
    if not (len(content.slice_starts) == len(content.slice_stops) == len(content.slice_types)):
        raise ValueError("slice arrays must have the same length")

    transients = [_clamp_transients(t) for t in content.transients]

    size = _calculate_size(content)
    flags_val = _pack_flags(content.flags)
    splice_val = _pack_splice(content.flags)

    buf = io.BytesIO()
    buf.write(struct.pack("<I", size))
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

    return buf.getvalue()


def write_info(path: Path, content: InfoContent) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = build_payload(content)
    path.write_bytes(payload)

