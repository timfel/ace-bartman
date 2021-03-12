### The maps

I extract the maps from DATA.WAR directly. There's no heuristic, it's just
hardcoded that maps start at chunk index 117 and that there's 12 for each race.

Maps encode the roads and walls directly in the tiles. The tileset info is
extracted from the maps directly and lazily extracted. The first 4 bytes of the
map are the name of the terrain. In the engine when loading a map, we use that
string to construct the loading path for the terrain bitmap as well as the
terrain palette (they have the same number for us.) After that come 64x64 bytes
of tile indices. To be able to fit, we reduce the tilemaps in our extraction
process by throwing out things like dark/middle/light grasses that don't really
shine in 32 colors anyway.
