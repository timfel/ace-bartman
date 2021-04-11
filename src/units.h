#ifndef UNITS_H
#define UNITS_H

#include <ace/utils/bitmap.h>
#include <ace/utils/file.h>

void *createUnitManager(void);

struct unitType {
    tBitMap *spritesheet;
    UBYTE maxHP;
    unsigned hasMana:1;
    unsigned isBuilding:1;
    unsigned speed:4;
};

extern struct unitType UnitTypes[];

struct unitLocation {
    unsigned x:6;
    unsigned y:6;
    unsigned xOff:2;
    unsigned yOff:2;
};

_Static_assert(sizeof(struct unitLocation) == sizeof(UWORD), "unit location is not 1 word");

struct unitStats {
    union {
        struct {
            unsigned padding1:8;
            unsigned padding2:7;
            unsigned isBuilding:1;
        };
        struct {
            unsigned unitHp:8;
            unsigned mana:7;
        };
        struct {
            unsigned buildingHp:15;
        };
    };
};

_Static_assert(sizeof(struct unitStats) == sizeof(UWORD), "unit stats is not 1 word");

struct unitHeader {
    unsigned type:6;
    unsigned currentAction:4;
    unsigned frame:6;
    // the frame doesn't really need to be in the header. But the current action
    // is basically always needed, and the type is needed by almost all actions.
    // So there's a little bit of room, and many actions do care about the frame,
    // so it's okay to keep it here.
};

_Static_assert(sizeof(struct unitHeader) == sizeof(UWORD), "unit header is not 1 word");

struct unit {
    struct unitHeader header;
    UWORD actionData;
    struct unitLocation location;
    struct unitStats stats;
};

#define UNIT_SIZE_SHIFT 6
_Static_assert(sizeof(struct unit) == (1 << UNIT_SIZE_SHIFT) >> 3, "unit struct is not 4 words");
_Static_assert(sizeof(struct unit) == 4 * sizeof(UWORD), "unit struct is not 4 words");

#endif
