"""
Lightweight class to create indexed bitmaps
"""

import math
import os

from itertools import zip_longest
from struct import pack


class Bitmap:
    """
    Simple class to write a subset of possible BMP formats. Only supports 24 bit
    RGB bitmaps or (when constructed with a list of bytes representing RGB values),
    can store indexed bitmaps with either 4 or 8 bits per pixel.
    """

    def __init__(self, width, height, pixels, rgb_palette=None):
        if rgb_palette:
            n, rem = divmod(len(rgb_palette), 3)
            if rem:
                raise TypeError("palette is not divisible by 3")
            self.bpp = int(math.log(n, 2))
            if self.bpp != 8:
                raise TypeError("only 8 bit palettes supported")
            self.palette = rgb_palette
        else:
            self.palette = []
            self.bpp = 24
        if width < 1 or height < 1:
            raise TypeError("width and height must be >= 1")
        self.width = width
        self.height = height
        bytes_per_row = (self.bpp * width) // 8
        self.bytes_padding_per_row = (4 - bytes_per_row % 4) % 4
        self.size = (bytes_per_row + self.bytes_padding_per_row) * height
        self.pixels = pixels

    def write_header(self, f):
        f.write(b"BM")
        f.write(pack("<L", self.size)) # type
        f.write(pack("<H", 0)) # reserved
        f.write(pack("<H", 0)) # reserved
        pixel_data_offset_location = f.tell()
        f.write(pack("<L", 0)) # pixel data offset, filled in later
        f.write(pack("<L", 40)) # BITMAPINFOHEADER
        f.write(pack("<l", self.width))
        f.write(pack("<l", -self.height)) # negative height, so we can store pixels top to bottom
        f.write(pack("<H", 1))  # num colorplanes
        f.write(pack("<H", self.bpp))
        f.write(pack("<L", 0))  # RGB (i.e., no) compression
        f.write(pack("<L", 0))  # image size
        f.write(pack("<L", 3000)) # pixels per metre horiz
        f.write(pack("<L", 3000)) # pixels per metre vert
        f.write(pack("<L", len(self.palette) // 3))
        f.write(pack("<L", 0)) # number of important colors
        end_of_dib_header = f.tell()
        for r,g,b in zip_longest(*([iter(self.palette)] * 3)):
            # bitmap color table is B,G,R,0x00 (0 for Alpha)
            f.write(pack("BBBB", b, g, r, 0))
        end_of_palette = f.tell()
        padding = (4 - (end_of_palette % 4)) % 4
        self._start_of_pixels = end_of_palette + padding
        f.seek(pixel_data_offset_location, os.SEEK_SET)
        f.write(pack("<L", self._start_of_pixels))
        f.seek(self._start_of_pixels, os.SEEK_SET)

    def write_pixels(self, f):
        assert hasattr(self, "_start_of_pixels") and f.tell() == self._start_of_pixels
        if (self.palette and self.bpp == 8 and
            self.bytes_padding_per_row == 0 and isinstance(self.pixels, (bytearray, bytes, memoryview))):
            # fast path when 1px == 1byte and we don't need padding
            f.write(self.pixels)
        elif self.bpp == 8:
            pixels_iter = iter(self.pixels)
            pixels_iter = (pack("B", p) for p in self.pixels_iter)
            for _ in range(self.height):
                for _ in range(self.width):
                    f.write(next(pixels_iter))
                for _ in range(self.bytes_padding_per_row):
                    f.write(b"0")
        elif self.bpp == 24:
            pixels_iter = zip_longest(*([iter(self.pixels)] * 3))
            for _ in range(self.height):
                for _ in range(self.width):
                    r,g,b = next(pixels_iter)
                    f.write(pack("BBB", b, g, r))
                for _ in range(self.bytes_padding_per_row):
                    f.write(b"0")

    def write(self, f):
        self.write_header(f)
        self.write_pixels(f)

    def __getitem__(self, xy):
        bypp = self.bpp / 8
        byte = x * bypp + y * self.width * self.bypp
        if self.palette:
            assert self.bpp >= 8, "no support for lower bitdepths now"
            return self.pixels[int(byte)]
        else:
            return self.pixels[byte:byte + bypp]

    def __setitem__(self, xy, pixel):
        bypp = self.bpp / 8
        byte = x * bypp + y * self.width * self.bypp
        if self.palette:
            assert self.bpp >= 8, "no support for lower bitdepths now"
            self.pixels[int(byte)] = int(pixel)
        else:
            self.pixels[byte:byte + bypp] = pixel
