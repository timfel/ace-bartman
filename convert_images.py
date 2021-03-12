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
from warchive.img import Image, Spritesheet, Tileset


TILE_SIZE = 16


DATA = {
    # "CURSORS": [
    #     "graphics/ui/cursors/upper_left_arrow.png",
    #     "graphics/ui/cursors/magnifying_glass.png",
    #     "graphics/ui/cursors/red_crosshair.png",
    # ],
    "HUMAN_PANEL": [
        Spritesheet("human_panel_portraits", 191, 361),
        Image("human_panel_gold_icon", 191, 406),
        Image("human_panel_wood_icon", 217, 407),
        Image("human_panel_percent_complete", 217, 410),
        Image("human_panel_icon_border", 255, 364),
        Spritesheet("human_panel_icon_select", 191, 359),
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
        }),
        Spritesheet("forest_human_footman", 191, 279),
        Spritesheet("forest_orc_grunt", 191, 280),
        Spritesheet("forest_human_peasant", 191, 281),
        Spritesheet("forest_orc_peon", 191, 282),
        Spritesheet("forest_human_catapult", 191, 283),
        Spritesheet("forest_orc_catapult", 191, 284),
        Spritesheet("forest_human_knight", 191, 285),
        Spritesheet("forest_orc_raider", 191, 286),
        Spritesheet("forest_human_archer", 191, 287),
        Spritesheet("forest_orc_spearman", 191, 288),
        Spritesheet("forest_human_conjurer", 191, 289),
        Spritesheet("forest_orc_warlock", 191, 290),
        Spritesheet("forest_human_cleric", 191, 291),
        Spritesheet("forest_orc_necrolyte", 191, 292),
        Spritesheet("forest_human_medivh", 191, 293),
        Spritesheet("forest_human_lothar", 191, 294),
        Spritesheet("forest_neutral_wounded", 191, 295),
        Spritesheet("forest_neutral_grizelda,garona", 191, 296),
        Spritesheet("forest_neutral_ogre", 191, 297),
        Spritesheet("forest_neutral_spider", 191, 298),
        Spritesheet("forest_neutral_slime", 191, 299),
        Spritesheet("forest_neutral_fire_elemental", 191, 300),
        Spritesheet("forest_neutral_scorpion", 191, 301),
        Spritesheet("forest_neutral_brigand", 191, 302),
        Spritesheet("forest_neutral_the_dead", 191, 303),
        Spritesheet("forest_neutral_skeleton", 191, 304),
        Spritesheet("forest_neutral_daemon", 191, 305),
        Spritesheet("forest_neutral_water_elemental", 191, 306),
        Spritesheet("forest_neutral_dead_bodies", 191, 326),
        Spritesheet("forest_human_peasant_with_wood", 191, 327),
        Spritesheet("forest_orc_peon_with_wood", 191, 328),
        Spritesheet("forest_human_peasant_with_gold", 191, 329),
        Spritesheet("forest_orc_peon_with_gold", 191, 330),

        Spritesheet("forest_missile_fireball", 217, 347),
        Spritesheet("forest_missile_catapult_projectile", 191, 348),
        Spritesheet("forest_missile_arrow", 217, 349),
        Spritesheet("forest_missile_poison_cloud", 191, 350),
        Spritesheet("forest_missile_rain_of_fire", 191, 351),
        Spritesheet("forest_missile_small_fire", 191, 352),
        Spritesheet("forest_missile_large_fire", 191, 353),
        Spritesheet("forest_missile_explosion", 191, 354),
        Spritesheet("forest_missile_healing", 217, 355),
        Spritesheet("forest_missile_building_collapse", 191, 356),
        Spritesheet("forest_missile_water_elemental_projectile", 217, 357),
        Spritesheet("forest_missile_fireball_2", 191, 358),

        Spritesheet("forest_human_farm", 191, 307),
        Spritesheet("forest_orc_farm", 191, 308),
        Spritesheet("forest_human_barracks", 191, 309),
        Spritesheet("forest_orc_barracks", 191, 310),
        Spritesheet("forest_human_church", 191, 311),
        Spritesheet("forest_orc_temple", 191, 312),
        Spritesheet("forest_human_tower", 191, 313),
        Spritesheet("forest_orc_tower", 191, 314),
        Spritesheet("forest_human_town_hall", 191, 315),
        Spritesheet("forest_orc_town_hall", 191, 316),
        Spritesheet("forest_human_lumber_mill", 191, 317),
        Spritesheet("forest_orc_lumber_mill", 191, 318),
        Spritesheet("forest_human_stable", 191, 319),
        Spritesheet("forest_orc_kennel", 191, 320),
        Spritesheet("forest_human_blacksmith", 191, 321),
        Spritesheet("forest_orc_blacksmith", 191, 322),
        Spritesheet("forest_human_stormwind_keep", 191, 323),
        Spritesheet("forest_orc_blackrock_spire", 191, 324),
        Spritesheet("forest_neutral_gold_mine", 191, 325),
        Spritesheet("forest_human_farm_construction", 191, 331),
        Spritesheet("forest_orc_farm_construction", 191, 332),
        Spritesheet("forest_human_barracks_construction", 191, 333),
        Spritesheet("forest_orc_barracks_construction", 191, 334),
        Spritesheet("forest_human_church_construction", 191, 335),
        Spritesheet("forest_orc_temple_construction", 191, 336),
        Spritesheet("forest_human_tower_construction", 191, 337),
        Spritesheet("forest_orc_tower_construction", 191, 338),
        Spritesheet("forest_human_town_hall_construction", 191, 339),
        Spritesheet("forest_orc_town_hall_construction", 191, 340),
        Spritesheet("forest_human_lumber_mill_construction", 191, 341),
        Spritesheet("forest_orc_lumber_mill_construction", 191, 342),
        Spritesheet("forest_human_stable_construction", 191, 343),
        Spritesheet("forest_orc_kennel_construction", 191, 344),
        Spritesheet("forest_human_blacksmith_construction", 191, 345),
        Spritesheet("forest_orc_blacksmith_construction", 191, 346),
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
