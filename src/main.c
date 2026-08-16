#include <gbdk/platform.h>
#include <gb/gb.h>
#include <rand.h>
#include <stdint.h>

#include "hUGEDriver.h"
#include "render.h"
#include "stats.h"
#include "sfx.h"
#include "tiles.h"
#include "wordlist.h"
#include "words.h"

// Auto-repeat for the letter dial: 26 letters is a long way to travel one press
// at a time, so hold-to-scroll is load-bearing rather than a nicety.
#define REPEAT_DELAY  18   // frames before a held direction starts repeating
#define REPEAT_RATE    4   // frames between repeats once it does

#define MSG_Y  15
#define HINT_Y 16

static uint8_t grid[MAX_GUESSES][WORD_LEN];
static uint8_t state[MAX_GUESSES][WORD_LEN];
// Deliberately not static: the symbol has to survive into the linker map so
// tools/test_save.py can read the answer out of WRAM and play a winning game.
uint8_t answer[WORD_LEN];
static uint8_t cur_row, cur_col;
static uint8_t game_over, game_won;
static Stats stats;

#define ST_EMPTY  0
#define ST_GREEN  1
#define ST_YELLOW 2
#define ST_ABSENT 3

static const uint8_t state_pal[4] = { PAL_EMPTY, PAL_GREEN, PAL_YELLOW, PAL_ABSENT };

// NYT's praise, indexed by how many guesses it took.
static const char *const win_words[MAX_GUESSES] = {
    "GENIUS", "MAGNIFICENT", "IMPRESSIVE", "SPLENDID", "GREAT", "PHEW"
};

static void num_to_str(uint16_t v, char *out) {
    char tmp[6];
    uint8_t n = 0;
    if (v == 0) { out[0] = '0'; out[1] = 0; return; }
    while (v > 0 && n < 5) { tmp[n++] = (char)('0' + (v % 10)); v /= 10; }
    for (uint8_t i = 0; i < n; i++) out[i] = tmp[n - 1 - i];
    out[n] = 0;
}

static void draw_cell_at(uint8_t row, uint8_t col) {
    uint8_t pal;
    if (!game_over && row == cur_row) {
        // The active row shows its own state: where the dial sits, which boxes
        // are already filled, and which are still waiting.
        if (col == cur_col) {
            pal = PAL_CURSOR;
        } else if (grid[row][col] != LETTER_EMPTY) {
            pal = PAL_FILLED;
        } else {
            pal = PAL_EMPTY;
        }
    } else {
        pal = state_pal[state[row][col]];
    }
    render_cell(col, row, grid[row][col], pal);
}

static void draw_row(uint8_t row) {
    for (uint8_t c = 0; c < WORD_LEN; c++) draw_cell_at(row, c);
}

static void draw_board(void) {
    for (uint8_t r = 0; r < MAX_GUESSES; r++) draw_row(r);
}

static void draw_header(void) {
    char buf[6];
    render_text_clear(0, 0, 20);
    render_text(1, 0, "STREAK", PAL_DIM);
    num_to_str(stats.streak, buf);
    render_text(8, 0, buf, PAL_DIM);

    if (!game_over) {
        num_to_str((uint16_t)(cur_row + 1), buf);
        render_text(16, 0, buf, PAL_DIM);
        render_text(17, 0, "/6", PAL_DIM);
    }
}

static void show_msg(const char *s, uint8_t pal) {
    render_text_clear(0, MSG_Y, 20);
    if (s) render_text_centered(MSG_Y, s, pal);
}

static void show_hint(const char *s) {
    render_text_clear(0, HINT_Y, 20);
    if (s) render_text_centered(HINT_Y, s, PAL_DIM);
}

static void new_game(void) {
    for (uint8_t r = 0; r < MAX_GUESSES; r++) {
        for (uint8_t c = 0; c < WORD_LEN; c++) {
            grid[r][c] = LETTER_EMPTY;
            state[r][c] = ST_EMPTY;
        }
    }
    cur_row = 0;
    cur_col = 0;
    game_over = 0;
    game_won = 0;
    word_unpack(word_answer((uint16_t)(randw() % ANSWER_COUNT)), answer);

    render_clear();
    draw_header();
    draw_board();
    show_msg(0, PAL_TEXT);
    show_hint("A ENTER   SEL STATS");
}

