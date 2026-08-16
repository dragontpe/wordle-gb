#ifndef SFX_H
#define SFX_H

#include <stdint.h>

// Small register-poked sound effects, in the register the game plays in:
// a dry tick for the dial, a thock for moving, per-state chimes as the
// reveal sweeps across a row, a buzz for a rejected word, and a sweep up
// or down for the end of the game. No driver - each effect is a couple of
// APU writes and the envelope does the rest, so they cost nothing per frame
// and cannot fight the title music (which never plays during the game).

void sfx_tick(void);           // dial moved one letter
void sfx_move(void);           // cursor moved a column
void sfx_reveal(uint8_t st);   // one cell revealed; st is the ST_ constant
void sfx_bad(void);            // word rejected (pairs with the shake)
void sfx_win(void);
void sfx_lose(void);

#endif
