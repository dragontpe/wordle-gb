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
        case '@': return 43;   // (c) copyright mark
        default:  return 36;   // space
    }
}

// Newsprint theme: the same keycap construction that made the board readable,
// re-grounded on warm paper with near-black ink - Wordle is a newspaper
// puzzle, and the page is an identity the wordyl family doesn't own. Tile
// pixel values: 0 = paper, 1 = key face, 2 = drop shadow, 3 = ink.
#define C_SKY     RGB8(240,237,228)   /* the paper - soft, barely warm */
#define C_FACE    RGB8(255,255,255)
#define C_SHADOW  RGB8(176,170,156)   /* soft print shadow */
#define C_INK     RGB8( 26, 24, 20)   /* warm near-black */
#define C_CURSOR  RGB8(255,238,170)
#define C_GREEN   RGB8( 72,160, 82)
#define C_GRNSH   RGB8( 38, 96, 52)
#define C_ORANGE  RGB8(238,152, 52)
#define C_ORGSH   RGB8(158, 92, 26)
#define C_GREYKEY RGB8(120,116,108)   /* absent key - dark, NYT-style */
#define C_GREYSH  RGB8( 82, 79, 72)
#define C_GREYINK RGB8(110,106, 96)
#define C_DIMBAR  RGB8(192,186,172)
#define C_DIMINK  RGB8(126,120,106)
#define C_WHITE   RGB8(255,255,255)

static const palette_color_t pal_empty[4]  = { C_SKY, C_FACE,    C_SHADOW, C_INK };
static const palette_color_t pal_filled[4] = { C_SKY, C_FACE,    C_SHADOW, C_INK };
static const palette_color_t pal_cursor[4] = { C_SKY, C_CURSOR,  C_SHADOW, C_INK };
static const palette_color_t pal_green[4]  = { C_SKY, C_GREEN,   C_GRNSH,  C_WHITE };
static const palette_color_t pal_yellow[4] = { C_SKY, C_ORANGE,  C_ORGSH,  C_INK };
static const palette_color_t pal_absent[4] = { C_SKY, C_GREYKEY, C_GREYSH, C_WHITE };
static const palette_color_t pal_text[4]   = { C_SKY, C_SKY,     C_INK,    C_INK };
static const palette_color_t pal_dim[4]    = { C_SKY, C_DIMBAR,  C_DIMINK, C_DIMINK };

// The title's rainbow logo hijacks four palette slots the title never draws
// with (filled, cursor, dim, absent). Letter colours are picked so every
// adjacent pair of letters fits one palette: red-yellow, green-yellow,
// green-blue, red-blue - six letters, four hues, one palette per boundary.
#define C_LRED    RGB8(224, 60, 48)
#define C_LYELLOW RGB8(244,180, 38)
#define C_LGREEN  RGB8( 72,160, 82)
#define C_LBLUE   RGB8( 62,118,214)

static const palette_color_t logo_pals[16] = {
    C_SKY, C_LRED,   C_LYELLOW, C_INK,
    C_SKY, C_LGREEN, C_LYELLOW, C_INK,
    C_SKY, C_LGREEN, C_LBLUE,   C_INK,
    C_SKY, C_LRED,   C_LBLUE,   C_INK
};
static const uint8_t logo_slots[4] = { PAL_FILLED, PAL_CURSOR, PAL_DIM, PAL_ABSENT };

void render_title_palettes(void) {
    for (uint8_t i = 0; i < 4; i++)
        set_bkg_palette(logo_slots[i], 1, &logo_pals[i * 4]);
}

void render_game_palettes(void) {
    set_bkg_palette(PAL_FILLED, 1, pal_filled);
    set_bkg_palette(PAL_CURSOR, 1, pal_cursor);
    set_bkg_palette(PAL_DIM,    1, pal_dim);
    set_bkg_palette(PAL_ABSENT, 1, pal_absent);
}

// The pre-baked mini-font copyright strip, one row, text palette.
void render_credit(uint8_t x, uint8_t y) {
    uint8_t row[CREDIT_W];
    for (uint8_t i = 0; i < CREDIT_W; i++)
        row[i] = (uint8_t)(CREDIT_TILE_BASE + credit_map[i]);
    set_bkg_tiles(x, y, CREDIT_W, 1, row);
    render_set_attr(x, y, CREDIT_W, 1, PAL_TEXT);
}

