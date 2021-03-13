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


from warchive.img import Tileset


CAMPAIGN_MAPS_START_IDX = 117


MAPPED_TILES = {
    "for": {
        (0x000, 0x00F): 0x10, # walls until 4-way
        (0x011, 0x01B): 0x10, # walls between 4-way and 4-way-broken
        (0x01D, 0x024): None, # walls between 4-way-broken and 4-way-remains
        (0x026, 0x028): None, # remains of walls until blackended remains of buildings
        (0x038, 0x045): 0x46, # all roads up to the first (singular) one until the trees
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
    },
    # "swa": {},
    # "dun": {},
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
    if code != 0:
        import pdb; pdb.set_trace()
    return


def record_tileset(tileset):
    tileset.mapped_tiles = MAPPED_TILES[tileset.name]
    TILESETS[tileset.name] = tileset


def spritesheets(data, out, bindir):
    imgdir = os.path.join(out, "imgs")
    os.makedirs(imgdir, exist_ok=True)

    rgb2amiga = os.path.join(bindir, 'bin', 'Rgb2Amiga')
    bitmap_conv = os.path.join(bindir, 'bin', 'bitmap_conv')
    tileset_conv = os.path.join(bindir, 'bin', 'tileset_conv')
    palette_conv = os.path.join(bindir, 'bin', 'palette_conv')
    w_h_re = re.compile(r"PNG image data, (\d+) x (\d+),")
    transparency = r'\#BBBBBB'

    for name, tileset in TILESETS.items():
        os.makedirs(os.path.join(imgdir, name), exist_ok=True)
        inputfiles = []
        pngfiles = []
        bmfiles = []

        inputfiles.append(f"{os.path.join(imgdir, name)}.bmp")
        pngfiles.append(inputfiles[-1].replace(".bmp", ""))
        bmfiles.append(inputfiles[-1].replace(".bmp", ".bm"))
        try:
            with open(inputfiles[-1], "xb") as f:
                tileset.write(f)
        except FileExistsError:
            # only write the tileset once
            pass

        for k,v in MAP_SPRITESHEETS.items():
            # TODO: extract all the spritesheets using the palette of that tileset

            # Then add them to inputfiles, outputfiles, bmfiles

            # inputfiles.append(f"{os.path.join(imgdir, name, k)}.bmp")
            # pngfiles.append(inputfiles[-1].replace(".bmp", ""))
            # bmfiles.append(inputfiles[-1].replace(".bmp", ".bm"))
            pass

        inargs = " -i ".join(inputfiles)
        outargs = " -o ".join(pngfiles)
        system(f"{rgb2amiga} -c 32 -f png-gpl -s ! -i {inargs} -o {outargs}")
        palette = os.path.join(imgdir, f"{name.lower()}.plt")
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

        # first one is the tileset
        system(f"{tileset_conv} {pngfiles[0]}.png {Tileset.TILE_SIZE} {bmfiles[0]} -plt {palette}")



def maps(data, out):
    data = os.path.join(data, ".")
    mapdir = os.path.join(out, "maps")
    os.makedirs(mapdir, exist_ok=True)
    palettes = os.path.join(out, ".")

    archive = WarArchive(os.path.join(data, "DATA.WAR"))
    archive.get_map(117).get_tiles()

    for idx, m in enumerate(["human", "orc"] * 12):
        lvl = idx // 2 + 1
        map = archive.get_map(CAMPAIGN_MAPS_START_IDX + idx)
        map.name = f"{m}{lvl}"
        print(map.name, map.get_briefing())

        record_tileset(map.get_tileset())
        with open(f"{os.path.join(mapdir, map.name)}.map", "wb") as f:
            map.write(f)
        break


if __name__ == "__main__":
    import sys
    from argparse import ArgumentParser
    parser = ArgumentParser(sys.argv[0])
    parser.add_argument('--data', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--prefix', required=True)
    parsed_args = parser.parse_args(sys.argv[1:])
    maps(parsed_args.data, parsed_args.output)
    spritesheets(parsed_args.data, parsed_args.output, parsed_args.prefix)
