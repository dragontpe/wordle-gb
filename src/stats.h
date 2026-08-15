#ifndef STATS_H
#define STATS_H

#include <stdint.h>

#include "words.h"

typedef struct {
    uint16_t magic;
    uint16_t played;
    uint16_t wins;
    uint16_t fails;
    uint16_t streak;
    uint16_t max_streak;
    uint16_t dist[MAX_GUESSES];   // solves in 1..6 guesses
} Stats;

void stats_load(Stats *out);
void stats_save(const Stats *in);
void stats_record(Stats *s, uint8_t won, uint8_t guesses_used);

#endif
