import glob
import os
import re
import subprocess

try:
    from warchive.archive import WarArchive
except ImportError:
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), "python"))
    from warchive.archive import WarArchive


from warchive.img import Tileset, Spritesheet


CAMPAIGN_MAPS_START_IDX = 117


MAPPED_TILES = {
    "for": {
        (0x00, 0x0F): 0x10, # walls until 4-way
        (0x11, 0x1B): 0x10, # walls between 4-way and 4-way-broken
        (0x1D, 0x24): None, # walls between 4-way-broken and 4-way-remains
        (0x26, 0x28): None, # remains of walls until blackended remains of buildings
        (0x38, 0x45): 0x46, # all roads up to the first (singular) one until the trees
        # Only trees are in the saved maps until here, so we can just subtract an offset from them.
        # Now start the tiles that we'll have to re-map and not just subtract an offset
            (0x61, 0x69): 0x6D, # grass transitions -> all map to 0x6D (just green grass)
        (0x70, 0x70): 0x6D, # grass
        (0x74, 0x7B): 0x6D, # grass
        (0x84, 0x85): None, # weird water
        (0x86, 0x8E): 0x6D, # grass
        (0x91, 0x92): None, # weird water
        (0x9B, 0xa3): 0x6D, # grass
        (0xa7, 0xb7): 0x6D, # grass
    },
    "swa": {
        (0x00, 0x0F): 0x10, # walls until 4-way
        (0x11, 0x1B): 0x10, # walls between 4-way and 4-way-broken
        (0x1D, 0x24): None, # walls between 4-way-broken and 4-way-remains
        (0x26, 0x29): None, # remains of walls until blackended remains of buildings
        (0x39, 0x39): 0x3a, # road mapping
        (0x3b, 0x47): 0x3a, # road mapping
        (0x65, 0x65): None, # black tile?
        (0x67, 0x67): 0x66, # grass
        (0x6b, 0x6c): 0x66, # grass
        (0x70, 0x71): 0x66, # grass
        (0x70, 0x71): 0x66, # grass
        (0x76, 0x76): 0x78, # grass stone deko
        (0x77, 0x77): 0x79, # grass tree deko
        (0x84, 0x84): 0x87, # grass deko
        (0x85, 0x85): 0x88, # grass deko
        (0x86, 0x86): 0x89, # grass deko
        (0x9c, 0x9c): 0x78, # grass stone deko
        (0x9d, 0x9d): 0x79, # grass tree deko
        (0xa9, 0xa9): 0x87, # grass deko
        (0xaa, 0xaa): 0x88, # grass deko
        (0xab, 0xab): 0x89, # grass deko
        (0xbe, 0xc5): 0x66, # grass
        (0xcb, 0xd2): 0x66, # grass
        (0xd8, 0xdf): 0x66, # grass
        (0xe7, 0xee): 0x66, # grass
        (0xf2, 0xf9): 0x66, # grass
        (0xff, 0x105): 0x66, # grass
        (0x109, 0x10f): 0x66, # grass
        (0x113, 0x11a): 0x66, # grass
    },
    "dun": {
        (0x00, 0x09): None,
        (0x2e, 0x2e): None,
        (0x34, 0x34): 0x35, # just darkness
        (0x39, 0x3a): 0x3b,
        (0x4b, 0x4c): 0x4d,
        (0x52, 0x56): 0x57, # ground
        (0x5e, 0x5e): 0x35,
        (0x63, 0x63): 0x35,
        (0x69, 0x6e): 0x57,
        (0x7e, 0x83): 0x57,
        (0x95, 0x9a): 0x57,
        (0xaa, 0xb0): 0x57,
        (0xb4, 0xb4): 0x35,
        (0xb6, 0xb6): 0x35,
        (0xb7, 0xb7): 0x57,
        (0xba, 0xba): 0x57,
        (0xc1, 0xc6): 0x57,
        (0xcc, 0xcc): 0x35,
        (0xcf, 0xcf): 0x35,
        (0xd5, 0xda): 0x57,
        (0xe7, 0xed): 0x57,
        (0xf0, 0xf0): 0x35,
        (0xf5, 0xf5): 0x35,
        (0xfe, 0x103): 0x57,
        (0x110, 0x111): 0x57,
        (0x128, 0x129): 0x57,
        (0x131, 0x134): 0x57,
    },
}


