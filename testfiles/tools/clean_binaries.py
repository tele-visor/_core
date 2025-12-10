"""Cleanup utility for generated patch artifacts.

This script deletes generated binary files under the testfiles workspace
(`.wav`, `.info`, `.zip` by default). It never runs automatically; invoke it
manually after regenerating artifacts if you want to return the tree to a
text-only state.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, List

DEFAULT_PATTERNS: tuple[str, ...] = ("*.wav", "*.info", "*.zip")


def _default_base() -> Path:
    """Resolve the default cleanup root (the `testfiles` directory)."""
    return Path(__file__).resolve().parent.parent


def collect_targets(base: Path, patterns: Iterable[str]) -> List[Path]:
    """Return all files under *base* that match any glob in *patterns*.

    The search is recursive and limited to the provided base path.
    """
    targets: list[Path] = []
    for pattern in patterns:
        for path in base.rglob(pattern):
            if path.is_file():
                targets.append(path)
    return sorted(targets)


def remove_files(paths: Iterable[Path], dry_run: bool = False) -> list[Path]:
    """Remove each file in *paths* unless *dry_run* is True.

    Returns the list of paths considered (removed or would-be removed).
    """
    processed: list[Path] = []
    for path in paths:
        processed.append(path)
        if dry_run:
            continue
        try:
            path.unlink()
        except FileNotFoundError:
            continue
    return processed


def main() -> None:
    parser = argparse.ArgumentParser(description="Remove generated binary artifacts under testfiles.")
    parser.add_argument(
        "base",
        nargs="?",
        type=Path,
        default=_default_base(),
        help="Directory to clean (default: testfiles root next to this script)",
    )
    parser.add_argument(
        "--pattern",
        action="append",
        default=list(DEFAULT_PATTERNS),
        help="Glob pattern to delete (default: %(default)s). Repeatable.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List files without deleting them.",
    )
    args = parser.parse_args()

    base = args.base.resolve()
    patterns = args.pattern
    targets = collect_targets(base, patterns)
    processed = remove_files(targets, dry_run=args.dry_run)

    verb = "Would remove" if args.dry_run else "Removed"
    for path in processed:
        print(f"{verb} {path}")


if __name__ == "__main__":
    main()
