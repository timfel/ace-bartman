#ifndef ACTIONS_H
#define ACTIONS_H

#include "units.h"
#include "ace/types.h"

typedef void (*action)(struct unit *);

void actionStill(struct unit *);
void actionMove(struct unit *);
void actionAttackMove(struct unit *);
void actionAttackTarget(struct unit *);
void actionHarvest(struct unit *);
void actionCast(struct unit *);
void actionDie(struct unit *);

typedef enum ActionTypes {
    ActionStill,
    ActionMove,
    ActionAttackMove,
    ActionAttackTarget,
    ActionHarvest,
    ActionCast,
    ActionDie
} ActionTypes;

extern action Actions[];

#endif
