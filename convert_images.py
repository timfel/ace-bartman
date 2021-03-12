import glob
import math
import os
import re
import subprocess

try:
    from warchive.archive import WarArchive
except ImportError:
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), "python"))
    from warchive.archive import WarArchive


from warchive.bitmap import Bitmap


TILE_SIZE = 16

TILESET_CONVERSION = {
    "forest": {
        "mapped_tiles": {
            (0x000, 0x00F): None, # first line
            (0x010, 0x01B): None, # walls on second line between 4-way and 4-way-broken
            (0x01C, 0x021): None, # walls on second and third line between 4-way-broken and 4-way-remains
            (0x023, 0x028): None, # remains of walls until blackended remains of buildings
            (0x039, 0x046): None, # all roads except the first (singular) one until the trees
            # Only trees are in the saved maps until here, so we can just subtract an offset from them.
            # Now start the tiles that we'll have to re-map and not just subtract an offset
            (0x061, 0x069): 0x06D, # grass transitions -> all map to 0x06D (just green grass)
            (0x070, 0x070): 0x06D, # grass
            (0x074, 0x07A): 0x06D, # grass
            (0x084, 0x085): None, # weird water
            (0x086, 0x08E): 0x06D, # grass
            (0x091, 0x092): None, # weird water
            (0x09B, 0x09F): 0x06D, # grass
            (0x100, 0x103): 0x06D, # grass
            (0x108, 0x10F): 0x06D, # grass
            (0x110, 0x118): 0x06D, # grass
        }
    }
}


class Entry:
    def __init__(self, name, ident, chunk, *args):
        self.name = name
        self.ident = ident
        self.chunk = chunk
        self.args = args


class Gfu(Entry):
    pass


class Image(Entry):
    pass


class Palette:
    """A Warcraft 1 Palette

    Palettes should be 256 colors, but some palettes need to be blended with the
    palette at 217. The blending rule is: The lower half of the palette up to
    index 128 has all colors that are 63,0,63 replaced with the global palette
    colors. For the upper half, all colors are taken from the global palette,
    unless the global palette color is 63,0,63.

    """

    def __init__(self, archive, index):
        self.archive = archive
        self.index = index
        self.rgb_palette = None

    def get_rgb_array(self):
        if not self.rgb_palette:
            palette = archive[self.index].writable_copy()
            if len(palette) < 768:
                palette.extend([0] * (768 - len(palette)))
            if self.index in [191, 194, 197]:
                gpalette = archive[217]
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


class Tileset(Entry):
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
    def __init__(self, *args, mapped_tiles=None):
        super().__init__(self, *args)
        if mapped_tiles:
            self.mapped_tiles = mapped_tiles
            self._removed_tiles = -1
        else:
            self.mapped_tiles = {}
            self._removed_tiles = 0

    @property
    def removed_tiles(self):
        if self._removed_tiles < 0:
            removed = 0
            for inclusive_removed_range in self.mapped_tiles.keys():
                removed += (inclusive_removed_range[1] - inclusive_removed_range[0] + 1)
            self._removed_tiles = removed
        return self._removed_tiles

    def extract(self, archive):
        palette = Palette(archive, self.chunk + 1).get_rgb_array()
        mini = archive[self.chunk]
        mega = archive[self.chunk - 1]
        numtiles = len(mega) // 8
        output_num_tiles = numtiles - self.removed_tiles
        width = 16
        height = output_num_tiles * 16
        image = memoryview(bytearray(bytearray([0]) * width * height))

        for tilenumber in range(numtiles):
            if self.is_removed(tilenumber):
                continue
            tile_info = mega[tilenumber * 8:]
            for y_half in range(2):
                for x_half in range(2):
                    output_x = x_half * 8 # either 0 or 8
                    output_y = self.map_tile(tilenumber) * 16 + y_half * 8
                    current_output_pixel = output_x + output_y * width
                    # multiply index into tile_info by 2, since we're reading shorts, not bytes
                    offset_of_quarter_tile = tile_info[(x_half + y_half * 2) * 2:].read16()
                    input_pixel_start = ((offset_of_quarter_tile & 0xFFFC) << 1) & 0xFFFF
                    mirror_x = bool(offset_of_quarter_tile & 2)
                    mirror_y = bool(offset_of_quarter_tile & 1)
                    x_range = range(8)
                    y_range = range(8)
                    if mirror_x:
                        x_range = list(reversed(x_range))
                    if mirror_y:
                        y_range = list(reversed(y_range))
                    for y in y_range:
                        for x in x_range:
                            image[current_output_pixel] = mini[input_pixel_start + x + y * 8]
                            current_output_pixel += 1
                        current_output_pixel += 8

        return Bitmap(width, height, image, rgb_palette=palette)

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


