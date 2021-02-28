import io
import os
import re
import struct


__all__ = ["WarArchive"]


def cache_decorator(func):
    def wrapper(self):
        if not hasattr(self, "_cache"):
            self._cache = {}
        result = self._cache.get(func, None)
        if not result:
            result = self._cache[func] = func(self)
        return result
    return wrapper


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


class Map:
    ALLOWED = 0x0 # 1 int
    UPGRADE_RANGED = 0x4 # 5 bytes
    UPGRADE_MELEE = 0x9 # 5 bytes
    UPGRADE_RIDER = 0xE # 5 bytes
    SPELL_SUMMON = 0x13 # 5 bytes
    SPELL_RAIN = 0x18 # 5 bytes
    SPELL_DAEMON = 0x1D # 5 bytes
    SPELL_HEALING = 0x22 # 5 bytes
    SPELL_VISION = 0x27 # 5 bytes
    SPELL_ARMOR = 0x2C # 5 bytes
    UPGRADE_SHIELDS = 0x31 # 5 bytes
    MARKER = 0x36 # 0xFFFFFFFF
    LUMBER = 0x5C # 5 shorts
    GOLD = 0x70 # 5 shorts
    MYSTERY_DATA = 0x88 # 5 bytes
    OFFSET_TO_BRIEFING = 0x94 # 1 short
    # chunks are 2 too large for some reason
    CHUNK_OFFSET = -2
    TILE_DATA_CHUNK = 0xD0 # 1 short
    TILE_FLAGS_CHUNK = 0xD2 # 1 short
    TILESET_PALETTE_CHUNK = 0xD4 # 1 short
    TILESET_INFO_CHUNK = 0xD6 # 1 short
    TILESET_IMG_CHUNK = 0xD8 # 1 short
    # after that, search for another 0xFFFFFFFF and then follows the unit data offset
    UNIT_DATA_OFFSET_MARKER = [0xff, 0xff, 0xff, 0xff]
    END_UNITS_MARKER = [0xff, 0xff]

    def __new__(cls, archive, content):
        inst = super().__new__(cls)
        inst.archive = archive
        inst.content = content
        return inst

    @cache_decorator
    def get_allowed(self):
        pass

    @cache_decorator
    def get_researched(self):
        pass

    @cache_decorator
    def get_lumber(self):
        pass

    @cache_decorator
    def get_gold(self):
        pass

    @cache_decorator
    def get_briefing(self):
        self.content.seek(self.OFFSET_TO_BRIEFING)
        offset = self.content.read16()
        self.content.seek(offset)
        self.content.scan(b"\0")
        return self.content.memory()[offset:self.content.tell() - 1].tobytes()

    @cache_decorator
    def get_tiles(self):
        self.content.seek(self.TILE_DATA_CHUNK)
        tiledata = self.archive[self.content.read16() + self.CHUNK_OFFSET]
        self.content.seek(self.TILE_FLAGS_CHUNK)
        tileflags = self.archive[self.content.read16() + self.CHUNK_OFFSET]
        return Tiles(tiledata, tileflags)

    @cache_decorator
    def get_tileset_palette(self):
        pass

    @cache_decorator
    def get_tileset_info(self):
        pass

    @cache_decorator
    def get_tileset_image(self):
        pass

    @cache_decorator
    def get_unit_data(self):
        self.content.seek(self.TILESET_IMG_CHUNK)
        self.content.scan(self.UNIT_DATA_OFFSET_MARKER)
        unit_data_offset = self.content.read16()
        self.content.seek(unit_data_offset)
        self.content.scan(self.END_UNITS_MARKER)
        return UnitData(self.content[unit_data_offset:self.content.tell() - len(self.END_UNITS_MARKER)])

    @cache_decorator
    def get_roads(self):
        self.content.seek(self.TILESET_IMG_CHUNK)
        self.content.scan(self.UNIT_DATA_OFFSET_MARKER)
        unit_data_offset = self.content.read16()
        self.content.seek(unit_data_offset)
        self.content.scan(self.END_UNITS_MARKER)
        roads_start = self.content.tell()
        self.content.scan(self.END_UNITS_MARKER)
        return Roads(self.content[roads_start:self.content.tell() - len(self.END_UNITS_MARKER)])

    @cache_decorator
    def get_walls(self):
        self.content.seek(self.TILESET_IMG_CHUNK)
        self.content.scan(self.UNIT_DATA_OFFSET_MARKER)
        unit_data_offset = self.content.read16()
        self.content.seek(unit_data_offset)
        self.content.scan(self.END_UNITS_MARKER)
        # here are the roads
        self.content.scan(self.END_UNITS_MARKER)
        # here are the walls
        walls_start = self.content.tell()
        self.content.scan(self.END_UNITS_MARKER)
        return Walls(self.content[walls_start:self.content.tell() - len(self.END_UNITS_MARKER)])

    def write(self, f):
        tiles = self.get_tiles()
        for x in range(64):
            for y in range(64):
                f.seek(x * 64 + y, os.SEEK_SET)
                f.write(bytearray([tiles[x, y].tile % 256]))
        self.get_roads().write(f)
        self.get_walls().write(f)


