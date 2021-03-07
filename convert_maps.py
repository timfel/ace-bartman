import os

try:
    from warchive.archive import WarArchive
except ImportError:
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), "python"))
    from warchive.archive import WarArchive


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
