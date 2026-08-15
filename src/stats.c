#include <gbdk/platform.h>
#include <stdint.h>

#include "stats.h"

// Battery-backed cartridge RAM. The magic word distinguishes a real save from
// whatever garbage a fresh cart (or emulator .sav) starts life with.
#define SRAM_MAGIC 0x5744  // 'WD'

static Stats *const sram = (Stats *)0xA000;

void stats_load(Stats *out) {
    ENABLE_RAM;
    if (sram->magic != SRAM_MAGIC) {
        for (uint8_t i = 0; i < MAX_GUESSES; i++) out->dist[i] = 0;
        out->magic = SRAM_MAGIC;
        out->played = 0;
        out->wins = 0;
        out->fails = 0;
        out->streak = 0;
        out->max_streak = 0;
        *sram = *out;
    } else {
        *out = *sram;
    }
    DISABLE_RAM;
}

void stats_save(const Stats *in) {
    ENABLE_RAM;
    *sram = *in;
    DISABLE_RAM;
}

void stats_record(Stats *s, uint8_t won, uint8_t guesses_used) {
    if (s->played < 65535U) s->played++;
    if (won) {
        if (s->wins < 65535U) s->wins++;
        if (guesses_used >= 1 && guesses_used <= MAX_GUESSES) {
            if (s->dist[guesses_used - 1] < 65535U) s->dist[guesses_used - 1]++;
        }
        if (s->streak < 65535U) s->streak++;
        if (s->streak > s->max_streak) s->max_streak = s->streak;
    } else {
        if (s->fails < 65535U) s->fails++;
        s->streak = 0;
    }
    stats_save(s);
}