DATA = {
    # "CURSORS": [
    #     "graphics/ui/cursors/upper_left_arrow.png",
    #     "graphics/ui/cursors/magnifying_glass.png",
    #     "graphics/ui/cursors/red_crosshair.png",
    # ],
    "HUMAN_PANEL": [
        Gfu("human_panel_portraits", 191, 361),
        Image("human_panel_gold_icon", 191, 406),
        Image("human_panel_wood_icon", 217, 407),
        Image("human_panel_percent_complete", 217, 410),
        Image("human_panel_icon_border", 255, 364),
        Gfu("human_panel_icon_select", 191, 359),
        Image("human_panel", 255, 235)
    ],
    # "ORC_PANEL": [
    #     "graphics/tilesets/forest/portrait_icons.png",
    #     "graphics/ui/gold_icon_1.png",
    #     "graphics/ui/lumber_icon_1.png",
    #     "graphics/ui/percent_complete.png",
    #     "graphics/ui/orc/icon_border.png",
    #     "graphics/ui/orc/icon_selection_boxes.png",
    #     "graphics/ui/orc/panel_2.png",
    # ],
    "FOREST_TILESET": [
        Tileset("forest", 190, mapped_tiles={
            (0x000, 0x00F): None, # walls until 4-way
            (0x011, 0x01B): None, # walls between 4-way and 4-way-broken
            (0x01D, 0x024): None, # walls between 4-way-broken and 4-way-remains
            (0x026, 0x028): None, # remains of walls until blackended remains of buildings
            (0x038, 0x045): None, # all roads except the first (singular) one until the trees
            # Only trees are in the saved maps until here, so we can just subtract an offset from them.
            # Now start the tiles that we'll have to re-map and not just subtract an offset
            (0x061, 0x069): 0x06D, # grass transitions -> all map to 0x06D (just green grass)
            (0x070, 0x070): 0x06D, # grass
            (0x074, 0x07B): 0x06D, # grass
            (0x084, 0x085): None, # weird water
            (0x086, 0x08E): 0x06D, # grass
            (0x091, 0x092): None, # weird water
            (0x09B, 0x0a3): 0x06D, # grass
            (0x0a7, 0x0b7): 0x06D, # grass
        }),
        Gfu("forest_human_footman", 191, 279),
        Gfu("forest_orc_grunt", 191, 280),
        Gfu("forest_human_peasant", 191, 281),
        Gfu("forest_orc_peon", 191, 282),
        Gfu("forest_human_catapult", 191, 283),
        Gfu("forest_orc_catapult", 191, 284),
        Gfu("forest_human_knight", 191, 285),
        Gfu("forest_orc_raider", 191, 286),
        Gfu("forest_human_archer", 191, 287),
        Gfu("forest_orc_spearman", 191, 288),
        Gfu("forest_human_conjurer", 191, 289),
        Gfu("forest_orc_warlock", 191, 290),
        Gfu("forest_human_cleric", 191, 291),
        Gfu("forest_orc_necrolyte", 191, 292),
        Gfu("forest_human_medivh", 191, 293),
        Gfu("forest_human_lothar", 191, 294),
        Gfu("forest_neutral_wounded", 191, 295),
        Gfu("forest_neutral_grizelda,garona", 191, 296),
        Gfu("forest_neutral_ogre", 191, 297),
        Gfu("forest_neutral_spider", 191, 298),
        Gfu("forest_neutral_slime", 191, 299),
        Gfu("forest_neutral_fire_elemental", 191, 300),
        Gfu("forest_neutral_scorpion", 191, 301),
        Gfu("forest_neutral_brigand", 191, 302),
        Gfu("forest_neutral_the_dead", 191, 303),
        Gfu("forest_neutral_skeleton", 191, 304),
        Gfu("forest_neutral_daemon", 191, 305),
        Gfu("forest_neutral_water_elemental", 191, 306),
        Gfu("forest_neutral_dead_bodies", 191, 326),
        Gfu("forest_human_peasant_with_wood", 191, 327),
        Gfu("forest_orc_peon_with_wood", 191, 328),
        Gfu("forest_human_peasant_with_gold", 191, 329),
        Gfu("forest_orc_peon_with_gold", 191, 330),

        Gfu("forest_missile_fireball", 217, 347),
        Gfu("forest_missile_catapult_projectile", 191, 348),
        Gfu("forest_missile_arrow", 217, 349),
        Gfu("forest_missile_poison_cloud", 191, 350),
        Gfu("forest_missile_rain_of_fire", 191, 351),
        Gfu("forest_missile_small_fire", 191, 352),
        Gfu("forest_missile_large_fire", 191, 353),
        Gfu("forest_missile_explosion", 191, 354),
        Gfu("forest_missile_healing", 217, 355),
        Gfu("forest_missile_building_collapse", 191, 356),
        Gfu("forest_missile_water_elemental_projectile", 217, 357),
        Gfu("forest_missile_fireball_2", 191, 358),

        Gfu("forest_human_farm", 191, 307),
        Gfu("forest_orc_farm", 191, 308),
        Gfu("forest_human_barracks", 191, 309),
        Gfu("forest_orc_barracks", 191, 310),
        Gfu("forest_human_church", 191, 311),
        Gfu("forest_orc_temple", 191, 312),
        Gfu("forest_human_tower", 191, 313),
        Gfu("forest_orc_tower", 191, 314),
        Gfu("forest_human_town_hall", 191, 315),
        Gfu("forest_orc_town_hall", 191, 316),
        Gfu("forest_human_lumber_mill", 191, 317),
        Gfu("forest_orc_lumber_mill", 191, 318),
        Gfu("forest_human_stable", 191, 319),
        Gfu("forest_orc_kennel", 191, 320),
        Gfu("forest_human_blacksmith", 191, 321),
        Gfu("forest_orc_blacksmith", 191, 322),
        Gfu("forest_human_stormwind_keep", 191, 323),
        Gfu("forest_orc_blackrock_spire", 191, 324),
        Gfu("forest_neutral_gold_mine", 191, 325),
        Gfu("forest_human_farm_construction", 191, 331),
        Gfu("forest_orc_farm_construction", 191, 332),
        Gfu("forest_human_barracks_construction", 191, 333),
        Gfu("forest_orc_barracks_construction", 191, 334),
        Gfu("forest_human_church_construction", 191, 335),
        Gfu("forest_orc_temple_construction", 191, 336),
        Gfu("forest_human_tower_construction", 191, 337),
        Gfu("forest_orc_tower_construction", 191, 338),
        Gfu("forest_human_town_hall_construction", 191, 339),
        Gfu("forest_orc_town_hall_construction", 191, 340),
        Gfu("forest_human_lumber_mill_construction", 191, 341),
        Gfu("forest_orc_lumber_mill_construction", 191, 342),
        Gfu("forest_human_stable_construction", 191, 343),
        Gfu("forest_orc_kennel_construction", 191, 344),
        Gfu("forest_human_blacksmith_construction", 191, 345),
        Gfu("forest_orc_blacksmith_construction", 191, 346),
    ],
    # "SWAMP_TILESET": [
    #     "graphics/tilesets/swamp/terrain.png",
    #     "graphics/human/units/*.png",
    #     "graphics/neutral/units/*.png",
    #     "graphics/orc/units/*.png",
    #     "graphics/missiles/*.png",
    #     "graphics/tilesets/swamp/human/buildings/*.png",
    #     "graphics/tilesets/swamp/orc/buildings/*.png",
    #     "graphics/tilesets/swamp/neutral/buildings/*.png",
    # ],
    # "DUNGEON_TILESET": [
    #     "graphics/tilesets/dungeon/terrain.png",
    #     "graphics/human/units/*.png",
    #     "graphics/neutral/units/*.png",
    #     "graphics/orc/units/*.png",
    #     "graphics/missiles/*.png",
    #     "graphics/tilesets/dungeon/neutral/buildings/*.png",
    # ],
}

