#ifndef MAP_H
#define MAP_H

#include "ace/types.h"

/*
 * 
 * dbu_ ____ tttt tttt - (d)iscovered, 
 * 
 * 
 * 11bb bbqq qqii iiii - 4x4 (b)uilding id (gold, barracks, mill, Stable, Hall, Church = 11), (q)uadrant of building, unitlist (i)ndex
 * 101b bbqq qqii iiii - 3x3 (b)uilding id (smith, tower, farm), (q)uadrant of building, unitlist (i)ndex
 * 1001 bqqq qqii iiii - 5x5 (b)uilding id (blackrock, stormwind), (q)uadrant of building, unitlist (i)ndex
 * 01uu uuuu iiii iiii - (u)nused, unit (i)d
 * 00wb dhau tttt tttt - (w)alkable, (b)uildable, (d)iscovered, (h)arvestable, (a)ttackable, (u)nused, original (t)ile from map data
 */

typedef UWORD* tileInfo;

#define tileInfoIsBuildingMacro(x) BTST(*x, 0)
#define tileInfoIsUnitMacro(x) BTST(*x, 1)
#define tileInfoIsDiscovered(x) BTST(*x, 0)

#ifdef ACE_DEBUG

#else
#endif

struct tileInfoFull {
    unsigned isBuilding:1;
    unsigned isUnit:1;
    union {
        struct {
            unsigned is4x4:1;
            unsigned is3x3:1;
            unsigned is5x5:1;
        } size;
        struct {
            unsigned padding:1;
            unsigned type:4;
            unsigned quadrant:4;
            unsigned index:6;
        } four;
        struct {
            unsigned padding:2;
            unsigned type:3;
            unsigned quadrant:4;
            unsigned index:6;
        } three;
        struct {
            unsigned padding:3;
            unsigned type:1;
            unsigned quadrant:5;
            unsigned index:6;
        } five;
    } building;
    struct {
        unsigned padding:6;
        unsigned index:8;
    } unit;
    struct {
        unsigned isWalkable:1;
        unsigned isBuildable:1;
        unsigned isDiscovered:1;
        unsigned isHarvestable:1;
        unsigned isAttackable:1;
        unsigned unused:1;
        unsigned originalTileIndex:8;
    } info;
};

#endif
