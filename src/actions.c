#include "actions.h"

action Actions[] = {
    actionStill,
    actionMove,
    actionAttackMove,
    actionAttackTarget,
    actionHarvest,
    actionCast,
    actionDie
};

void actionStill(struct unit  __attribute__((__unused__)) *unit) {
    return;
};

#define moveTargetXMask 0b1111110000000000
#define moveTargetYMask 0b0000001111110000
#define moveCounterMask 0b0000000000001111
#define moveTargetXShift 10
#define moveTargetYShift 4
#define moveCounterShift 0
void actionMove(struct unit *unit) {
    UWORD data = unit->actionData;
    UBYTE counter = (data & moveCounterMask) >> moveCounterShift;

    struct unitHeader hdr = unit->header;
    struct unitType type = UnitTypes[hdr.type];

    // not moving in this step
    if (counter > type.speed) {
        counter -= type.speed;
        return;
    }

    // reset counter
    counter = moveCounterMask;

    // set next movement frame
    // if (hdr.frame == type.stillFrame) {
    //     hdr.frame = type.moveFrame;
    // } else {
    //     hdr.frame = type.stillFrame;
    // }

    // calculate next position
    UBYTE targetX = (data & moveTargetXMask) >> moveTargetXShift;
    UBYTE targetY = (data & moveTargetYMask) >> moveTargetYShift;
    struct unitLocation loc = unit->location;
    UBYTE currentX = loc.x;
    UBYTE currentY = loc.y;
    if (currentX == targetX && currentY == targetY) {
        hdr.currentAction = ActionStill;
    }
    BYTE dirX = targetX - currentX;
    BYTE dirY = targetY - currentY;
};

void actionAttackMove(struct unit  __attribute__((__unused__)) *unit) {
    return;
};

void actionAttackTarget(struct unit  __attribute__((__unused__)) *unit) {
    return;
};

void actionHarvest(struct unit  __attribute__((__unused__)) *unit) {
    return;
};

void actionCast(struct unit  __attribute__((__unused__)) *unit) {
    return;
};

void actionDie(struct unit  __attribute__((__unused__)) *unit) {
    return;
};
