#include <gbdk/platform.h>
#include <stdint.h>

#include "wordlist.h"
#include "words.h"

// The valid-guess list is sorted and split across consecutive ROM banks, so a
// word index maps to (bank, offset) arithmetically. Every read switches the
// bank, which is cheap enough that a 14-probe binary search is not worth
// optimising further.
static const uint8_t *bank_base(uint8_t chunk) {
    switch (chunk) {
        case 0: SWITCH_ROM(BANK(valid_words_0)); return valid_words_0;
        case 1: SWITCH_ROM(BANK(valid_words_1)); return valid_words_1;
        default: SWITCH_ROM(BANK(valid_words_2)); return valid_words_2;
    }
}

static uint32_t read_packed(const uint8_t *p) {
    return ((uint32_t)p[0] << 16) | ((uint32_t)p[1] << 8) | (uint32_t)p[2];
}

uint32_t word_pack(const uint8_t *letters) {
    uint32_t n = 0;
    for (uint8_t i = 0; i < WORD_LEN; i++) {
        n = n * 26UL + letters[i];
    }
    return n;
}

void word_unpack(uint32_t n, uint8_t *out) {
    for (int8_t i = WORD_LEN - 1; i >= 0; i--) {
        out[i] = (uint8_t)(n % 26UL);
        n /= 26UL;
    }
}

uint8_t word_is_valid(uint32_t packed) {
    uint16_t lo = 0;
    uint16_t hi = VALID_WORD_COUNT - 1;
    while (lo <= hi) {
        uint16_t mid = lo + ((hi - lo) >> 1);
        const uint8_t *base = bank_base((uint8_t)(mid / WORDS_PER_BANK));
        uint32_t v = read_packed(base + (uint16_t)(mid % WORDS_PER_BANK) * 3);
        if (v == packed) return 1;
        if (v < packed) {
            lo = mid + 1;
        } else {
            if (mid == 0) break;   // unsigned underflow guard
            hi = mid - 1;
        }
    }
    return 0;
}

uint32_t word_answer(uint16_t index) {
    SWITCH_ROM(BANK(answer_words));
    return read_packed(answer_words + index * 3);
}
