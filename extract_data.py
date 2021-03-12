import os

try:
    from warchive.archive import WarArchive
except ImportError:
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), "python"))
    from warchive.archive import WarArchive


CAMPAIGN_MAPS_START_IDX = 117


MAPPED_TILES = {
    "forest": {
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
    "swamp": {},
    "dungeon": {},
}


def main(data, out):
    data = os.path.join(data, ".")
    mapdir = os.path.join(out, "maps")
    imgdir = os.path.join(out, "imgs")
    os.makedirs(mapdir, exist_ok=True)
    os.makedirs(imgdir, exist_ok=True)
    palettes = os.path.join(out, ".")

    archive = WarArchive(os.path.join(data, "DATA.WAR"))
    archive.get_map(117).get_tiles()

    for idx, m in enumerate(["human", "orc"] * 12):
        lvl = idx // 2 + 1
        map = archive.get_map(CAMPAIGN_MAPS_START_IDX + idx)
        map.name = f"{m}{lvl}"
        print(map.name, map.get_briefing())

        tileset = map.get_tileset()
        tileset.mapped_tiles = MAPPED_TILES[tileset.name]
        try:
            with open(f"{os.path.join(imgdir, str(tileset.idx))}.bmp", "xb") as f:
                tileset.write(f)
        except FileExistsError:
            # only write the tileset once
            pass

        with open(f"{os.path.join(mapdir, map.name)}.map", "wb") as f:
            map.write(f)
        return


if __name__ == "__main__":
    import sys
    from argparse import ArgumentParser
    parser = ArgumentParser(sys.argv[0])
    parser.add_argument('--data', required=True)
    parser.add_argument('--output', required=True)
    parsed_args = parser.parse_args(sys.argv[1:])
    main(parsed_args.data, parsed_args.output)