def system(s):
    code = os.system(s)
    if code != 0:
        import pdb; pdb.set_trace()
    return

def main(data, out, bindir):
    rgb2amiga = os.path.join(bindir, 'bin', 'Rgb2Amiga')
    bitmap_conv = os.path.join(bindir, 'bin', 'bitmap_conv')
    tileset_conv = os.path.join(bindir, 'bin', 'tileset_conv')
    palette_conv = os.path.join(bindir, 'bin', 'palette_conv')
    w_h_re = re.compile(r"PNG image data, (\d+) x (\d+),")
    transparency = r'\#BBBBBB'

    data = os.path.join(data, ".")
    out = os.path.join(out, ".")

    for name,set in DATA.items():
        inputfiles = []
        pngfiles = []
        bmfiles = []
        for pattern in set:
            for i in glob.glob(os.path.join(data, pattern)):
                output = i.replace(data, os.path.join(out, name.lower()))
                inputfiles.append(i)
                pngfiles.append(output)
                os.makedirs(os.path.dirname(output), exist_ok=True)
                bmfiles.append(output.replace(".png", ".bm"))

        inargs = " -i ".join(inputfiles)
        outargs = " -o ".join(pngfiles)
        system(f"{rgb2amiga} -c 32 -f png-gpl -s ! -i {inargs} -o {outargs}")
        palette = os.path.join(out, f"{name.lower()}.plt")
        system(f"{palette_conv} {pngfiles[0]}.gpl {palette}")
        for bmfile,pngfile in zip(bmfiles, pngfiles):
            # TODO: mask color is transparency
            info = subprocess.check_output(f"file {pngfile}.png", shell=True).decode()
            w, h = (int(x) for x in w_h_re.search(info).groups())
            if w % 16:
                if w > 16:
                    crop_left = math.floor((w % 16) / 2)
                    crop_right = math.ceil((w % 16) / 2)
                    system(f"convert {pngfile}.png -gravity East -crop {w - crop_left}x{h}+0+0 +repage {pngfile}.png")
                    system(f"convert {pngfile}.png -gravity West -crop {w - crop_left - crop_right}x{h}+0+0 +repage {pngfile}.png")
                else:
                    add_left = math.floor((16 - w) / 2)
                    add_right = math.ceil((16 - w) / 2)
                    system(f"convert {pngfile}.png -gravity East -background {transparency} -splice {add_left}x0 +repage {pngfile}.png")
                    system(f"convert {pngfile}.png -gravity West -background {transparency} -splice {add_right}x0 +repage {pngfile}.png")
            system(f"{bitmap_conv} {palette} {pngfile}.png -o {bmfile} -mc {transparency}")
        if name.endswith("_TILESET"):
            system(f"{tileset_conv} {pngfiles[0]}.png {TILE_SIZE} {bmfiles[0]} -plt {palette}")


if __name__ == "__main__":
    import sys
    from argparse import ArgumentParser
    parser = ArgumentParser(sys.argv[0])
    parser.add_argument('--data', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--prefix', required=True)
    parsed_args = parser.parse_args(sys.argv[1:])

    ts = DATA["FOREST_TILESET"][0]
    archive = WarArchive(os.path.join(parsed_args.data, "DATA.WAR"))
    with open("test.bmp", "wb") as f:
        ts.extract(archive).write(f)

    # main(parsed_args.data, parsed_args.output, parsed_args.prefix)
