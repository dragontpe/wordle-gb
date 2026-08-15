#ifndef WORDS_H
#define WORDS_H

#include <stdint.h>

#define WORD_LEN 5
#define MAX_GUESSES 6

// Letters are stored as 0-25 throughout; 26 means "empty box".
#define LETTER_EMPTY 26

uint32_t word_pack(const uint8_t *letters);
void word_unpack(uint32_t n, uint8_t *out);
uint8_t word_is_valid(uint32_t packed);
uint32_t word_answer(uint16_t index);

#endif
