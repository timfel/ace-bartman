* tilesets are converted and stripped of many tiles to go under 256 tiles
* spritesheets are converted, units are stripped of many frames and the sheets are cropped
* buildings are rendered with the "solid grass" and "solid swamp" background colors to avoid needing masks for them
* buildings will be marked in the tileinfo array and then (partially) blitted in the tiledraw callback
* units will be bobs
* unit death animations are mostly merged into just human dead body, orc dead body, skeleton
* movement is only "still frame" + "movement frame"
* attack is only "still frame" + "attack frame", with sometimes the attack frame being the same as the movement frame, but played faster
* we use sprites for mouse cursor and selection rectangles
* we cannot quickly mirror units horizontally, so we generate all directions. to save memory, maybe we'll only use 4 instead of 8 directions (could be a runtime detection thing so we have better visuals when more chipram is available)

the tile info, 64*64 short values

10wb dhau tttt tttt - (w)alkable, (b)uildable, (d)iscovered, (h)arvestable, (a)ttackable, (u)nused, original (t)ile from map data
11uu uuuu iiii iiii - (u)nused, unit (i)d
01bb bbqq qqii iiii - 4x4 (b)uilding id (gold, barracks, mill, Stable, Hall, Church = 11), (q)uadrant of building, unitlist (i)ndex
001b bbqq qqii iiii - 3x3 (b)uilding id (smith, tower, farm), (q)uadrant of building, unitlist (i)ndex
000b bqqq qqii iiii - 5x5 (b)uilding id (blackrock, stormwind), (q)uadrant of building, unitlist (i)ndex


each frame:
 - mouse sprite move to mouse location
 - mouse sprite update if over building or unit
 - check cursor buttons and move camera
 - check mouse corner position and move camera
 - check mouse down and act on it with button action state (usually reading the tile underneath and selected units)
 - tilebuffer refresh
   - use tile callback to draw buildings
 - iterate bobs, draw iff on screen
 - iterate units and execute their actions on them
 - iterate unit ai and execute it
 - iterate ai requests and execute them
