# Patch workspace (testfiles/patches)

Text-only definitions for Ectocore/Zeptocore patches live here. You provide the
audio (`source.wav`) and run the Python tooling to regenerate all binaries
(`wav/`, `info/`, `patch.zip`) locally; none of those are produced in this
editing session.

## Layout

```
testfiles/patches/
  README.md                 # this file
  <patch_name>/
    config.py               # patch definition (Python dict: PATCH_CONFIG)
    source.wav              # user-provided audio (not committed)
    wav/                    # generated slices
    info/                   # generated .wav.info files
    patch.zip               # zip containing wav+info under <patch_name>/<bank>/
```

## Creating a patch

1. Duplicate `example_patch` into `testfiles/patches/<your_patch>/`.
2. Edit `config.py` inside that folder; set `PATCH_CONFIG["patch_name"]`,
   `PATCH_CONFIG["source"]`, and either `PATCH_CONFIG["slices"]` (manual grid)
   or the `PATCH_CONFIG["slicing"]` transient settings.
3. Place your `source.wav` next to `config.py` (it is not committed).
4. Install Python requirements (once per checkout):
   ```bash
   pip install -r testfiles/tools/requirements.txt
   ```
5. Build the patch (creates `wav/`, `info/`, and `patch.zip`):
   ```bash
   python testfiles/tools/build_patch.py testfiles/patches/<your_patch>/config.py
   ```
6. Inspect the generated outputs under your patch folder and add/commit them if
 desired. If you need to clear generated binaries before committing, run from
   the repo root:
   ```bash
   python testfiles/tools/clean_binaries.py --dry-run   # inspect
   python testfiles/tools/clean_binaries.py             # delete generated wav/info/zip
   ```

## Config (PATCH_CONFIG) schema

Top-level keys expected by the tooling:

- `patch_name` (string): folder name inside the zip (defaults to patch directory
  name).
- `source` (string): relative path to the source audio (usually `source.wav`).
- `bpm` (int): convenience alias for `flags.bpm`.
- `output` (object): `bank`, `start_index`, `variation` for filenames and zip
  structure.
- `flags` (object): mirrors `SampleInfo`-style bitfields (BPM, tempo match,
  channels, splice trigger, etc.).
- `slicing` (object): transient-driven slicing when `slices` is empty
  (`strategy`, `target_slices`, `min_gap_ms`, `threshold_db`, `window_ms`,
  `explicit_seconds`).
- `slices` (array): optional manual grid; if present it is used instead of
  transient detection. Each entry supports:
  - `name` (string, informational)
  - `start_ms` / `end_ms` (floats, required)
  - `gain_db` (float, default 0)
  - `fade_in_ms` / `fade_out_ms` (floats, default 0)
  - `transients_ms` (array of floats, optional per-slice markers)
- `labels` (object): assigns slice indices to tag codes for `.info` generation.
  `kick`, `snare`, `transient`, and `random` accept arrays of indices or `"all"`.
- `transients.per_slice_ms` (object): optional map of slice index → transient
  times (used when `transients_ms` is not provided per slice).

### Mapping to `SampleInfoPack` (see `lib/sampleinfo.h`)

- `flags` pack into the `Flags` field: bpm bits 0–8, play mode bits 9–11,
  one_shot bit 12, tempo_match bit 13, oversampling bit 14, num_channels bit 15,
  version bits 16–22, reserved bits 23–31.
- `flags.splice_trigger` and `flags.splice_variable` combine into the
  `SpliceInfo` uint16 (bits 0–14 trigger, bit 15 variable).
- Each generated `.wav.info` sets `slice_num` to the number of slices described
  for that WAV (default is one slice per exported WAV). Slice arrays are ordered
  as: all `slice_start` int32 (bytes from start of file), then all `slice_stop`
  int32, then all `slice_type` int8.
- When `flags.version >= 1`, three transient banks follow: three uint16 counts
  (non-zero transients only) then each transient position as uint16. Positions
  are derived from sample positions divided by 16 and clamped to 0xFFFF (values
  > 0xFFFF become 0 and are dropped from the counts).
- `size` in the header is the PCM data size of the WAV (bytes, not including the
  WAV header). The builder aligns `slice_stop` to a multiple of four bytes to
  mirror the firmware rounding in `core/src/zeptocore/zeptocorebinary.go`.

## Notes and assumptions

- `.info` payloads follow the bit layout in `lib/sampleinfo.h`. Each generated
  slice sets `slice_num=1` with `slice_start=[0]` and `slice_stop` equal to the
  PCM data length in bytes, aligned to a 4-byte boundary to mirror
  `core/src/zeptocore/zeptocorebinary.go`.
- `splice_trigger` defaults to 24 pulses-per-quarter; adjust `flags` if your
  workflow differs.
- `labels` map to `slice_type` codes in `.info`: default=0, kick=1, snare=2,
  transient=3, random=4. Update `testfiles/tools/build_patch.py` if you prefer
  different mappings.
- Transient arrays in `.info` (version ≥1) store per-slice markers defined either
  in each slice's `transients_ms` or in `transients.per_slice_ms`. Values are
  clamped to 16 entries per level to match firmware limits seen in
  `SampleInfo`.
