#include <gb/gb.h>
#include <stdint.h>

#include "sfx.h"

// Pulse channel 2 for pitched blips (no sweep unit to configure), noise
// channel 4 for thuds and buzzes, pulse channel 1 only for the endgame
// sweeps, which are what its sweep unit is for. Every effect is trigger +
// envelope decay; nothing needs servicing afterwards.

// Mirrors the ST_ values in main.c; sfx.h takes the raw state byte so the
// caller does not need a shared header for two constants. If the ST_ order
// ever changes in main.c, change it here too.
#define ST_GREEN  1
#define ST_YELLOW 2

// Square blip on channel 2. freq is the 11-bit period value.
static void blip(uint16_t freq, uint8_t env) {
    NR21_REG = 0x80;                            // 50% duty
    NR22_REG = env;
    NR23_REG = (uint8_t)(freq & 0xFF);
    NR24_REG = (uint8_t)(0x80 | (freq >> 8));   // trigger
}

void sfx_tick(void) {
    blip(1900, 0x51);      // ~890 Hz, quiet and very short: a dial detent
}

void sfx_move(void) {
    blip(1750, 0x51);      // lower thock for sideways movement
}

void sfx_reveal(uint8_t st) {
    if (st == ST_GREEN) {
        blip(1949, 0xA2);  // ~1.3 kHz ding, longer ring
    } else if (st == ST_YELLOW) {
        blip(1849, 0x82);  // lower, shorter
    } else {
        // Absent: a soft noise tap rather than a tone.
        NR41_REG = 0x00;
        NR42_REG = 0x51;
        NR43_REG = 0x44;
        NR44_REG = 0x80;
    }
}

void sfx_bad(void) {
    // A low buzz alongside the row shake.
    NR41_REG = 0x00;
    NR42_REG = 0xA2;
    NR43_REG = 0x62;
    NR44_REG = 0x80;
}

void sfx_win(void) {
    // Channel 1 sweeping upward: a little rising zip.
    NR10_REG = 0x27;       // period 2, add mode, shift 7
    NR11_REG = 0x80;
    NR12_REG = 0xA3;
    NR13_REG = 0x05;
    NR14_REG = 0x87;       // trigger, freq 0x705 (~C5)
}

void sfx_lose(void) {
    // The same zip falling instead.
    NR10_REG = 0x2F;       // period 2, subtract mode, shift 7
    NR11_REG = 0x80;
    NR12_REG = 0x93;
    NR13_REG = 0x39;
    NR14_REG = 0x87;       // trigger, freq 0x739 (~E5)
}
