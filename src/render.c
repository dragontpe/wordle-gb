#include <gbdk/platform.h>
#include <gb/gb.h>
#include <stdint.h>

#include "render.h"
#include "tiles.h"
#include "words.h"

// Font glyph order must match FONT_ORDER in tools/gen_tiles.py.
uint8_t font_index(char c) {
    if (c >= 'A' && c <= 'Z') return (uint8_t)(c - 'A');
    if (c >= 'a' && c <= 'z') return (uint8_t)(c - 'a');
    if (c >= '0' && c <= '9') return (uint8_t)(26 + (c - '0'));
    switch (c) {
        case '!': return 37;
        case '-': return 38;
        case ':': return 39;
        case '%': return 40;
        case '/': return 41;
        case '.': return 42;
        default:  return 36;   // space
    }
}

// NYT dark theme. Tile pixel values mean 0 = fill, 1 = border, 2 = ink; a
// scored tile sets fill and border to the same colour so it reads as solid,
// while an empty one keeps the border visible as a 1px outline.
#define C_BG      RGB8( 18, 18, 19)
#define C_OUTLINE RGB8( 58, 58, 60)
#define C_BRIGHT  RGB8( 86, 87, 88)
#define C_INK     RGB8(255,255,255)
#define C_DIM     RGB8(129,131,132)
#define C_GREEN   RGB8( 83,141, 78)
#define C_YELLOW  RGB8(181,159, 59)
#define C_ABSENT  RGB8( 58, 58, 60)

static const palette_color_t pal_empty[4]  = { C_BG,     C_OUTLINE, C_INK, C_INK };
static const palette_color_t pal_filled[4] = { C_BG,     C_BRIGHT,  C_INK, C_INK };
static const palette_color_t pal_cursor[4] = { C_BG,     C_INK,     C_INK, C_INK };
static const palette_color_t pal_green[4]  = { C_GREEN,  C_GREEN,   C_INK, C_INK };
static const palette_color_t pal_yellow[4] = { C_YELLOW, C_YELLOW,  C_INK, C_INK };
static const palette_color_t pal_absent[4] = { C_ABSENT, C_ABSENT,  C_INK, C_INK };
static const palette_color_t pal_text[4]   = { C_BG,     C_BG,      C_INK, C_INK };
static const palette_color_t pal_dim[4]    = { C_BG,     C_DIM,     C_DIM, C_DIM };

void render_init(void) {
    set_bkg_data(CELL_TILE_BASE, CELL_TILE_COUNT, cell_tiles);
    set_bkg_data(FONT_TILE_BASE, FONT_TILE_COUNT, font_tiles);
    set_bkg_data(UTIL_TILE_BASE, UTIL_TILE_COUNT, util_tiles);

    set_bkg_palette(PAL_EMPTY,  1, pal_empty);
    set_bkg_palette(PAL_FILLED, 1, pal_filled);
    set_bkg_palette(PAL_CURSOR, 1, pal_cursor);
    set_bkg_palette(PAL_GREEN,  1, pal_green);
    set_bkg_palette(PAL_YELLOW, 1, pal_yellow);
    set_bkg_palette(PAL_ABSENT, 1, pal_absent);
    set_bkg_palette(PAL_TEXT,   1, pal_text);
    set_bkg_palette(PAL_DIM,    1, pal_dim);
}

// The scratch buffer must cover the widest run we ever write, which is a full
// 20-tile screen row. Sizing it any smaller overruns and scribbles garbage
// attributes -- including bit 3, the VRAM tile bank select, which makes tiles
// vanish entirely.
void render_set_attr(uint8_t x, uint8_t y, uint8_t w, uint8_t h, uint8_t pal) {
    uint8_t attr[20];
    if (w > 20) w = 20;
    for (uint8_t i = 0; i < w; i++) attr[i] = pal;
    VBK_REG = 1;
    for (uint8_t row = 0; row < h; row++) {
        set_bkg_tiles(x, y + row, w, 1, attr);
    }
    VBK_REG = 0;
}

