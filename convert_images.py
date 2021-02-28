import glob
import math
import os
import re
import subprocess

TILE_SIZE = 16

DATA = {
    # "CURSORS": [
    #     "graphics/ui/cursors/upper_left_arrow.png",
    #     "graphics/ui/cursors/magnifying_glass.png",
    #     "graphics/ui/cursors/red_crosshair.png",
    # ],
    "HUMAN_PANEL": [
        "graphics/tilesets/forest/portrait_icons.png",
        "graphics/ui/gold_icon_1.png",
        "graphics/ui/lumber_icon_1.png",
        "graphics/ui/percent_complete.png",
        "graphics/ui/human/icon_border.png",
        "graphics/ui/human/icon_selection_boxes.png",
        "graphics/ui/human/panel_2.png",
    ],
    "ORC_PANEL": [
        "graphics/tilesets/forest/portrait_icons.png",
        "graphics/ui/gold_icon_1.png",
        "graphics/ui/lumber_icon_1.png",
        "graphics/ui/percent_complete.png",
        "graphics/ui/orc/icon_border.png",
        "graphics/ui/orc/icon_selection_boxes.png",
        "graphics/ui/orc/panel_2.png",
    ],
    "FOREST_TILESET": [
        "graphics/tilesets/forest/terrain.png",
        "graphics/human/units/*.png",
        "graphics/neutral/units/*.png",
        "graphics/orc/units/*.png",
        "graphics/missiles/*.png",
        "graphics/tilesets/forest/human/buildings/*.png",
        "graphics/tilesets/forest/orc/buildings/*.png",
        "graphics/tilesets/forest/neutral/buildings/*.png",
    ],
    "SWAMP_TILESET": [
        "graphics/tilesets/swamp/terrain.png",
        "graphics/human/units/*.png",
        "graphics/neutral/units/*.png",
        "graphics/orc/units/*.png",
        "graphics/missiles/*.png",
        "graphics/tilesets/swamp/human/buildings/*.png",
        "graphics/tilesets/swamp/orc/buildings/*.png",
        "graphics/tilesets/swamp/neutral/buildings/*.png",
    ],
    "DUNGEON_TILESET": [
        "graphics/tilesets/dungeon/terrain.png",
        "graphics/human/units/*.png",
        "graphics/neutral/units/*.png",
        "graphics/orc/units/*.png",
        "graphics/missiles/*.png",
        "graphics/tilesets/dungeon/neutral/buildings/*.png",
    ],
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
    main(parsed_args.data, parsed_args.output, parsed_args.prefix)
