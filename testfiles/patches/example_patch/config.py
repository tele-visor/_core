"""Example patch configuration in Python form.

Drop a `source.wav` next to this file, then run the build script:

    python ../../tools/build_patch.py config.py
"""

PATCH_CONFIG = {
    "patch_name": "example_patch",
    "source": "source.wav",
    "bpm": 155,
    "output": {
        "bank": "bank1",
        "start_index": 0,
        "variation": 0,
    },
    "flags": {
        "play_mode": 0,
        "one_shot": True,
        "tempo_match": True,
        "oversampling": False,
        "num_channels": 0,  # 0 = mono, 1 = stereo
        "version": 1,
        "reserved": 0,
        "splice_trigger": 24,
        "splice_variable": False,
    },
    # Slicing hints used when `slices` is empty. Left here as a reference for
    # transient-driven slicing if you want to experiment.
    "slicing": {
        "strategy": "transient",
        "target_slices": 16,
        "min_gap_ms": 35.0,
        "threshold_db": -28.0,
        "window_ms": 10.0,
        "explicit_seconds": [],
    },
    "labels": {
        "kick": [0, 8],
        "snare": [4, 12],
        "transient": [2, 6, 10, 14],
        "random": "all",
    },
    # Manual slice grid for a 155 BPM loop (~387 ms per beat). Times are in ms.
    "slices": [
        {"name": "slice_01", "start_ms": 0.0, "end_ms": 420.0, "gain_db": 0.0, "fade_in_ms": 2.0, "fade_out_ms": 6.0, "transients_ms": [0.0]},
        {"name": "slice_02", "start_ms": 420.0, "end_ms": 780.0, "gain_db": 0.0, "fade_in_ms": 2.0, "fade_out_ms": 6.0},
        {"name": "slice_03", "start_ms": 780.0, "end_ms": 1120.0, "gain_db": 0.0, "fade_in_ms": 2.0, "fade_out_ms": 6.0, "transients_ms": [18.0]},
        {"name": "slice_04", "start_ms": 1120.0, "end_ms": 1460.0, "gain_db": -0.5, "fade_in_ms": 2.0, "fade_out_ms": 6.0},
        {"name": "slice_05", "start_ms": 1460.0, "end_ms": 1800.0, "gain_db": 0.0, "fade_in_ms": 2.5, "fade_out_ms": 8.0, "transients_ms": [4.0]},
        {"name": "slice_06", "start_ms": 1800.0, "end_ms": 2140.0, "gain_db": 0.0, "fade_in_ms": 2.5, "fade_out_ms": 8.0},
        {"name": "slice_07", "start_ms": 2140.0, "end_ms": 2480.0, "gain_db": 0.0, "fade_in_ms": 2.5, "fade_out_ms": 8.0, "transients_ms": [20.0]},
        {"name": "slice_08", "start_ms": 2480.0, "end_ms": 2820.0, "gain_db": 0.0, "fade_in_ms": 2.5, "fade_out_ms": 8.0},
        {"name": "slice_09", "start_ms": 2820.0, "end_ms": 3160.0, "gain_db": -0.5, "fade_in_ms": 3.0, "fade_out_ms": 8.0, "transients_ms": [8.0]},
        {"name": "slice_10", "start_ms": 3160.0, "end_ms": 3500.0, "gain_db": -0.5, "fade_in_ms": 3.0, "fade_out_ms": 8.0},
        {"name": "slice_11", "start_ms": 3500.0, "end_ms": 3840.0, "gain_db": 0.0, "fade_in_ms": 3.0, "fade_out_ms": 8.0, "transients_ms": [12.0]},
        {"name": "slice_12", "start_ms": 3840.0, "end_ms": 4180.0, "gain_db": 0.0, "fade_in_ms": 3.0, "fade_out_ms": 8.0},
        {"name": "slice_13", "start_ms": 4180.0, "end_ms": 4520.0, "gain_db": 0.5, "fade_in_ms": 3.0, "fade_out_ms": 8.0, "transients_ms": [6.0]},
        {"name": "slice_14", "start_ms": 4520.0, "end_ms": 4860.0, "gain_db": 0.0, "fade_in_ms": 3.0, "fade_out_ms": 8.0},
        {"name": "slice_15", "start_ms": 4860.0, "end_ms": 5200.0, "gain_db": 0.0, "fade_in_ms": 3.0, "fade_out_ms": 8.0, "transients_ms": [14.0]},
        {"name": "slice_16", "start_ms": 5200.0, "end_ms": 5540.0, "gain_db": 0.0, "fade_in_ms": 3.0, "fade_out_ms": 8.0},
    ],
}
