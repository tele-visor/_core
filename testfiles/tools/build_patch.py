#!/usr/bin/env python3
"""Build Ectocore patch assets from a Python config (testfiles-only).

Usage:
    python testfiles/tools/build_patch.py testfiles/patches/example_patch/config.py
"""
from __future__ import annotations

import argparse
import importlib.util
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Sequence
from zipfile import ZIP_DEFLATED, ZipFile

# Support running as a standalone script (no installed package needed).
if __package__ is None or __package__ == "":  # pragma: no cover - runtime convenience
    TOOL_ROOT = Path(__file__).resolve().parent
    sys.path.append(str(TOOL_ROOT))
    import ectocore_info  # type: ignore
    from ectocore_info import InfoContent, InfoFlags  # type: ignore
    from slicing import (  # type: ignore
        SlicePlan,
        SliceConfigError,
        export_slices,
        load_audio,
        plan_manual_slices,
        plan_slices,
    )
else:  # pragma: no cover - normal package import
    from . import ectocore_info
    from .ectocore_info import InfoContent, InfoFlags
    from .slicing import (
        SlicePlan,
        SliceConfigError,
        export_slices,
        load_audio,
        plan_manual_slices,
        plan_slices,
    )

TYPE_DEFAULT = 0
TYPE_KICK = 1
TYPE_SNARE = 2
TYPE_TRANSIENT = 3
TYPE_RANDOM = 4


def _load_config(path: Path) -> Dict:
    """Import a config module and return the PATCH_CONFIG dict."""
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise ImportError(f"Cannot import config module from {path}")
    module = importlib.util.module_from_spec(spec)
    loader = spec.loader
    loader.exec_module(module)
    if not hasattr(module, "PATCH_CONFIG"):
        raise AttributeError(f"{path} must define PATCH_CONFIG")
    cfg = module.PATCH_CONFIG
    if not isinstance(cfg, dict):
        raise TypeError("PATCH_CONFIG must be a dict")
    # Return a shallow copy to avoid mutating the imported module.
    return dict(cfg)


def _clean_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def _labels_from_config(cfg: Dict) -> Dict[str, Sequence[int]]:
    labels = cfg.get("labels", {})

    def _as_list(value):
        if value is None:
            return []
        if value == "all":
            return "all"
        if isinstance(value, (int, float)):
            return [int(value)]
        return [int(v) for v in value]

    return {
        "kick": _as_list(labels.get("kick", [])),
        "snare": _as_list(labels.get("snare", [])),
        "transient": _as_list(labels.get("transient", [])),
        "random": _as_list(labels.get("random", [])),
    }


def _slice_type(idx: int, labels: Dict[str, Sequence[int]]) -> int:
    kick = labels["kick"]
    snare = labels["snare"]
    transient = labels["transient"]
    random_label = labels["random"]

    if idx in kick:
        return TYPE_KICK
    if idx in snare:
        return TYPE_SNARE
    if idx in transient:
        return TYPE_TRANSIENT
    if random_label == "all" or idx in random_label:
        return TYPE_RANDOM
    return TYPE_DEFAULT


def _transients_for_slice(slice_idx: int, cfg: Dict) -> List[List[int]]:
    per_slice = cfg.get("transients", {}).get("per_slice_ms", {})
    if isinstance(per_slice, dict):
        entry = per_slice.get(str(slice_idx)) or per_slice.get(slice_idx)
    else:
        entry = None

    def _ms_to_samples(values: Sequence[float] | None, sample_rate: int) -> List[int]:
        if not values:
            return []
        return [int(round(v / 1000.0 * sample_rate)) for v in values]

    sample_rate = cfg.get("_internal_sample_rate", 48000)
    level1 = _ms_to_samples(entry, sample_rate) if entry else []
    return [level1[:ectocore_info.MAX_TRANSIENTS], [], []]


def _slice_settings(cfg: Dict) -> List[Dict]:
    raw = cfg.get("slices") or []
    settings: List[Dict] = []
    for entry in raw:
        if not isinstance(entry, dict):
            raise SliceConfigError("Each entry in 'slices' must be a dict")
        settings.append(entry)
    return settings


def _manual_transients(slice_cfg: Dict, sample_rate: int) -> List[List[int]] | None:
    times = slice_cfg.get("transients_ms")
    if not times:
        return None
    samples = [int(round(float(v) / 1000.0 * sample_rate)) for v in times]
    return [samples[: ectocore_info.MAX_TRANSIENTS], [], []]


