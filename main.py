#!/usr/bin/env python3
"""Entry for the make.fun news-image-20261118 competition.

The picture sums up Wednesday 18 November 2026: Crimea bridge arch collapses
after Ukraine's largest drone attack, Trump's Quad summit in Manila, Cyclone
Akvan, UK sanctions on Israeli settlement firms, NVIDIA's 115.8 billion dollar
revenue, and Latvia's new government.

This program validates the bundled picture and copies it, unchanged, to
$MAKEFUN_OUTPUT_DIR/entry.png (default /output).
"""

from __future__ import annotations

import hashlib
import os
import struct
import sys
from pathlib import Path

SOURCE_NAME = "entry.jpg"
MAX_BYTES = 1_048_576  # 1 MiB
MAX_SIDE = 1024
JPEG_SOI = b"\xff\xd8"
JPEG_EOI = b"\xff\xd9"

# Start-of-frame markers that carry frame dimensions (excluding DHT/JPG/DAC).
SOF_MARKERS = frozenset(range(0xC0, 0xD0)) - {0xC4, 0xC8, 0xCC}


def fail(message: str) -> "NoReturn":  # type: ignore[name-defined]
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def locate_source() -> Path:
    """Find entry.jpg next to this program, or under /bot."""
    here = Path(__file__).resolve().parent
    candidates = [here / SOURCE_NAME, Path("/bot") / SOURCE_NAME]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    tried = ", ".join(str(c) for c in candidates)
    fail(f"could not find {SOURCE_NAME} (tried: {tried})")


def jpeg_dimensions(data: bytes) -> tuple[int, int]:
    """Parse width and height from the first JPEG start-of-frame segment."""
    if not data.startswith(JPEG_SOI):
        fail("file does not start with JPEG SOI bytes FF D8")
    if not data.endswith(JPEG_EOI):
        fail("file does not end with JPEG EOI bytes FF D9")

    pos = 2
    end = len(data)
    while pos < end:
        # Skip fill bytes to the next marker prefix.
        while pos < end and data[pos] != 0xFF:
            pos += 1
        while pos < end and data[pos] == 0xFF:
            pos += 1
        if pos >= end:
            break
        marker = data[pos]
        pos += 1

        if marker in (0x01, 0xD8) or 0xD0 <= marker <= 0xD7:
            continue  # no length field
        if marker == 0xD9:
            break

        if pos + 2 > end:
            break
        (segment_len,) = struct.unpack(">H", data[pos : pos + 2])
        if segment_len < 2:
            fail("malformed JPEG segment length")
        payload = pos + 2
        segment_end = pos + segment_len
        if segment_end > end:
            break

        if marker in SOF_MARKERS:
            if segment_len < 7:
                fail("malformed JPEG start-of-frame segment")
            height, width = struct.unpack(">HH", data[payload + 1 : payload + 5])
            if width == 0 or height == 0:
                fail("JPEG start-of-frame reports zero width or height")
            return width, height

        if marker == 0xDA:  # start of scan: no frame header seen
            break
        pos = segment_end

    fail("no JPEG start-of-frame segment found")


def main() -> int:
    source = locate_source()
    data = source.read_bytes()

    if len(data) > MAX_BYTES:
        fail(
            f"{source} is {len(data)} bytes ({len(data) / MAX_BYTES:.2f} MiB), "
            f"which exceeds the {MAX_BYTES} byte (1 MiB) limit; "
            "the file was not copied"
        )
    if len(data) == 0:
        fail(f"{source} is empty")

    width, height = jpeg_dimensions(data)
    if width > MAX_SIDE or height > MAX_SIDE:
        fail(
            f"{source} is {width}x{height}, exceeds the "
            f"{MAX_SIDE}x{MAX_SIDE} pixel limit"
        )

    out_dir = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "entry.png"

    with open(target, "wb") as handle:
        handle.write(data)

    digest = hashlib.sha256(data).hexdigest()
    written = target.read_bytes()
    if hashlib.sha256(written).hexdigest() != digest:
        fail(f"verification failed: {target} does not match the source bytes")

    print(
        f"ok {len(data)} bytes {width}x{height} sha256={digest} -> {target}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