class Roads:
    TILE = 0x22

    def __new__(cls, content):
        inst = super().__new__(cls)
        inst.content = content
        return inst

    def write(self, f):
        while self.content.remaining():
            x1, y1, x2, y2, player = (self.content.read8() for _ in range(5))
            for x in range(x1 // 2, x2 // 2 + 1):
                for y in range(y1 // 2, y2 // 2 + 1):
                    f.seek(x * 64 + y, os.SEEK_SET)
                    f.write(bytearray([self.TILE]))


class Walls(Roads):
    TILE = 0x10


class UnitData:
    def __new__(cls, archive, content):
        inst = super().__new__(cls)
        inst.archive = archive
        inst.content = content
        return inst


class Tiles:
    def __new__(cls, terrain, flags):
        inst = super().__new__(cls)
        inst.terrain = terrain
        inst.flags = flags
        return inst

    def __getitem__(self, xy):
        x, y = xy
        offset = (x + y * 64) * 2
        self.terrain.seek(offset)
        self.flags.seek(offset)
        return Tile(self.terrain.read16(), self.flags.read16())

    def __iter__(self):
        return _TileIter(self)


class _TileIter:
    def __init__(self, m):
        self.m = m
        self.x = 0
        self.y = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self.y == 64:
            raise StopIteration
        tile = self.m[self.x, self.y]
        self.x += 1
        if self.x == 64:
            self.x = 0
            self.y += 1
        return tile


class Tile:
    def __new__(cls, tile, flags):
        inst = super().__new__(cls)
        inst.tile = tile
        inst.flags = flags
        return inst

    def is_ground(self):
        return self.flags == 0x00

    def is_water(self):
        return self.flags == 0x80

    def is_bridge(self):
        return self.flags == 0x10

    def is_passable(self):
        return self.is_ground() or self.is_bridge()

    def is_door(self):
        return self.flags == 0x0C

    def is_rescue_point(self):
        return self.flags == 0x20


def main(data, out):
    data = os.path.join(data, ".")
    mapdir = os.path.join(out, "maps")
    os.makedirs(mapdir, exist_ok=True)
    palettes = os.path.join(out, ".")

    archive = WarArchive(os.path.join(data, "DATA.WAR"))
    archive.get_map(117).get_tiles()

    for idx, m in enumerate(["human", "orc"] * 12):
        lvl = idx // 2 + 1
        map = archive.get_map(117 + idx)
        map.name = f"{m}{lvl}"
        print(map.name, map.get_briefing())
        with open(f"{os.path.join(mapdir, map.name)}.map", "wb") as f:
            map.write(f)


if __name__ == "__main__":
    import sys
    from argparse import ArgumentParser
    parser = ArgumentParser(sys.argv[0])
    parser.add_argument('--data', required=True)
    parser.add_argument('--output', required=True)
    parsed_args = parser.parse_args(sys.argv[1:])
    main(parsed_args.data, parsed_args.output)
