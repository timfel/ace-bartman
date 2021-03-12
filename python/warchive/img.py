import os


from . import cache_decorator
from .bitmap import Bitmap


__all__ = ["Image", "Cursor", "Spritesheet", "Tileset"]


class Image:
    @staticmethod
    def match(chunk):
        chunk = chunk.copy()
        if len(chunk) < 4:
            return False
        w = chunk.read16()
        h = chunk.read16()
        return len(chunk) - 4 == w * h


class Cursor(Image):
    @staticmethod
    def match(chunk):
        chunk = chunk.copy()
        if len(chunk) < 8:
            return False
        xoff = chunk.read16()
        yoff = chunk.read16()
        w = chunk.read16()
        h = chunk.read16()
        return len(chunk) - 8 == w * h


class Spritesheet(Image):
    """Structure of spritesheets (GFU in war1tool)

    Sprite sheet files start with a 2 byte integer telling the number of frames
    inside the file, followed by the sprite dimensions as 1 byte width and
    height. Next is a list of all frames, starting with their y and x offset,
    followed by width and height, each as 1 byte value.  Last comes the offset
    of the frame inside the file, stored as 4 byte integer.  If the width times
    height is greater than the difference between this and the next offset, then
    the frame is compressed as specified below. Else it is to be read as a usual
    indexed 256 color bitmap.
    """

    @staticmethod
    def match(chunk):
        chunk = chunk.copy()
        framecount = chunk.read16()
        sprite_w = chunk.read8()
        sprite_h = chunk.read8()
        frames = []
        for i in range(framecount):
            xoff = chunk.read8()
            yoff = chunk.read8()
            w = chunk.read8()
            h = chunk.read8()
            frame_offset_in_chunk = chunk.read32()
        if frames:
            lastw = frames[i - 1][2]
            lasth = frames[i - 1][3]
            lasto = frames[i - 1][4]
            if lastw * lasth < frame_offset_in_chunk - lasto:
                # not enough room for uncompressed frame between the last
                # offset and this, so the last frame is compressed
                frames[i - 1] = Frame(*frames[:-1], chunk[lasto:frame_offset_in_chunk])
        frames.append((xoff, yoff, w, h, frame_offset_in_chunk))


class Frame:
    def __init__(self, x, y, w, h, chunk):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.is_compressed = len(chunk) < w * h


