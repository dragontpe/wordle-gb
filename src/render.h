#ifndef RENDER_H
#define RENDER_H

#include <stdint.h>

// Background palette slots. The CGB allows eight and all eight are used.
#define PAL_EMPTY  0   // box not yet filled: dim outline
#define PAL_FILLED 1   // letter typed but not submitted: brighter outline
#define PAL_CURSOR 2   // the box the dial is on: white outline
#define PAL_GREEN  3
#define PAL_YELLOW 4
#define PAL_ABSENT 5
#define PAL_TEXT   6   // white text on the dark ground
#define PAL_DIM    7   // secondary text and inactive histogram bars

// Grid origin in tiles: 5 cells * 2 tiles = 10 wide, centred in a 20 tile screen.
#define GRID_X 5
#define GRID_Y 3

void render_init(void);
void render_clear(void);
void render_set_attr(uint8_t x, uint8_t y, uint8_t w, uint8_t h, uint8_t pal);
void render_cell(uint8_t col, uint8_t row, uint8_t letter, uint8_t pal);
void render_text(uint8_t x, uint8_t y, const char *s, uint8_t pal);
void render_text_centered(uint8_t y, const char *s, uint8_t pal);
void render_text_clear(uint8_t x, uint8_t y, uint8_t width);
void render_bar(uint8_t x, uint8_t y, uint8_t width, uint8_t pal);
void render_wordmark(uint8_t x, uint8_t y);
void render_shake(void);

#endif
