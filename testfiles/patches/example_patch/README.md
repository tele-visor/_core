# example_patch

This patch definition shows how to slice a 155 BPM loop into 16 manual slices
(with fades and gain) using `config.py`.

```bash
pip install -r ../../tools/requirements.txt
python ../../tools/build_patch.py config.py
```

Outputs land in `wav/`, `info/`, and `patch.zip` directly under this folder.
No binary outputs are committed; if you generated them locally and want a clean
tree before committing, delete them from the repo root with:

```bash
find testfiles -type f \( -name '*.wav' -o -name '*.info' -o -name '*.zip' \) -delete
```
or use the cleanup helper (dry-run first to review what would be removed):

```bash
python testfiles/tools/clean_binaries.py --dry-run
python testfiles/tools/clean_binaries.py
```

Key `.wav.info` mappings (see `lib/sampleinfo.h`):

- `PATCH_CONFIG["bpm"]` and `PATCH_CONFIG["flags"]` populate the `Flags`
  bitfield (bpm bits 0–8, play mode bits 9–11, one_shot bit 12, tempo_match bit
  13, oversampling bit 14, num_channels bit 15, version bits 16–22, reserved
  bits 23–31). Splice trigger/variable pack into `SpliceInfo` (bits 0–14 trigger
  and bit 15 variable).
- Each generated `.wav.info` for this patch contains one slice per WAV with
  `slice_start=[0]` and `slice_stop` equal to the PCM data length (bytes) aligned
  to four bytes to mirror the firmware rounding in
  `core/src/zeptocore/zeptocorebinary.go`.
- Transients are written when `version >= 1` as three uint16 counts followed by
  uint16 positions (sample positions divided by 16, values > 0xFFFF become 0 and
  are excluded from the counts).