void render_logo2(uint8_t x, uint8_t y) {
    for (uint8_t ty = 0; ty < LOGO2_H; ty++) {
        uint8_t row[LOGO2_W];
        for (uint8_t i = 0; i < LOGO2_W; i++)
            row[i] = (uint8_t)(LOGO2_TILE_BASE + logo2_map[ty * LOGO2_W + i]);
        set_bkg_tiles(x, (uint8_t)(y + ty), LOGO2_W, 1, row);
        VBK_REG = 1;
        for (uint8_t i = 0; i < LOGO2_W; i++)
            row[i] = logo_slots[logo2_attr[ty * LOGO2_W + i]];
        set_bkg_tiles(x, (uint8_t)(y + ty), LOGO2_W, 1, row);
        VBK_REG = 0;
    }
}

void render_init(void) {
    set_bkg_data(CELL_TILE_BASE, CELL_TILE_COUNT, cell_tiles);
    set_bkg_data(FONT_TILE_BASE, FONT_TILE_COUNT, font_tiles);
    set_bkg_data(UTIL_TILE_BASE, UTIL_TILE_COUNT, util_tiles);
    set_bkg_data(LOGO_TILE_BASE, LOGO_TILE_COUNT, logo_tiles);
    set_bkg_data(LOGO2_TILE_BASE, LOGO2_TILE_COUNT, logo2_tiles);
    set_bkg_data(CREDIT_TILE_BASE, CREDIT_TILE_COUNT, credit_tiles);

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

// Print flecks in the margins - dots and the odd diamond, like ink specks on
// newsprint. No stars: sparkles are wordyl's signature, specks are the page's.
static const uint8_t sparkles[][3] = {
    { 1,  1, TILE_DOT },     { 17,  2, TILE_DOT },   { 3,  5, TILE_DOT },
    { 18,  6, TILE_DOT },    { 1,  9, TILE_DIAMOND },{ 17, 10, TILE_DOT },
    { 2, 13, TILE_DOT },     { 18, 14, TILE_DOT },   { 4, 16, TILE_DIAMOND },
    { 15, 17, TILE_DOT },
};

void render_clear(void) {
    uint8_t row[20];
    for (uint8_t i = 0; i < 20; i++) row[i] = FONT_TILE_BASE + font_index(' ');
    for (uint8_t y = 0; y < 18; y++) {
        set_bkg_tiles(0, y, 20, 1, row);
        render_set_attr(0, y, 20, 1, PAL_TEXT);
    }
    for (uint8_t i = 0; i < sizeof(sparkles) / 3; i++) {
        set_bkg_tile_xy(sparkles[i][0], sparkles[i][1], sparkles[i][2]);
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

// The drawn WORDLE logo: two rows of consecutive tiles, sliced row-major by
// gen_tiles.py. PAL_EMPTY supplies dark ink over a soft shadow on the sky.
void render_logo(uint8_t x, uint8_t y) {
    // White sticker letters with one scored letter of each colour in the
    // middle - the logo itself introduces the game's colour language.
    static const uint8_t letter_pal[6] = {
        PAL_EMPTY, PAL_EMPTY, PAL_YELLOW, PAL_ABSENT, PAL_EMPTY, PAL_EMPTY
    };
    uint8_t row[LOGO_TILES_W];
    for (uint8_t r = 0; r < 2; r++) {
        for (uint8_t i = 0; i < LOGO_TILES_W; i++)
            row[i] = (uint8_t)(LOGO_TILE_BASE + r * LOGO_TILES_W + i);
        set_bkg_tiles(x, (uint8_t)(y + r), LOGO_TILES_W, 1, row);
    }
    for (uint8_t i = 0; i < 6; i++)
        render_set_attr((uint8_t)(x + i * 2), y, 2, 2, letter_pal[i]);
}

// A keycap anywhere on screen, for the title's scattered decoration.
void render_key(uint8_t x, uint8_t y, uint8_t letter, uint8_t pal) {
    draw_cell_tiles(x, y, letter, pal);
}

// The title spells WORDLE in the same tiles the board uses, letters bouncing
// on alternate rows the way wordyl staggers its tiles, two of them already
// scored so the screen teaches the colour language before the first guess.
void render_wordmark(uint8_t x, uint8_t y) {
    static const char word[6] = { 'W', 'O', 'R', 'D', 'L', 'E' };
    static const uint8_t pals[6] = {
        PAL_GREEN, PAL_EMPTY, PAL_YELLOW, PAL_EMPTY, PAL_EMPTY, PAL_GREEN
    };
    // Three tiles of pitch, not two: staggered keys jammed edge to edge read
    // as one broken mosaic. The bounce only works with air between the keys.
    for (uint8_t i = 0; i < 6; i++) {
        draw_cell_tiles((uint8_t)(x + i * 3), (uint8_t)(y + (i & 1)),
                        (uint8_t)(word[i] - 'A'), pals[i]);
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