MAP_SPRITESHEETS = {
    "human_footman": 279,
    "orc_grunt": 280,
    "human_peasant": 281,
    "orc_peon": 282,
    "human_catapult": 283,
    "orc_catapult": 284,
    "human_knight": 285,
    "orc_raider": 286,
    "human_archer": 287,
    "orc_spearman": 288,
    "human_conjurer": 289,
    "orc_warlock": 290,
    "human_cleric": 291,
    "orc_necrolyte": 292,
    "human_medivh": 293,
    "human_lothar": 294,
    "neutral_wounded": 295,
    "neutral_grizelda,garona": 296,
    "neutral_ogre": 297,
    "neutral_spider": 298,
    "neutral_slime": 299,
    "neutral_fire_elemental": 300,
    "neutral_scorpion": 301,
    "neutral_brigand": 302,
    "neutral_the_dead": 303,
    "neutral_skeleton": 304,
    "neutral_daemon": 305,
    "neutral_water_elemental": 306,
    "neutral_dead_bodies": 326,
    "human_peasant_with_wood": 327,
    "orc_peon_with_wood": 328,
    "human_peasant_with_gold": 329,
    "orc_peon_with_gold": 330,

    # "missile_fireball": 217, 347,
    "missile_catapult_projectile": 348,
    # "missile_arrow": 217, 349,
    "missile_poison_cloud": 350,
    "missile_rain_of_fire": 351,
    "missile_small_fire": 352,
    "missile_large_fire": 353,
    "missile_explosion": 354,
    # "missile_healing": 217, 355,
    "missile_building_collapse": 356,
    # "missile_water_elemental_projectile": 217, 357,
    "missile_fireball_2": 358,

    "human_farm": 307,
    "orc_farm": 308,
    "human_barracks": 309,
    "orc_barracks": 310,
    "human_church": 311,
    "orc_temple": 312,
    "human_tower": 313,
    "orc_tower": 314,
    "human_town_hall": 315,
    "orc_town_hall": 316,
    "human_lumber_mill": 317,
    "orc_lumber_mill": 318,
    "human_stable": 319,
    "orc_kennel": 320,
    "human_blacksmith": 321,
    "orc_blacksmith": 322,
    "human_stormwind_keep": 323,
    "orc_blackrock_spire": 324,
    "neutral_gold_mine": 325,
    "human_farm_construction": 331,
    "orc_farm_construction": 332,
    "human_barracks_construction": 333,
    "orc_barracks_construction": 334,
    "human_church_construction": 335,
    "orc_temple_construction": 336,
    "human_tower_construction": 337,
    "orc_tower_construction": 338,
    "human_town_hall_construction": 339,
    "orc_town_hall_construction": 340,
    "human_lumber_mill_construction": 341,
    "orc_lumber_mill_construction": 342,
    "human_stable_construction": 343,
    "orc_kennel_construction": 344,
    "human_blacksmith_construction": 345,
    "orc_blacksmith_construction": 346,
}


DATA = {
    # "HUMAN_PANEL": [
    #     "graphics/tilesets/forest/portrait_icons.png",
    #     "graphics/ui/gold_icon_1.png",
    #     "graphics/ui/lumber_icon_1.png",
    #     "graphics/ui/percent_complete.png",
    #     "graphics/ui/human/icon_border.png",
    #     "graphics/ui/human/icon_selection_boxes.png",
    #     "graphics/ui/human/panel_2.png",
    # ],
    # "ORC_PANEL": [
    #     "graphics/tilesets/forest/portrait_icons.png",
    #     "graphics/ui/gold_icon_1.png",
    #     "graphics/ui/lumber_icon_1.png",
    #     "graphics/ui/percent_complete.png",
    #     "graphics/ui/orc/icon_border.png",
    #     "graphics/ui/orc/icon_selection_boxes.png",
    #     "graphics/ui/orc/panel_2.png",
    # ],
}