// Standard Wordle marking: greens claim their letter first, then yellows draw
// from whatever occurrences remain, so duplicates score the way players expect.
static void score_row(uint8_t row) {
    uint8_t counts[26];
    for (uint8_t i = 0; i < 26; i++) counts[i] = 0;
    for (uint8_t i = 0; i < WORD_LEN; i++) counts[answer[i]]++;

    for (uint8_t i = 0; i < WORD_LEN; i++) {
        if (grid[row][i] == answer[i]) {
            state[row][i] = ST_GREEN;
            counts[grid[row][i]]--;
        } else {
            state[row][i] = ST_ABSENT;
        }
    }
    for (uint8_t i = 0; i < WORD_LEN; i++) {
        if (state[row][i] == ST_GREEN) continue;
        uint8_t l = grid[row][i];
        if (counts[l] > 0) {
            state[row][i] = ST_YELLOW;
            counts[l]--;
        }
    }
}

static void reveal_row(uint8_t row) {
    // Staggered reveal so the result reads left to right instead of snapping.
    for (uint8_t c = 0; c < WORD_LEN; c++) {
        render_cell(c, row, grid[row][c], state_pal[state[row][c]]);
        sfx_reveal(state[row][c]);
        for (uint8_t f = 0; f < 6; f++) vsync();
    }
}

static void show_stats(void) {
    char buf[6];
    render_clear();
    render_text_centered(0, "STATISTICS", PAL_TEXT);

    // Two columns of big numbers with quiet labels beneath them.
    num_to_str(stats.played, buf);
    render_text(1, 2, buf, PAL_TEXT);
    render_text(1, 3, "PLAYED", PAL_DIM);

    uint16_t pct = 0;
    if (stats.played) pct = (uint16_t)(((uint32_t)stats.wins * 100UL) / stats.played);
    num_to_str(pct, buf);
    render_text(11, 2, buf, PAL_TEXT);
    render_text(11, 3, "WIN %", PAL_DIM);

    num_to_str(stats.streak, buf);
    render_text(1, 4, buf, PAL_TEXT);
    render_text(1, 5, "STREAK", PAL_DIM);

    num_to_str(stats.max_streak, buf);
    render_text(11, 4, buf, PAL_TEXT);
    render_text(11, 5, "MAX", PAL_DIM);

    render_text(1, 7, "GUESSES", PAL_DIM);

    // Bars are scaled to the tallest bucket so the shape stays readable whether
    // you have played ten games or a thousand.
    uint16_t top = 1;
    for (uint8_t i = 0; i < MAX_GUESSES; i++) {
        if (stats.dist[i] > top) top = stats.dist[i];
    }
    for (uint8_t i = 0; i < MAX_GUESSES; i++) {
        uint8_t y = (uint8_t)(9 + i);
        buf[0] = (char)('1' + i);
        buf[1] = 0;
        render_text(1, y, buf, PAL_DIM);

        uint8_t w = 0;
        if (stats.dist[i]) {
            w = (uint8_t)(((uint32_t)stats.dist[i] * 11UL) / top);
            if (w == 0) w = 1;
        }
        if (w) render_bar(3, y, w, PAL_GREEN);
        num_to_str(stats.dist[i], buf);
        render_text((uint8_t)(3 + w + 1), y, buf, PAL_DIM);
    }

    render_text(1, 15, "X", PAL_DIM);
    num_to_str(stats.fails, buf);
    render_text(4, 15, buf, PAL_DIM);

    render_text_centered(17, "B - BACK", PAL_DIM);

    waitpadup();
    while (1) {
        if (joypad() & (J_B | J_START | J_SELECT)) break;
        vsync();
    }
    waitpadup();

    render_clear();
    draw_header();
    draw_board();
    if (game_over) {
        show_msg(game_won ? win_words[cur_row] : "OUT OF GUESSES",
                 game_won ? PAL_TEXT : PAL_DIM);
        show_hint("START - NEW GAME");
    } else {
        show_msg(0, PAL_TEXT);
        show_hint("A ENTER   SEL STATS");
    }
}

