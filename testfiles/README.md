# Test files

This directory keeps reference documentation plus a **text-only** pipeline for
building Ectocore/Zeptocore patch artifacts. Binary outputs (`.wav`, `.wav.info`,
`.zip`) are **not** tracked here; generate them yourself by running the Python
scripts under `testfiles/tools/` after placing your own audio next to a patch
config.

Contents (text only):
- `patch/`: legacy reference folder; its `bank1/` contents have been removed so
  no binary files remain. You can repopulate it by running the pipeline with
  your own audio if you need comparable outputs.
- `patches/`: reproducible patch definitions that live entirely in Git (Python
  configs + build scripts). See `testfiles/patches/README.md` for usage.
- `tools/`: Python utilities used by the patch pipeline (`build_patch.py`,
  `slicing.py`, `ectocore_info.py`).

Repository path: this folder is `testfiles/` at the repository root. In the
standard development container the checkout lives at `/workspace/_core`, so the
absolute path is `/workspace/_core/testfiles` (the same location visible via
`https://github.com/tele-visor/_core/tree/main/testfiles`).