void render_clear(void) {
    uint8_t row[20];
    for (uint8_t i = 0; i < 20; i++) row[i] = FONT_TILE_BASE + font_index(' ');
    for (uint8_t y = 0; y < 18; y++) {
        set_bkg_tiles(0, y, 20, 1, row);
        render_set_attr(0, y, 20, 1, PAL_TEXT);
    }
}

// A cell is 2x2 tiles. gen_tiles.py emits them column-major, so reorder to the
// row-major layout set_bkg_tiles expects.
static void draw_cell_tiles(uint8_t x, uint8_t y, uint8_t letter, uint8_t pal) {
    uint8_t base = (letter == LETTER_EMPTY ? 0 : (uint8_t)(letter + 1)) * 4;
    uint8_t map[4];
    map[0] = CELL_TILE_BASE + base + 0;   // (x,   y)
    map[1] = CELL_TILE_BASE + base + 2;   // (x+1, y)
    map[2] = CELL_TILE_BASE + base + 1;   // (x,   y+1)
    map[3] = CELL_TILE_BASE + base + 3;   // (x+1, y+1)
    set_bkg_tiles(x, y, 2, 2, map);
    render_set_attr(x, y, 2, 2, pal);
}

void render_cell(uint8_t col, uint8_t row, uint8_t letter, uint8_t pal) {
    draw_cell_tiles(GRID_X + col * 2, GRID_Y + row * 2, letter, pal);
}

// The title spells WORDLE in the same tiles the board uses, two of them already
// scored, so the screen teaches the colour language before the first guess.
void render_wordmark(uint8_t x, uint8_t y) {
    static const char word[6] = { 'W', 'O', 'R', 'D', 'L', 'E' };
    static const uint8_t pals[6] = {
        PAL_GREEN, PAL_EMPTY, PAL_YELLOW, PAL_EMPTY, PAL_EMPTY, PAL_GREEN
    };
    for (uint8_t i = 0; i < 6; i++) {
        draw_cell_tiles((uint8_t)(x + i * 2), y, (uint8_t)(word[i] - 'A'), pals[i]);
    }
}

void render_text(uint8_t x, uint8_t y, const char *s, uint8_t pal) {
    uint8_t buf[20];
    uint8_t n = 0;
    while (s[n] && n < 20 && (uint8_t)(x + n) < 20) {
        buf[n] = FONT_TILE_BASE + font_index(s[n]);
        n++;
    }
    if (n == 0) return;
    set_bkg_tiles(x, y, n, 1, buf);
    render_set_attr(x, y, n, 1, pal);
}

void render_text_centered(uint8_t y, const char *s, uint8_t pal) {
    uint8_t len = 0;
    while (s[len]) len++;
    if (len > 20) len = 20;
    render_text((uint8_t)((20 - len) / 2), y, s, pal);
}

void render_text_clear(uint8_t x, uint8_t y, uint8_t width) {
    uint8_t buf[20];
    if (width > 20) width = 20;
    for (uint8_t i = 0; i < width; i++) buf[i] = FONT_TILE_BASE + font_index(' ');
    set_bkg_tiles(x, y, width, 1, buf);
    render_set_attr(x, y, width, 1, PAL_TEXT);
}

// Solid run used for the statistics histogram.
void render_bar(uint8_t x, uint8_t y, uint8_t width, uint8_t pal) {
    uint8_t buf[20];
    if (width > 20) width = 20;
    // Explicit cast: tile indices above 127 otherwise trip SDCC's signed-char
    // conversion warning.
    for (uint8_t i = 0; i < width; i++) buf[i] = (uint8_t)TILE_SOLID;
    if (width == 0) return;
    set_bkg_tiles(x, y, width, 1, buf);
    render_set_attr(x, y, width, 1, pal);
}

// Horizontal wobble used to reject an invalid word, mirroring the NYT shake.
void render_shake(void) {
    static const int8_t offsets[] = { -3, 3, -3, 3, -2, 2, -1, 1, 0 };
    for (uint8_t i = 0; i < sizeof(offsets); i++) {
        move_bkg((uint8_t)(offsets[i] & 0xFF), 0);
        for (uint8_t f = 0; f < 3; f++) vsync();
    }
    move_bkg(0, 0);
}