static void submit_guess(void) {
    for (uint8_t c = 0; c < WORD_LEN; c++) {
        if (grid[cur_row][c] == LETTER_EMPTY) {
            show_msg("NOT ENOUGH LETTERS", PAL_DIM);
            sfx_bad();
            render_shake();
            return;
        }
    }

    uint32_t packed = word_pack(grid[cur_row]);
    if (!word_is_valid(packed)) {
        show_msg("NOT IN WORD LIST", PAL_DIM);
        sfx_bad();
        render_shake();
        return;
    }

    show_msg(0, PAL_TEXT);
    score_row(cur_row);
    reveal_row(cur_row);

    uint8_t solved = 1;
    for (uint8_t c = 0; c < WORD_LEN; c++) {
        if (state[cur_row][c] != ST_GREEN) { solved = 0; break; }
    }

    if (solved) {
        game_over = 1;
        game_won = 1;
        stats_record(&stats, 1, (uint8_t)(cur_row + 1));
        draw_header();
        show_msg(win_words[cur_row], PAL_TEXT);
        show_hint("START - NEW GAME");
        sfx_win();
        return;
    }

    if (cur_row + 1 >= MAX_GUESSES) {
        game_over = 1;
        game_won = 0;
        stats_record(&stats, 0, 0);
        draw_header();
        // Reveal the answer rather than leaving the player guessing.
        char word[WORD_LEN + 1];
        for (uint8_t c = 0; c < WORD_LEN; c++) word[c] = (char)('A' + answer[c]);
        word[WORD_LEN] = 0;
        show_msg(word, PAL_TEXT);
        show_hint("START - NEW GAME");
        sfx_lose();
        return;
    }

    // The next row starts blank, matching the NYT game. Carrying the previous
    // guess forward would save dialling, but it is not how Wordle behaves.
    // Advance before repainting: draw_cell_at() paints whichever row equals
    // cur_row with the cursor palette, so redrawing the finished row first
    // would wipe the scoring colours that were just revealed.
    uint8_t finished = cur_row;
    cur_row++;
    cur_col = 0;
    draw_row(finished);
    draw_row(cur_row);
    draw_header();
}

// "Seaside Village" by Beatscribe, CC0. See audio/README.md.
extern const hUGESong_t seaside_song;

static void music_start(void) {
    NR52_REG = 0x80;   // sound on
    NR51_REG = 0xFF;   // all channels to both speakers
    NR50_REG = 0x77;   // full volume
    __critical {
        hUGE_init(&seaside_song);
        // Driven from VBlank rather than a timer: VBlank still fires once per
        // real frame in CGB double-speed mode, so cpu_fast() cannot skew tempo.
        add_VBL(hUGE_dosound);
    }
}

static void music_stop(void) {
    __critical {
        remove_VBL(hUGE_dosound);
    }
    // Keep the APU powered for the in-game effects; just silence whatever
    // note the tune left ringing.
    NR12_REG = 0x08; NR14_REG = 0x80;
    NR22_REG = 0x08; NR24_REG = 0x80;
    NR32_REG = 0x00;
    NR42_REG = 0x08; NR44_REG = 0x80;
}

// The colour key done wordyl's way: real scored keycaps with labels, not
// prose, plus this game's own dial controls. Reached from the title with
// SELECT; B returns.
static void help_screen(void) {
    render_clear();
    render_text_centered(0, "HOW TO PLAY", PAL_TEXT);
    render_text_centered(2, "GUESS THE WORD IN 6", PAL_DIM);

    render_key(2, 4, (uint8_t)('A' - 'A'), PAL_GREEN);
    render_text(6, 5, "RIGHT SPOT", PAL_TEXT);
    render_key(2, 7, (uint8_t)('B' - 'A'), PAL_YELLOW);
    render_text(6, 8, "WRONG SPOT", PAL_TEXT);
    render_key(2, 10, (uint8_t)('C' - 'A'), PAL_ABSENT);
    render_text(6, 11, "NOT IN WORD", PAL_TEXT);

    render_text_centered(13, "UP DOWN - LETTER", PAL_DIM);
    render_text_centered(14, "LEFT RIGHT - MOVE", PAL_DIM);
    render_text_centered(15, "A ENTER  SEL STATS", PAL_DIM);
    render_text_centered(17, "B - BACK", PAL_TEXT);

    while (!(joypad() & (J_B | J_START))) vsync();
    waitpadup();
}

static void title_draw(void) {
    render_clear();

    // The big rainbow logo owns the screen the way real GBC titles work, a
    // QWERTY keycap ridge is the ground band, and the copyright lines close
    // the frame. The logo borrows four palette slots the title never draws
    // with; render_game_palettes() gives them back on the way out.
    render_title_palettes();
    render_logo2(3, 1);

    render_text_centered(6, "THE WORD GAME", PAL_TEXT);

    render_text_centered(15, "SELECT: HOW TO PLAY", PAL_TEXT);
    render_text_centered(16, "@2026", PAL_TEXT);
    render_text_centered(17, "WITHOUT BANNERS", PAL_TEXT);
}

