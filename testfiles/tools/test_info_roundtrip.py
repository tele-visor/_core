"""Byte-for-byte regression test for `.wav.info` packing.

This mirrors the C layout in `lib/sampleinfo.h` and the Go writer in
`core/src/zeptocore/zeptocorebinary.go`. Run locally to ensure the Python
writer matches the firmware serialization exactly.
"""
from __future__ import annotations

import struct

from ectocore_info import InfoContent, InfoFlags, build_payload


def _pack_flags(flags: InfoFlags) -> int:
    bpm = min(max(int(flags.bpm), 0), 510)
    play_mode = min(max(int(flags.play_mode), 0), 7)
    one_shot = 1 if flags.one_shot else 0
    tempo_match = 1 if flags.tempo_match else 0
    oversampling = 1 if flags.oversampling else 0
    num_channels = 1 if flags.num_channels else 0
    version = min(max(int(flags.version), 0), 0x7F)
    reserved = min(max(int(flags.reserved), 0), 0x1FF)
    packed = bpm
    packed |= play_mode << 9
    packed |= one_shot << 12
    packed |= tempo_match << 13
    packed |= oversampling << 14
    packed |= num_channels << 15
    packed |= version << 16
    packed |= reserved << 23
    return packed


def _normalize_transients(levels):
    normalized = []
    for level in levels:
        bucket = []
        for raw in level:
            value = int(raw)
            if value <= 0:
                continue
            scaled = value // 16
            if scaled > 0xFFFF:
                scaled = 0
            if scaled == 0:
                continue
            bucket.append(scaled)
            if len(bucket) >= 16:
                break
        normalized.append(bucket)
    while len(normalized) < 3:
        normalized.append([])
    return normalized[:3]


def pack_like_firmware(content: InfoContent) -> bytes:
    transients = _normalize_transients(content.transients)
    slice_num = len(content.slice_starts)
    header = struct.pack(
        "<IIHB",
        int(content.size_bytes),
        _pack_flags(content.flags),
        (int(content.flags.splice_trigger) & 0x7FFF)
        | ((1 if content.flags.splice_variable else 0) << 15),
        slice_num,
    )

    buf = bytearray(header)
    for v in content.slice_starts:
        buf.extend(struct.pack("<i", int(v)))
    for v in content.slice_stops:
        buf.extend(struct.pack("<i", int(v)))
    for v in content.slice_types:
        buf.extend(struct.pack("<b", int(v)))

    if content.flags.version >= 1:
        for level in transients:
            buf.extend(struct.pack("<H", len(level)))
        for level in transients:
            for item in level:
                buf.extend(struct.pack("<H", item))
    return bytes(buf)


def test_bytes_match() -> None:
    flags = InfoFlags(
        bpm=155,
        play_mode=0,
        one_shot=True,
        tempo_match=True,
        oversampling=False,
        num_channels=0,
        version=1,
        reserved=0,
        splice_trigger=24,
        splice_variable=False,
    )
    content = InfoContent(
        size_bytes=6400,
        flags=flags,
        slice_starts=[0],
        slice_stops=[6396],
        slice_types=[1],
        transients=[[480, 960], [1200], []],
    )

    firmware_bytes = pack_like_firmware(content)
    python_bytes = build_payload(content)
    assert firmware_bytes == python_bytes


if __name__ == "__main__":
    test_bytes_match()
    print("Firmware-compatible packing confirmed (python == reference bytes)")
