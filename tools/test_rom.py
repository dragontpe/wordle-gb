#!/usr/bin/env python3
"""Boot the built ROM headlessly and play it, asserting on real emulator state.

This is end-to-end verification: it drives the d-pad exactly as a player would
and then reads the hardware's own background tilemap back to confirm which
letters are on the board, plus the framebuffer to confirm the scoring colours.
Anything that only shows up when the thing actually runs - tile or attribute
corruption, palette mistakes, input handling, redraw ordering - surfaces here
instead of on the Miyoo.
"""
import os
import sys

from PIL import Image
from pyboy import PyBoy

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROM = os.path.join(ROOT, "build", "wordle.gbc")
OUT = os.path.join(ROOT, "build", "rom_test.png")

GRID_X, GRID_Y = 5, 3
EMPTY_CELL = 0

fail = 0
shots = []


def check(cond, msg):
    global fail
    print(("ok  : " if cond else "FAIL: ") + msg)
    if not cond:
        fail += 1


def q(c):
    """CGB palettes are 5 bits per channel, so RGB8() values come back quantised."""
    return tuple((v >> 3) << 3 for v in c)


# Dark theme, matching the RGB8() constants in src/render.c.
# Daytime keycap theme (see render.c). An unscored cell's fill is the white
# key face, or the cursor tint on the cell the dial is sitting on.
FACE = q((255, 255, 255))
CURSOR = q((255, 238, 170))
UNSCORED = {FACE, CURSOR}
NYT_GREEN = q((72, 160, 82))
NYT_YELLOW = q((238, 152, 52))
NYT_ABSENT = q((120, 116, 108))
SCORED_FILLS = {NYT_GREEN, NYT_YELLOW, NYT_ABSENT}


class Rom:
    def __init__(self):
        self.pb = PyBoy(ROM, window="null", sound_emulated=False)
        self.pb.set_emulation_speed(0)
        self.tm = self.pb.tilemap_background

    def tick(self, n):
        self.pb.tick(n)

    def tap(self, button, times=1, hold=3, gap=3):
        for _ in range(times):
            self.pb.button_press(button)
            self.pb.tick(hold)
            self.pb.button_release(button)
            self.pb.tick(gap)

    def row(self, r):
        """Read a guess row back out of the background tilemap as text."""
        out = []
        for c in range(5):
            t = self.tm[GRID_X + c * 2, GRID_Y + r * 2]
            t &= 0xFF          # PyBoy reports an addressing-mode offset
            if t == EMPTY_CELL:
                out.append(".")
            elif t % 4 == 0 and 1 <= t // 4 <= 26:
                out.append(chr(ord("A") + t // 4 - 1))
            else:
                out.append("?")
        return "".join(out)

    def type_word(self, word):
        """Each box dials up from blank, so letter N takes N+1 taps."""
        for i, ch in enumerate(word):
            self.tap("up", times=ord(ch) - ord("A") + 1)
            if i < len(word) - 1:
                self.tap("right")

    def clear_row(self):
        # Walk to box 0 first; the cursor's position depends on how the row was
        # reached, and clearing while moving Left only works from box 4.
        self.tap("left", times=6)
        for i in range(5):
            self.tap("b")
            if i < 4:
                self.tap("right")
        self.tap("left", times=6)

    def colors(self):
        img = self.pb.screen.image.convert("RGB")
        return {c for _, c in img.getcolors(70000)}

    def fills(self, r):
        """Sample each cell's interior fill colour on a guess row.

        In the dark theme an absent tile is the same colour as an empty tile's
        border, so presence-of-colour tests cannot distinguish them. The fill
        pixel can: it is the background until a row is scored. (1,1) inside the
        16x16 cell is inside the border and clear of the glyph, which starts at
        x=3.
        """
        img = self.pb.screen.image.convert("RGB")
        out = []
        for c in range(5):
            x = (GRID_X + c * 2) * 8 + 1
            y = (GRID_Y + r * 2) * 8 + 1
            out.append(img.getpixel((x, y)))
        return out

    def grab(self, label):
        shots.append((label, self.pb.screen.image.convert("RGB")))


def main():
    if not os.path.exists(ROM):
        print("ROM not found:", ROM)
        return 1

    r = Rom()
    r.tick(120)
    r.grab("title")
    check(len(r.colors()) > 1, "title screen renders something")

    r.tap("start", hold=6, gap=10)
    r.tick(30)
    r.grab("empty board")
    check(r.row(0) == ".....", "board starts empty (got %r)" % r.row(0))
    check(all(f in UNSCORED for f in r.fills(0)),
          "empty board cells are unfilled (got %r)" % r.fills(0))
    # With a 5-colour palette the scoring colours also serve as text and
    # cursor colours, so whole-screen colour checks prove nothing; the
    # per-cell fill checks above and below carry the invariant instead.

    # --- a non-word must be rejected without consuming a guess --------------
    r.type_word("ZZZZZ")
    r.tick(10)
    check(r.row(0) == "ZZZZZ", "dial entered ZZZZZ (got %r)" % r.row(0))
    r.grab("ZZZZZ entered")
    r.tap("a", hold=6, gap=6)
    r.tick(100)
    r.grab("ZZZZZ rejected")
    check(r.row(1) == ".....", "rejected word did not advance to row 1")
    check(all(f in UNSCORED for f in r.fills(0)),
          "rejected non-word leaves cells unscored (got %r)" % r.fills(0))

    # --- a real word must be accepted and scored ---------------------------
    r.clear_row()
    check(r.row(0) == ".....", "B clears the row (got %r)" % r.row(0))
    r.type_word("CRANE")
    r.tick(10)
    check(r.row(0) == "CRANE", "dial entered CRANE (got %r)" % r.row(0))
    r.grab("CRANE entered")

    r.tap("a", hold=6, gap=6)
    r.tick(160)
    r.grab("CRANE scored")
    check(r.row(0) == "CRANE", "scored row still shows the guess")
    check(r.row(1) == ".....",
          "next row starts blank, as in the NYT game (got %r)" % r.row(1))

    fills = r.fills(0)
    check(all(f not in UNSCORED for f in fills),
          "every scored cell is filled (got %r)" % fills)
    check(all(f in SCORED_FILLS for f in fills),
          "every scored cell uses a scoring colour (got %r)" % fills)
    check(all(f in UNSCORED for f in r.fills(1)),
          "the next row is not scored yet (got %r)" % r.fills(1))

    # --- stats screen ------------------------------------------------------
    r.tap("select", hold=6, gap=10)
    r.tick(40)
    r.grab("stats")
    check(len(r.colors()) > 1, "stats screen renders")

    r.pb.stop(save=False)

    # --- contact sheet -----------------------------------------------------
    scale, pad = 2, 8
    w, h = 160 * scale, 144 * scale
    sheet = Image.new("RGB", (len(shots) * (w + pad) + pad, h + pad * 2), (32, 32, 34))
    for i, (_, img) in enumerate(shots):
        sheet.paste(img.resize((w, h), Image.NEAREST), (pad + i * (w + pad), pad))
    sheet.save(OUT)
    print("\nwrote %s (%s)" % (OUT, ", ".join(l for l, _ in shots)))

    if fail:
        print("%d CHECK(S) FAILED" % fail)
        return 1
    print("all ROM checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