// PRESS / START spelled in the game's own keycaps, staggered like the word
// blocks on era title screens. The pair pulses green on the title loop -
// the prompt is the decoration, instead of a text line plus filler tiles.
static void draw_press_start(uint8_t pal) {
    static const char p_word[5] = { 'P', 'R', 'E', 'S', 'S' };
    static const char s_word[5] = { 'S', 'T', 'A', 'R', 'T' };
    for (uint8_t i = 0; i < 5; i++)
        render_key((uint8_t)(2 + i * 2), 8, (uint8_t)(p_word[i] - 'A'), pal);
    for (uint8_t i = 0; i < 5; i++)
        render_key((uint8_t)(8 + i * 2), 11, (uint8_t)(s_word[i] - 'A'), pal);
}

static void title_screen(void) {
    title_draw();

    music_start();

    // Seed from how long the player takes to press a button; DIV keeps counting
    // regardless, so this is effectively unpredictable. The prompt blinks on
    // the same loop, and SELECT detours through the help screen.
    uint16_t seed = 0;
    uint8_t blink = 0;
    for (;;) {
        uint8_t j = joypad();
        if (j & (J_START | J_A)) break;
        if (j & J_SELECT) {
            waitpadup();
            render_game_palettes();   // help uses the slots the logo borrows
            help_screen();
            title_draw();
            blink = 0;
        }
        seed += DIV_REG;
        if ((blink & 31) == 0) {
            draw_press_start((blink & 32) ? PAL_EMPTY : PAL_GREEN);
        }
        blink++;
        vsync();
    }
    initrand(seed ? seed : 1);
    render_game_palettes();
    waitpadup();

    // The board is a quiet screen; the tune belongs to the title only.
    music_stop();
}

void main(void) {
    cpu_fast();          // CGB double speed
    DISPLAY_ON;
    SHOW_BKG;

    render_init();
    stats_load(&stats);
    title_screen();
    new_game();

    uint8_t prev = 0;
    uint8_t hold_frames = 0;
    uint8_t last_dir = 0;

    while (1) {
        uint8_t pad = joypad();
        uint8_t pressed = pad & ~prev;

        if (game_over) {
            if (pressed & J_START) {
                new_game();
            } else if (pressed & J_SELECT) {
                show_stats();
            }
            prev = pad;
            vsync();
            continue;
        }

        // Letter dial with hold-to-repeat.
        uint8_t dir = pad & (J_UP | J_DOWN);
        if (dir && dir == last_dir) {
            hold_frames++;
        } else {
            hold_frames = 0;
            last_dir = dir;
        }

        uint8_t step = 0;
        if (pressed & (J_UP | J_DOWN)) {
            step = 1;
        } else if (dir && hold_frames >= REPEAT_DELAY &&
                   ((hold_frames - REPEAT_DELAY) % REPEAT_RATE) == 0) {
            step = 1;
        }

        if (step) {
            uint8_t l = grid[cur_row][cur_col];
            if (dir & J_UP) {
                l = (l == LETTER_EMPTY) ? 0 : (uint8_t)((l + 1) % 26);
            } else {
                l = (l == LETTER_EMPTY) ? 25 : (uint8_t)((l + 25) % 26);
            }
            grid[cur_row][cur_col] = l;
            draw_cell_at(cur_row, cur_col);
            show_msg(0, PAL_TEXT);
            sfx_tick();
        }

        if (pressed & J_LEFT) {
            if (cur_col > 0) {
                cur_col--;
                draw_row(cur_row);
                sfx_move();
            }
        }
        if (pressed & J_RIGHT) {
            if (cur_col + 1 < WORD_LEN) {
                cur_col++;
                draw_row(cur_row);
                sfx_move();
            }
        }
        if (pressed & J_B) {
            // Clear the current box, a faster escape than dialling to blank.
            grid[cur_row][cur_col] = LETTER_EMPTY;
            draw_cell_at(cur_row, cur_col);
            show_msg(0, PAL_TEXT);
        }
        if (pressed & J_A) {
            submit_guess();
        }
        if (pressed & J_SELECT) {
            show_stats();
        }

        prev = pad;
        vsync();
    }
}
