import os
import struct


from . import cache_decorator
from .map import Map


__all__ = ["WarArchive"]


class _Stream:
    def __init__(self, memview):
        self._pos = 0
        self._view = memoryview(memview)

    def read8(self):
        try:
            return self._view[self._pos]
        finally:
            self._pos += 1

    def read16(self):
        try:
            return struct.unpack_from("<H", self._view[self._pos:self._pos + 2])[0]
        finally:
            self._pos += 2

    def read32(self):
        try:
            return struct.unpack_from("<I", self._view[self._pos:self._pos + 4])[0]
        finally:
            self._pos += 4

    def scan(self, pattern):
        """
        Scan's for the "pattern" bytes and leaves the stream pos after those bytes
        """
        pattern = list(pattern)
        value = [self.read8() for _ in range(len(pattern))]
        while value != pattern and self.remaining():
            value.pop(0)
            value.append(self.read8())

    def remaining(self):
        return len(self) - self.tell()

    def tell(self):
        return self._pos

    def seek(self, offset, whence=os.SEEK_SET):
        if whence == os.SEEK_SET:
            self._pos = offset
        else:
            assert whence == os.SEEK_CUR
            self._pos += offset
        self._pos = max(min(self._pos, len(self)), 0)

    def memory(self):
        return self._view

    def copy(self):
        return _Stream(self._view.tobytes())

    def __getitem__(self, part):
        return _Stream(self._view[part])

    def __len__(self):
        return len(self._view)


class WarArchive:
    COMPRESSED_FLAG = 0x20

    def __new__(cls, path):
        inst = super().__new__(cls)
        with open(path, "rb") as f:
            inst.stream = _Stream(f.read())
        inst.magic = inst.stream.read32()
        assert inst.magic in [0x19, 0x18], f"Wrong magic {hex(inst.magic)}"
        inst.entries = inst.stream.read16()
        typ = inst.stream.read16()
        inst.offsets = [inst.stream.read32() for e in range(inst.entries)]
        inst.length = len(inst.stream)
        inst.offsets.append(inst.length)
        return inst

    def __getitem__(self, idx):
        length =  - self.offsets[idx] - 4,
        chunk = self.stream[self.offsets[idx]:self.offsets[idx + 1]]
        length = len(chunk) - 4
        uncompressed_length = chunk.read32()
        is_compressed = uncompressed_length & 0x20000000
        uncompressed_length &= 0x1FFFFFFF

        if is_compressed:
            tmp = []
            buf = [0] * 4096
            while len(tmp) < uncompressed_length:
                i = 0
                bflags = chunk.read8()
                for i in range(8):
                    o = 0
                    if bflags & 1: # uncompressed byte
                        buf[len(tmp) % 4096] = byte = chunk.read8()
                        tmp.append(byte)
                    else: # compressed bytes
                        offset = chunk.read16()
                        numbytes = (offset // 4096) + 3
                        offset = offset % 4096
                        for i in range(numbytes):
                            buf[len(tmp) % 4096] = byte = buf[offset]
                            tmp.append(byte)
                            offset = (offset + 1) % 4096
                            if len(tmp) == uncompressed_length:
                                break
                    if len(tmp) == uncompressed_length:
                        break
                    bflags = bflags >> 1
            return _Stream(bytes(tmp))
        else:
            return chunk

    def get_map(self, idx):
        return Map(self, self[idx])
