# example_patch

This patch definition shows how to slice a 155 BPM loop into 16 manual slices
(with fades and gain) using `config.py`.

```bash
pip install -r ../../tools/requirements.txt
python ../../tools/build_patch.py config.py
```

Outputs land in `wav/`, `info/`, and `patch.zip` directly under this folder.
