"""Minimal PNG read/write using only the standard library."""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass
class Image:
    width: int
    height: int
    rgba: bytearray  # length = width * height * 4

    def pixel(self, x: int, y: int) -> tuple[int, int, int, int]:
        i = (y * self.width + x) * 4
        r = self.rgba
        return r[i], r[i + 1], r[i + 2], r[i + 3]

    def set_pixel(self, x: int, y: int, rgba: tuple[int, int, int, int]) -> None:
        i = (y * self.width + x) * 4
        self.rgba[i : i + 4] = bytes(rgba)

    def copy(self) -> "Image":
        return Image(self.width, self.height, bytearray(self.rgba))


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def read_png(path: str | Path) -> Image:
    data = Path(path).read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"not a PNG: {path}")
    pos = 8
    width = height = None
    bit_depth = color_type = None
    raw = bytearray()
    while pos < len(data):
        length = struct.unpack(">I", data[pos : pos + 4])[0]
        pos += 4
        ctype = data[pos : pos + 4]
        pos += 4
        chunk = data[pos : pos + length]
        pos += length
        pos += 4  # crc
        if ctype == b"IHDR":
            width, height, bit_depth, color_type, *_ = struct.unpack(">IIBBBBB", chunk)
        elif ctype == b"IDAT":
            raw.extend(chunk)
        elif ctype == b"IEND":
            break
    if width is None or height is None:
        raise ValueError("missing IHDR")
    if bit_depth != 8:
        raise ValueError(f"only 8-bit PNG supported (got {bit_depth})")
    decompressed = zlib.decompress(bytes(raw))
    if color_type == 6:
        bpp = 4
    elif color_type == 2:
        bpp = 3
    elif color_type == 0:
        bpp = 1
    elif color_type == 4:
        bpp = 2
    else:
        raise ValueError(f"unsupported color type {color_type}")
    stride = width * bpp
    rows: list[bytearray] = []
    i = 0
    prev = bytearray(stride)
    for _ in range(height):
        filt = decompressed[i]
        i += 1
        row = bytearray(decompressed[i : i + stride])
        i += stride
        out = bytearray(stride)
        for x in range(stride):
            left = out[x - bpp] if x >= bpp else 0
            up = prev[x]
            ul = prev[x - bpp] if x >= bpp else 0
            v = row[x]
            if filt == 0:
                out[x] = v
            elif filt == 1:
                out[x] = (v + left) & 255
            elif filt == 2:
                out[x] = (v + up) & 255
            elif filt == 3:
                out[x] = (v + ((left + up) // 2)) & 255
            elif filt == 4:
                out[x] = (v + _paeth(left, up, ul)) & 255
            else:
                raise ValueError(f"unknown filter {filt}")
        rows.append(out)
        prev = out
    rgba = bytearray(width * height * 4)
    for y, row in enumerate(rows):
        for x in range(width):
            j = y * width * 4 + x * 4
            if bpp == 4:
                rgba[j : j + 4] = row[x * 4 : x * 4 + 4]
            elif bpp == 3:
                rgba[j : j + 3] = row[x * 3 : x * 3 + 3]
                rgba[j + 3] = 255
            elif bpp == 1:
                g = row[x]
                rgba[j : j + 4] = bytes((g, g, g, 255))
            else:  # GA
                g, a = row[x * 2], row[x * 2 + 1]
                rgba[j : j + 4] = bytes((g, g, g, a))
    return Image(width, height, rgba)


def write_png(path: str | Path, image: Image) -> None:
    width, height, rgba = image.width, image.height, image.rgba
    raw = bytearray()
    stride = width * 4
    for y in range(height):
        raw.append(0)  # filter None
        start = y * stride
        raw.extend(rgba[start : start + stride])
    compressed = zlib.compress(bytes(raw), 9)

    def chunk(tag: bytes, payload: bytes) -> bytes:
        return (
            struct.pack(">I", len(payload))
            + tag
            + payload
            + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    blob = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", compressed) + chunk(b"IEND", b"")
    Path(path).write_bytes(blob)


def resize_nearest(image: Image, tw: int, th: int) -> Image:
    out = Image(tw, th, bytearray(tw * th * 4))
    for y in range(th):
        sy = min(image.height - 1, y * image.height // th)
        for x in range(tw):
            sx = min(image.width - 1, x * image.width // tw)
            out.set_pixel(x, y, image.pixel(sx, sy))
    return out


def grayscale(image: Image) -> list[int]:
    g: list[int] = []
    for i in range(0, len(image.rgba), 4):
        r, gg, b = image.rgba[i], image.rgba[i + 1], image.rgba[i + 2]
        g.append((r * 30 + gg * 59 + b * 11) // 100)
    return g


def side_by_side(left: Image, right: Image, gap: int = 8, gap_rgb=(32, 32, 32)) -> Image:
    h = max(left.height, right.height)
    w = left.width + gap + right.width
    out = Image(w, h, bytearray(w * h * 4))
    for y in range(h):
        for x in range(w):
            out.set_pixel(x, y, (*gap_rgb, 255))
    for y in range(left.height):
        for x in range(left.width):
            out.set_pixel(x, y, left.pixel(x, y))
    ox = left.width + gap
    for y in range(right.height):
        for x in range(right.width):
            out.set_pixel(ox + x, y, right.pixel(x, y))
    return out


def hstack(images: Iterable[Image], gap: int = 4) -> Image:
    imgs = list(images)
    if not imgs:
        raise ValueError("no images")
    h = max(i.height for i in imgs)
    w = sum(i.width for i in imgs) + gap * (len(imgs) - 1)
    out = Image(w, h, bytearray(w * h * 4))
    for y in range(h):
        for x in range(w):
            out.set_pixel(x, y, (24, 24, 24, 255))
    ox = 0
    for im in imgs:
        for y in range(im.height):
            for x in range(im.width):
                out.set_pixel(ox + x, y, im.pixel(x, y))
        ox += im.width + gap
    return out