TILESETS = {}


def system(s):
    code = os.system(s)
    print("Running", s)
    if code != 0:
        print("ERROR")
        sys.exit(code)
    return


def record_tileset(tileset):
    tileset.mapped_tiles = MAPPED_TILES[tileset.name]
    TILESETS[tileset.name] = tileset


def spritesheets(out, bindir):
    imgdir = os.path.join(out, "imgs")
    os.makedirs(imgdir, exist_ok=True)

    rgb2amiga = os.path.join(bindir, 'Rgb2Amiga')
    bitmap_conv = os.path.join(bindir, 'bitmap_conv')
    tileset_conv = os.path.join(bindir, 'tileset_conv')
    palette_conv = os.path.join(bindir, 'palette_conv')
    w_h_re = re.compile(r"PNG image data, (\d+) x (\d+),")
    transparency = r'\#FF00FF'

    for name, tileset in TILESETS.items():
        os.makedirs(os.path.join(imgdir, name), exist_ok=True)
        inputfiles = []
        pngfiles = []
        bmfiles = []

        inputfiles.append(f"{os.path.join(imgdir, name)}.bmp")
        pngfiles.append(inputfiles[-1].replace(".bmp", ""))
        bmfiles.append(inputfiles[-1].replace(".bmp", ".bm"))
        with open(inputfiles[-1], "wb") as f:
            tileset.write(f)

        for k,v in MAP_SPRITESHEETS.items():
            inputfiles.append(f"{os.path.join(imgdir, name, k)}.bmp")
            pngfiles.append(inputfiles[-1].replace(".bmp", ""))
            bmfiles.append(inputfiles[-1].replace(".bmp", ".bm"))
            with open(inputfiles[-1], "wb") as f:
                Spritesheet(ARCHIVE, ARCHIVE[v], tileset.palette).write(f)

        inargs = " -i ".join(inputfiles)
        outargs = " -o ".join(pngfiles)
        system(f"{rgb2amiga} -c 32 -f png-gpl -s ! -i {inargs} -o {outargs}")
        palette = os.path.join(imgdir, f"{name.lower()}.plt")
        system(f"{palette_conv} {pngfiles[0]}.gpl {palette}")
        for bmfile,pngfile in zip(bmfiles, pngfiles):
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

        # first one is the tileset
        system(f"{tileset_conv} {pngfiles[0]}.png {Tileset.TILE_SIZE} {bmfiles[0]} -plt {palette}")



def maps(out):
    mapdir = os.path.join(out, "maps")
    os.makedirs(mapdir, exist_ok=True)
    palettes = os.path.join(out, ".")

    for idx, m in enumerate(["human", "orc"] * 12):
        lvl = idx // 2 + 1
        map = ARCHIVE.get_map(CAMPAIGN_MAPS_START_IDX + idx)
        map.name = f"{m}{lvl}"
        print(map.name, map.get_briefing())

        record_tileset(map.get_tileset())
        with open(f"{os.path.join(mapdir, map.name)}.map", "wb") as f:
            map.write(f)


if __name__ == "__main__":
    import sys
    from argparse import ArgumentParser
    parser = ArgumentParser(sys.argv[0])
    parser.add_argument('--data', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--prefix', required=True)
    parsed_args = parser.parse_args(sys.argv[1:])
    ARCHIVE = WarArchive(os.path.join(parsed_args.data, "DATA.WAR"))
    maps(parsed_args.output)
    spritesheets(parsed_args.output, parsed_args.prefix)
