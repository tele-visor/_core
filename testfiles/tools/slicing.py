"""Slicing utilities for ectocore patch generation (testfiles-only).

This module keeps transient detection intentionally simple so it works in a
GitHub Codespace without heavy dependencies. It prioritizes deterministic
slice placement based on a configurable amplitude threshold and minimum gap.
It also supports explicit slice boundaries supplied in config files.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence

import numpy as np
import soundfile as sf


@dataclass
class Slice:
    start: int
    stop: int

    @property
    def length(self) -> int:
        return max(0, self.stop - self.start)


@dataclass
class SlicePlan:
    slices: List[Slice]
    sample_rate: int
    mono: bool


class SliceConfigError(ValueError):
    """Raised when the slicing config cannot be fulfilled."""


DEFAULT_THRESHOLD_DB = -32.0
DEFAULT_MIN_GAP_MS = 40.0
DEFAULT_WINDOW_MS = 12.0
DEFAULT_FADE_MS = 0.0
DEFAULT_GAIN_DB = 0.0


def load_audio(path: Path, force_mono: bool) -> tuple[np.ndarray, int]:
    """Load audio as float32 and optionally collapse to mono."""
    data, sr = sf.read(path, always_2d=True)
    if force_mono:
        data = data.mean(axis=1, keepdims=True)
    return data.astype(np.float32), sr


def _to_samples(value_seconds: float, sample_rate: int) -> int:
    return int(round(value_seconds * sample_rate))


def _ms_to_samples(value_ms: float, sample_rate: int) -> int:
    return int(round(value_ms / 1000.0 * sample_rate))


def _find_transients(
    mono_signal: np.ndarray,
    sample_rate: int,
    threshold_db: float,
    min_gap_ms: float,
    window_ms: float,
    max_slices: int,
) -> List[int]:
    envelope = np.abs(mono_signal)
    if envelope.size == 0:
        return [0]

    # Smooth to reduce single-sample spikes.
    window = int(max(1, round(sample_rate * window_ms / 1000.0)))
    kernel = np.ones(window) / float(window)
    smoothed = np.convolve(envelope, kernel, mode="same")

    peak = smoothed.max()
    if peak == 0:
        return [0]
    threshold = peak * 10 ** (threshold_db / 20.0)

    min_gap = int(round(sample_rate * min_gap_ms / 1000.0))
    indices: List[int] = []
    last = -min_gap
    for idx, value in enumerate(smoothed):
        if value >= threshold and (idx - last) >= min_gap:
            indices.append(idx)
            last = idx
            if len(indices) >= max_slices:
                break
    return indices or [0]


def plan_slices(
    signal: np.ndarray,
    sample_rate: int,
    *,
    strategy: str,
    target_slices: int,
    min_gap_ms: float = DEFAULT_MIN_GAP_MS,
    threshold_db: float = DEFAULT_THRESHOLD_DB,
    window_ms: float = DEFAULT_WINDOW_MS,
    explicit_seconds: Sequence[float] | None = None,
) -> SlicePlan:
    mono_signal = signal[:, 0] if signal.ndim == 2 else signal

    if strategy == "explicit" and explicit_seconds:
        starts = sorted({_to_samples(v, sample_rate) for v in explicit_seconds})
        if 0 not in starts:
            starts.insert(0, 0)
    else:
        starts = _find_transients(
            mono_signal,
            sample_rate,
            threshold_db=threshold_db,
            min_gap_ms=min_gap_ms,
            window_ms=window_ms,
            max_slices=target_slices,
        )
        if starts[0] != 0:
            starts.insert(0, 0)

    # Cap to the requested number of slices.
    starts = starts[:target_slices]
    # Ensure the last slice reaches the end of the buffer.
    total_len = len(mono_signal)
    if starts[-1] >= total_len:
        raise SliceConfigError("Slice start exceeds buffer length")

    stops = starts[1:] + [total_len]
    slices = [Slice(start=s, stop=e) for s, e in zip(starts, stops) if e > s]

    if len(slices) == 0:
        raise SliceConfigError("No slices could be created")

    return SlicePlan(slices=slices, sample_rate=sample_rate, mono=signal.shape[1] == 1)


def plan_manual_slices(
    slice_cfg: Sequence[dict], sample_rate: int, total_length: int, mono: bool
) -> SlicePlan:
    """Plan slices based on explicit millisecond boundaries from config."""

    def _resolve_edge(key: str, entry: dict) -> int:
        if key not in entry:
            raise SliceConfigError(f"Manual slice is missing '{key}'")
        return _ms_to_samples(float(entry[key]), sample_rate)

    starts: List[int] = []
    stops: List[int] = []
    for entry in slice_cfg:
        start = _resolve_edge("start_ms", entry)
        end = _resolve_edge("end_ms", entry)
        if end <= start:
            raise SliceConfigError("Manual slice end_ms must be greater than start_ms")
        starts.append(start)
        stops.append(end)

    # Ensure ordering and clamp to buffer length.
    combined = sorted(zip(starts, stops), key=lambda x: x[0])
    normalized: List[Slice] = []
    last_stop = 0
    for start, stop in combined:
        if start < last_stop:
            raise SliceConfigError("Manual slices must be non-overlapping and ordered")
        start = max(0, min(start, total_length - 1))
        stop = max(start + 1, min(stop, total_length))
        normalized.append(Slice(start=start, stop=stop))
        last_stop = stop

    if not normalized:
        raise SliceConfigError("No manual slices provided")

    return SlicePlan(slices=normalized, sample_rate=sample_rate, mono=mono)


def export_slices(
    signal: np.ndarray,
    sample_rate: int,
    plan: SlicePlan,
    output_dir: Path,
    base_id: int,
    variation: int,
    slice_settings: Sequence[dict] | None = None,
) -> List[tuple[int, Path]]:
    """Write slice WAV files and return (slice_index, path) tuples."""
    output_dir.mkdir(parents=True, exist_ok=True)
    written: List[tuple[int, Path]] = []
    settings = list(slice_settings) if slice_settings is not None else [{}] * len(plan.slices)
    if len(settings) != len(plan.slices):
        raise SliceConfigError("slice_settings length must match planned slices")

    for local_idx, (slc, opts) in enumerate(zip(plan.slices, settings)):
        data = np.copy(signal[slc.start : slc.stop])
        gain_db = float(opts.get("gain_db", DEFAULT_GAIN_DB))
        fade_in_ms = float(opts.get("fade_in_ms", DEFAULT_FADE_MS))
        fade_out_ms = float(opts.get("fade_out_ms", DEFAULT_FADE_MS))

        if gain_db:
            data *= 10 ** (gain_db / 20.0)

        if fade_in_ms > 0:
            fade_in = min(len(data), _ms_to_samples(fade_in_ms, sample_rate))
            if fade_in > 1:
                ramp = np.linspace(0.0, 1.0, fade_in, endpoint=True)
                data[:fade_in] *= ramp[:, None]

        if fade_out_ms > 0:
            fade_out = min(len(data), _ms_to_samples(fade_out_ms, sample_rate))
            if fade_out > 1:
                ramp = np.linspace(1.0, 0.0, fade_out, endpoint=True)
                data[-fade_out:] *= ramp[:, None]

        fname = f"{base_id + local_idx}.{variation}.wav"
        dest = output_dir / fname
        # Firmware expects PCM16; cast and clip to match binary size assumptions.
        pcm_data = np.clip(data, -1.0, 1.0).astype(np.float32)
        sf.write(dest, pcm_data, sample_rate, subtype="PCM_16")
        written.append((base_id + local_idx, dest))
    return written

