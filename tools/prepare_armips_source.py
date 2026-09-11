#!/usr/bin/env python3
"""Flatten armips includes to avoid a Windows include-decoder regression."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


INCLUDE_RE = re.compile(
    r'^\s*\.include\s+"([^"]+)"(?:\s*,\s*"[^"]+")?\s*(?:(?:;|//).*)?$'
)


def expand(path: Path, root: Path, stack: tuple[Path, ...] = ()) -> str:
    path = path.resolve()
    if path in stack:
        chain = " -> ".join(str(item) for item in (*stack, path))
        raise RuntimeError(f"recursive armips include: {chain}")
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise RuntimeError(f"include escapes fontpatch root: {path}") from exc

    output: list[str] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        match = INCLUDE_RE.match(line)
        if not match:
            output.append(line)
            continue

        included = (root / match.group(1)).resolve()
        output.append(f"; begin flattened include: {included.relative_to(root).as_posix()}")
        output.append(expand(included, root, (*stack, path)))
        output.append(f"; end flattened include: {included.relative_to(root).as_posix()}")
    return "\n".join(output)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    source = args.source.resolve()
    root = source.parent
    flattened = expand(source, root)
    args.output.write_text(flattened + "\n", encoding="utf-8-sig", newline="\n")
    print(f"armips source: {source.name} -> {args.output.name}")


if __name__ == "__main__":
    main()