def build_from_config(config_path: Path) -> None:
    cfg = _load_config(config_path)
    patch_dir = config_path.parent
    patch_name = cfg.get("patch_name") or patch_dir.name

    flags_cfg = dict(cfg.get("flags", {}))
    if "bpm" in cfg and "bpm" not in flags_cfg:
        flags_cfg["bpm"] = cfg["bpm"]
    flags = InfoFlags(
        bpm=int(flags_cfg.get("bpm", 120)),
        play_mode=int(flags_cfg.get("play_mode", 0)),
        one_shot=bool(flags_cfg.get("one_shot", True)),
        tempo_match=bool(flags_cfg.get("tempo_match", True)),
        oversampling=bool(flags_cfg.get("oversampling", False)),
        num_channels=int(flags_cfg.get("num_channels", 0)),
        version=int(flags_cfg.get("version", 1)),
        reserved=int(flags_cfg.get("reserved", 0)),
        splice_trigger=int(flags_cfg.get("splice_trigger", 24)),
        splice_variable=bool(flags_cfg.get("splice_variable", False)),
    )

    source_name = cfg.get("source_wav") or cfg.get("source") or "source.wav"
    source = patch_dir / source_name
    if not source.exists():
        raise FileNotFoundError(f"Missing source wav at {source}")

    output_cfg = cfg.get("output", {})
    bank = output_cfg.get("bank", "bank1")
    start_index = int(output_cfg.get("start_index", 0))
    variation = int(output_cfg.get("variation", 0))

    wav_dir = patch_dir / "wav"
    info_dir = patch_dir / "info"
    _clean_dir(wav_dir)
    _clean_dir(info_dir)

    signal, sr = load_audio(source, force_mono=flags.num_channels == 0)
    cfg["_internal_sample_rate"] = sr

    slicing_cfg = cfg.get("slicing", {})
    slice_settings = _slice_settings(cfg)
    if slice_settings:
        plan = plan_manual_slices(
            slice_settings,
            sample_rate=sr,
            total_length=len(signal),
            mono=signal.shape[1] == 1,
        )
    else:
        plan = plan_slices(
            signal,
            sr,
            strategy=slicing_cfg.get("strategy", "transient"),
            target_slices=int(slicing_cfg.get("target_slices", 16)),
            min_gap_ms=float(slicing_cfg.get("min_gap_ms", 40.0)),
            threshold_db=float(slicing_cfg.get("threshold_db", -32.0)),
            window_ms=float(slicing_cfg.get("window_ms", 12.0)),
            explicit_seconds=slicing_cfg.get("explicit_seconds"),
        )

    slice_labels = _labels_from_config(cfg)
    slice_types = [_slice_type(i, slice_labels) for i in range(len(plan.slices))]

    written = export_slices(
        signal,
        sr,
        plan,
        wav_dir,
        base_id=start_index,
        variation=variation,
        slice_settings=slice_settings or None,
    )

    info_paths: List[Path] = []
    for (local_idx, (slice_idx, _wav_path)) in enumerate(written):
        manual_transients = None
        if slice_settings:
            manual_transients = _manual_transients(slice_settings[local_idx], sr)
        transients = manual_transients or _transients_for_slice(slice_idx - start_index, cfg)
        content = InfoContent(
            flags=flags,
            slice_starts=[0],
            slice_stops=[plan.slices[slice_idx - start_index].length],
            slice_types=[slice_types[slice_idx - start_index]],
            transients=transients,
        )
        info_path = info_dir / f"{slice_idx}.{variation}.wav.info"
        ectocore_info.write_info(info_path, content)
        info_paths.append(info_path)

    zip_path = patch_dir / "patch.zip"
    with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as zf:
        for _, wav_path in written:
            arcname = f"{patch_name}/{bank}/{wav_path.name}"
            zf.write(wav_path, arcname=arcname)
        for info_path in info_paths:
            arcname = f"{patch_name}/{bank}/{info_path.name}"
            zf.write(info_path, arcname=arcname)

    print(f"Wrote {len(written)} slices -> {wav_dir}")
    print(f"Wrote {len(info_paths)} info files -> {info_dir}")
    print(f"Created zip -> {zip_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build ectocore patch assets from a Python config")
    parser.add_argument("config", type=Path, help="Path to config.py under testfiles/patches/<name>/")
    args = parser.parse_args()
    try:
        build_from_config(args.config)
    except SliceConfigError as exc:
        sys.exit(f"Slicing failed: {exc}")
    except Exception as exc:  # pragma: no cover
        sys.exit(str(exc))