class Tileset:
    """Structure of tileset entries:

    The palette is always at index + 1. It is handled with the Palette class.

    Tilesets are split into two chunks: a chunk with tileinfo and a chunk with
    tilepixels. Each tile index points to an 8-byte offset in the tileinfo
    chunk. Each tile's pixel data is really stored as 4 8x8 "mini" tiles (I
    believe to safe space). So there a 4 "mini" tiles per tile. At the tileinfo
    offset for each tile, we find 4 shorts that describe each of the 4 "mini"
    tiles. the upper 16 bits needs to be multiplied by 2 to get the offset into
    the pixel data. The lower two bits indicate wether the "mini" tile needs to
    be flipped in x or y direction (this is the space saving measure, because
    many tiles are just mirrors of others). The lowest bit is for Y, the other
    for X.

    """

    # These can only be hardcoded, there's no info about that in the archive
    NAMES = {190: "forest", 193: "swamp", 196: "dungeon"}

    TILE_SIZE = 16
    MINI_TILE_SIZE = 8
    MINI_TILE_DIVISON = TILE_SIZE // MINI_TILE_SIZE
    TILE_INFO_SIZE = 8 # 4 * 2-byte offsets to the mini tiles

    def __init__(self, archive, idx, palette, info, image, mapped_tiles=None):
        self.idx = idx
        print(self.name)
        self.archive = archive
        self.palette = palette
        self.info = info
        self.image = image
        self._mapped_tiles = mapped_tiles
        self._removed_tiles = -1

    @property
    def name(self):
        return self.NAMES[self.idx]

    @property
    def mapped_tiles(self):
        return self._mapped_tiles

    @mapped_tiles.setter
    def mapped_tiles(self, value):
        self._mapped_tiles = value
        self._removed_tiles = -1

    @property
    def removed_tiles(self):
        if self._removed_tiles < 0:
            removed = 0
            for inclusive_removed_range in self.mapped_tiles.keys():
                removed += (inclusive_removed_range[1] - inclusive_removed_range[0] + 1)
            self._removed_tiles = removed
        return self._removed_tiles

    def extract(self):
        archive = self.archive
        palette = Palette(archive, self.palette).get_rgb_array()
        numtiles = len(self.info) // self.TILE_INFO_SIZE
        output_num_tiles = numtiles - self.removed_tiles
        width = self.TILE_SIZE
        height = output_num_tiles * self.TILE_SIZE
        image = memoryview(bytearray(bytearray([0]) * width * height))

        for tilenumber in range(numtiles):
            if self.is_removed(tilenumber):
                continue
            tile_info = self.info[tilenumber * self.TILE_INFO_SIZE:]
            for y_half in range(self.MINI_TILE_DIVISON):
                for x_half in range(self.MINI_TILE_DIVISON):
                    output_x = x_half * self.MINI_TILE_SIZE # either 0 or 8
                    output_y = self.map_tile(tilenumber) * self.TILE_SIZE + y_half * self.MINI_TILE_SIZE
                    current_output_pixel = output_x + output_y * width
                    # multiply index into tile_info by 2, since we're reading shorts, not bytes
                    offset_of_quarter_tile = tile_info[(x_half + y_half * self.MINI_TILE_DIVISON) * 2:].read16()
                    input_pixel_start = ((offset_of_quarter_tile & 0xFFFC) << 1) & 0xFFFF
                    mirror_x = bool(offset_of_quarter_tile & 2)
                    mirror_y = bool(offset_of_quarter_tile & 1)
                    x_range = range(self.MINI_TILE_SIZE)
                    y_range = range(self.MINI_TILE_SIZE)
                    if mirror_x:
                        x_range = list(reversed(x_range))
                    if mirror_y:
                        y_range = list(reversed(y_range))
                    for y in y_range:
                        for x in x_range:
                            image[current_output_pixel] = self.image[input_pixel_start + x + y * self.MINI_TILE_SIZE]
                            current_output_pixel += 1
                        current_output_pixel += self.MINI_TILE_SIZE

        return Bitmap(width, height, image, rgb_palette=palette)

    def write(self, f):
        self.extract().write(f)

    def is_removed(self, tile):
        for k,v in self.mapped_tiles.items():
            if tile >= k[0] and tile <= k[1]:
                return True
        return False

    def map_tile(self, tile):
        offset = 0
        for k,v in self.mapped_tiles.items():
            if tile < k[0]:
                # we are in between things that are removed, so there's no custom
                # mapping for us, we just subtract the offset
                return tile - offset
            offset += (k[1] - k[0] + 1) # ranges are inclusive
            if tile > k[1]:
                continue
            elif v:
                # we're not after the range, we're not before it, we're inside and
                # there's a custom mapping.
                return v
            else:
                # we're not after the range, we're not before it, we're inside and
                # there isn't a custom mapping. so our tile was removed, but it
                # appeared explicitly in the map and there's no mapping!
                print("WARNING: Got tile {}, but that was removed via {} and no mapping given!".format(tile, k))
                return 0
        # we are behind all things that are removed, just subtract the accumulated offset
        assert offset == self.removed_tiles
        return tile - offset


class Palette:
    """A Warcraft 1 Palette

    Palettes should be 256 colors, but some palettes need to be blended with the
    palette at 217. The blending rule is: The lower half of the palette up to
    index 128 has all colors that are 63,0,63 replaced with the global palette
    colors. For the upper half, all colors are taken from the global palette,
    unless the global palette color is 63,0,63.

    """

    GLOBAL_PALETTE_INDEX = 217

    def __init__(self, archive, chunk):
        self.archive = archive
        self.chunk = chunk
        self.rgb_palette = None

    def get_rgb_array(self):
        if not self.rgb_palette:
            palette = self.chunk.writable_copy()
            needs_blending = False
            if len(palette) < 768:
                palette.extend([0] * (768 - len(palette)))
                needs_blending = True
            if needs_blending:# if self.index in [191, 194, 197]:
                gpalette = self.archive[self.GLOBAL_PALETTE_INDEX]
                for i in range(128):
                    idx = i * 3
                    if palette[idx:idx + 3] == [63, 0, 63]:
                        palette[idx:idx + 3] = gpalette[idx:idx + 3]
                for i in range(128, 256):
                    idx = i * 3
                    if gpalette[idx:idx + 3] != [63, 0, 63]:
                        palette[idx:idx + 3] = gpalette[idx:idx + 3]
            for i in range(768):
                palette[i] <<= 2
            self.rgb_palette = palette
        return self.rgb_palette
