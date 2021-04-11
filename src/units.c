#include "units.h"
#include "actions.h"
#include "ace/types.h"
#include "ace/macros.h"
#include "ace/managers/memory.h"

enum UnitTypes {
    dead = 0,
    //
    peasant,
    peon,
    footman,
    grunt,
    archer,
    spearman,
    catapult,
    knight,
    raider,
    cleric,
    necrolyte,
    conjurer,
    warlock
};

struct unitType UnitTypes[] = {
    {.spritesheet = NULL, .maxHP = 0, .mana = 0, .speed = 1}
};

#define MAX_UNITS 200
// with 10 units per frame, we need 20 frames to get through all units
// so on NTSC, we'd handle each unit 3 times per second. This should give
// generally nice animation and speed
#define UNITS_PER_FRAME 10

struct unitManager {
    UBYTE index;
    UBYTE fillLevel;
    struct unit units[MAX_UNITS];
};

void *createUnitManager(void) {
    return memAllocFastClear(sizeof(struct unitManager));
}

void processUnits(void *unitManager) {
    struct unitManager *m = (struct unitManager *)unitManager;
    UBYTE start = m->index;
    UBYTE end = start + UNITS_PER_FRAME;
    for (UBYTE i = start; i < end; ++i) {
        struct unit *unit = &m->units[i];
        Actions[unit->header.currentAction](unit);
    }
}

struct unit *allocateUnit(void *unitManager) {
    struct unitManager *m = (struct unitManager *)unitManager;
    UBYTE i = m->fillLevel;
    if (i < MAX_UNITS) {
        m->fillLevel += 1;
        return m->units + i;
    }
    // fill level is at top, we need to scan
    // TODO: implement bitfield and arenas for faster memory management?
    for (i = 0; i < MAX_UNITS; ++i) {
        struct unit *unit = m->units + i;
        if (unit->header.type == dead) {
            return unit;
        };
    }
    return NULL;
}

void freeUnit(void *unitManager, struct unit *unit) {
    struct unitManager *m = (struct unitManager *)unitManager;
    unit->header.type = dead;
    UBYTE index = ((ULONG)unit - (ULONG)(m->units)) >> UNIT_SIZE_SHIFT;
    if (index == m->fillLevel) {
        m->fillLevel = index;
    }
}
