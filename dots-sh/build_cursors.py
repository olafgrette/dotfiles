#!/usr/bin/env python3
"""Add pixel-preserving sizes to the approved Brood War Xcursor archive."""

import argparse
import copy
import gzip
import io
from pathlib import Path
import struct
import tarfile


IMAGE = 0xFFFD0002
SIZES = (48, 64, 96, 128)


def images(data):
    magic, header, version, count = struct.unpack_from("<4I", data)
    if (magic, header, version) != (0x72756358, 16, 0x10000):
        raise ValueError("unsupported Xcursor header")
    result = []
    for index in range(count):
        kind, nominal, offset = struct.unpack_from("<3I", data, header + index * 12)
        chunk = struct.unpack_from("<9I", data, offset)
        length, chunk_type, size, revision, width, height, xhot, yhot, delay = chunk
        if (kind, length, chunk_type, size, revision) != (IMAGE, 36, IMAGE, nominal, 1):
            raise ValueError("unsupported Xcursor chunk")
        if not (size > 0 and 0 < width <= 32767 and 0 < height <= 32767
                and xhot < width and yhot < height):
            raise ValueError("invalid Xcursor dimensions or hotspot")
        pixels = data[offset + length:offset + length + width * height * 4]
        if len(pixels) != width * height * 4:
            raise ValueError("truncated Xcursor pixels")
        result.append((size, width, height, xhot, yhot, delay, pixels))
    if not result or len({frame[0] for frame in result}) != 1:
        raise ValueError("expected one original size per cursor")
    return result


def resize(frame, size):
    nominal, width, height, xhot, yhot, delay, pixels = frame
    scale = lambda value: (value * size + nominal // 2) // nominal
    new_width, new_height = max(1, scale(width)), max(1, scale(height))
    # Copy packed ARGB pixels intact; interpolation would blur the pixel art
    # and can introduce alpha fringes in premultiplied cursor data.
    rows = []
    for y in range(new_height):
        source_y = min(height - 1, (2 * y + 1) * height // (2 * new_height))
        row = []
        for x in range(new_width):
            source_x = min(width - 1, (2 * x + 1) * width // (2 * new_width))
            offset = (source_y * width + source_x) * 4
            row.append(pixels[offset:offset + 4])
        rows.append(b"".join(row))
    return (size, new_width, new_height, min(new_width - 1, scale(xhot)),
            min(new_height - 1, scale(yhot)), delay, b"".join(rows))


def upscale(data):
    original = images(data)
    frames = original + [resize(frame, size) for size in SIZES
                         if size > original[0][0] for frame in original]
    toc, chunks = [], []
    offset = 16 + 12 * len(frames)
    for size, width, height, xhot, yhot, delay, pixels in frames:
        chunk = struct.pack("<9I", 36, IMAGE, size, 1, width, height, xhot, yhot, delay) + pixels
        toc.append(struct.pack("<3I", IMAGE, size, offset))
        chunks.append(chunk)
        offset += len(chunk)
    return struct.pack("<4I", 0x72756358, 16, 0x10000, len(frames)) + b"".join(toc + chunks)


def build(source, destination):
    # Fixed archive metadata and gzip timestamp make the approved output
    # reproducible. Original names, theme identity, and aliases stay intact.
    with tarfile.open(source) as original, destination.open("wb") as output:
        with gzip.GzipFile(filename="", mode="wb", fileobj=output, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w", format=tarfile.USTAR_FORMAT) as result:
                for member in sorted(original.getmembers(), key=lambda item: item.name):
                    info = copy.copy(member)
                    info.uid = info.gid = info.mtime = 0
                    info.uname = info.gname = ""
                    if member.isfile():
                        content = original.extractfile(member).read()
                        if member.name.startswith("broodwar/cursors/"):
                            content = upscale(content)
                        info.size = len(content)
                        info.mode = 0o644
                        result.addfile(info, io.BytesIO(content))
                    elif member.isdir() or member.issym():
                        result.addfile(info)
                    else:
                        raise ValueError(f"unsupported archive entry: {member.name}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="verified original archive")
    parser.add_argument("destination", type=Path, help="generated archive outside Git")
    args = parser.parse_args()
    if args.source.resolve() == args.destination.resolve():
        parser.error("source and destination must differ")
    build(args.source, args.destination)


if __name__ == "__main__":
    main()
