import os


from . import cache_decorator
from .img import Tileset


__all__ = ["Map"]


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
    TILESET_INFO_CHUNK = 0xD4 # 1 short
    TILESET_IMG_CHUNK = 0xD6 # 1 short
    TILESET_PALETTE_CHUNK = 0xD8 # 1 short
    # after that, search for another 0xFFFFFFFF and then follows the unit data offset
    UNIT_DATA_OFFSET_MARKER = [0xff, 0xff, 0xff, 0xff]
    END_UNITS_MARKER = [0xff, 0xff]
    END_ROADS_MARKER = END_UNITS_MARKER
    END_WALLS_MARKER = END_UNITS_MARKER

    @staticmethod
    def match(archive, content):
        content = content.copy()
        min_size = (
            0xD8 +
            len(UNIT_DATA_OFFSET_MARKER) +
            len(END_UNITS_MARKER) +
            len(END_ROADS_MARKER) +
            len(END_WALLS_MARKER)
        )
        if size < min_size:
            return False
        try:
            content.seek(self.TILE_DATA_CHUNK)
            tiledata = archive[content.read16() + self.CHUNK_OFFSET]
            content.seek(self.TILE_FLAGS_CHUNK)
            tileflags = archive[content.read16() + self.CHUNK_OFFSET]
        except:
            return False
        if not Tiles.match(tiledata, tileflags):
            return False
        return True

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
        return Tiles(self.get_tileset(), tiledata, tileflags)

    @cache_decorator
    def get_tileset_palette(self):
        self.content.seek(self.TILESET_PALETTE_CHUNK)
        return self.content.read16() + self.CHUNK_OFFSET

    @cache_decorator
    def get_tileset_info(self):
        self.content.seek(self.TILESET_INFO_CHUNK)
        return self.content.read16() + self.CHUNK_OFFSET

    @cache_decorator
    def get_tileset_image(self):
        self.content.seek(self.TILESET_IMG_CHUNK)
        return self.content.read16() + self.CHUNK_OFFSET

    @cache_decorator
    def get_tileset(self):
        palette = self.archive[self.get_tileset_palette()]
        info = self.archive[self.get_tileset_info()]
        idx = self.get_tileset_image()
        image = self.archive[idx]
        return Tileset(self.archive, idx, palette, info, image)

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

    OUTPUT_MAP_DATA_OFFSET = 3

    def write(self, f):
        tsname = self.get_tileset().name
        assert len(tsname) == self.OUTPUT_MAP_DATA_OFFSET
        f.write(b"%s" % tsname.encode())
        tiles = self.get_tiles()
        for x in range(64):
            for y in range(64):
                f.seek(x * 64 + y + self.OUTPUT_MAP_DATA_OFFSET, os.SEEK_SET)
                f.write(bytearray([tiles[x, y].tile % 256]))
        self.get_roads().write(f)
        self.get_walls().write(f)


class Roads:
    TILE = 0x46 # TODO: real road layout, and then use tileset mapping

    def __new__(cls, content):
        inst = super().__new__(cls)
        inst.content = content
        return inst

    def write(self, f):
        while self.content.remaining():
            x1, y1, x2, y2, player = (self.content.read8() for _ in range(5))
            for x in range(x1 // 2, x2 // 2 + 1):
                for y in range(y1 // 2, y2 // 2 + 1):
                    f.seek(x * 64 + y + Map.OUTPUT_MAP_DATA_OFFSET, os.SEEK_SET)
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
    @staticmethod
    def match(terrain, flags):
        return len(terrain) == len(flags) == 64 * 64 * 2

    def __new__(cls, tileset, terrain, flags):
        inst = super().__new__(cls)
        inst.tileset = tileset
        inst.terrain = terrain
        inst.flags = flags
        return inst

    def __getitem__(self, xy):
        x, y = xy
        offset = (x + y * 64) * 2
        self.terrain.seek(offset)
        self.flags.seek(offset)
        tile = self.tileset.map_tile(self.terrain.read16())
        return Tile(tile, self.flags.read16())

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
