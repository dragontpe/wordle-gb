#!/usr/bin/env python3
"""Verify the scorecard actually survives a power cycle.

Plays a game to completion, shuts the emulator down writing battery RAM, then
boots a fresh instance from the same save file and reads the statistics screen
back out of the tilemap. This is the only way to prove SRAM persistence - the
code path looks identical whether or not the cartridge header, RAM enable, or
save wiring are right.
"""
import os
import sys

from pyboy import PyBoy

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROM = os.path.join(ROOT, "build", "wordle.gbc")
# Every emulator names battery RAM differently: PyBoy writes "<rom>.ram", mGBA
# and the Miyoo's gambatte core use "<rom>.sav". Accept whichever appears.
SAV_CANDIDATES = [ROM + ".ram", os.path.splitext(ROM)[0] + ".sav", ROM + ".sav"]


def find_save():
    for p in SAV_CANDIDATES:
        if os.path.exists(p):
            return p
    return None

GRID_X, GRID_Y = 5, 3
FONT_BASE = 108
FONT_ORDER = ([chr(c) for c in range(ord("A"), ord("Z") + 1)] +
              [chr(c) for c in range(ord("0"), ord("9") + 1)] +
              [" ", "!", "-", ":", "%", "/"])

fail = 0


def check(cond, msg):
    global fail
    print(("ok  : " if cond else "FAIL: ") + msg)
    if not cond:
        fail += 1


class Rom:
    def __init__(self):
        self.pb = PyBoy(ROM, window="null", sound_emulated=False)
        self.pb.set_emulation_speed(0)
        self.tm = self.pb.tilemap_background

    def tap(self, button, times=1, hold=3, gap=3):
        for _ in range(times):
            self.pb.button_press(button)
            self.pb.tick(hold)
            self.pb.button_release(button)
            self.pb.tick(gap)

    def tick(self, n):
        self.pb.tick(n)

    def row(self, r):
        out = []
        for c in range(5):
            t = self.tm[GRID_X + c * 2, GRID_Y + r * 2] & 0xFF
            if t == 0:
                out.append(".")
            elif t % 4 == 0 and 1 <= t // 4 <= 26:
                out.append(chr(ord("A") + t // 4 - 1))
            else:
                out.append("?")
        return "".join(out)

    def text(self, x, y, width):
        """Read a run of the font tilemap back as a string."""
        out = []
        for i in range(width):
            t = (self.tm[x + i, y] & 0xFF) - FONT_BASE
            out.append(FONT_ORDER[t] if 0 <= t < len(FONT_ORDER) else "?")
        return "".join(out).strip()

    def type_word(self, word):
        for i, ch in enumerate(word):
            self.tap("up", times=ord(ch) - ord("A") + 1)
            if i < len(word) - 1:
                self.tap("right")

    def clear_row(self):
        # Walk to box 0 first: after a submit the cursor is already there, so
        # pressing Left between clears would leave boxes 1-4 still holding the
        # pre-filled previous guess.
        self.tap("left", times=6)
        for i in range(5):
            self.tap("b")
            if i < 4:
                self.tap("right")
        self.tap("left", times=6)


def answer_address():
    """Look up the `answer` array's WRAM address in the linker's symbol dump."""
    noi = os.path.join(ROOT, "build", "wordle.noi")
    if not os.path.exists(noi):
        return None
    for line in open(noi):
        parts = line.split()
        if len(parts) == 3 and parts[0] == "DEF" and parts[1] == "_answer":
            return int(parts[2], 16)
    return None


def digits(s):
    """Keep only digits: histogram rows interleave bar tiles with the count."""
    return "".join(c for c in s if c.isdigit())


def read_stats(r):
    """Open the stats screen and scrape the numbers.

    Layout mirrors show_stats() in src/main.c: two columns of values at rows 2
    and 4 with labels beneath, then the guess histogram on rows 9-14 where each
    row is "<n> <bar> <count>" and the bar's width shifts the count sideways.
    """
    r.tap("select", hold=6, gap=10)
    r.tick(40)
    vals = {
        "played": digits(r.text(1, 2, 6)),
        "winpct": digits(r.text(11, 2, 6)),    # percentage, not a raw count
        "streak": digits(r.text(1, 4, 6)),
        "max": digits(r.text(11, 4, 6)),
        "dist": [digits(r.text(3, 9 + i, 17)) for i in range(6)],
        "fails": digits(r.text(4, 15, 6)),
    }
    r.tap("b", hold=6, gap=10)
    r.tick(40)
    return vals


def main():
    for p in SAV_CANDIDATES:
        if os.path.exists(p):
            os.remove(p)
            print("removed stale save:", os.path.basename(p))

    # --- session 1: play one game to completion ---------------------------
    r = Rom()
    r.tick(120)
    r.tap("start", hold=6, gap=10)
    r.tick(30)

    before = read_stats(r)
    print("fresh cart stats:", before)
    check(before["played"] == "0", "fresh cart shows 0 played (got %r)" % before["played"])

    # Six real words. If one happens to be the answer the game ends early as a
    # win, which is equally valid for this test - either way one game is played.
    words = ["CRANE", "SLOTH", "PUDGY", "WHIMS", "BLEAK", "FJORD"]
    for i, w in enumerate(words):
        if i > 0:
            r.clear_row()
        r.type_word(w)
        r.tick(5)
        r.tap("a", hold=6, gap=6)
        r.tick(170)

    after = read_stats(r)
    print("after one game :", after)
    check(after["played"] == "1", "one completed game recorded (got %r)" % after["played"])
    check(after["fails"] == "1" or after["winpct"] == "100",
          "game recorded as a win or a loss (win%%=%r fails=%r)"
          % (after["winpct"], after["fails"]))

    r.pb.stop(save=True)

    sav = find_save()
    check(sav is not None, "battery save file was written")
    if sav:
        print("save file:", os.path.basename(sav), os.path.getsize(sav), "bytes")
        # The struct starts with magic 'WD' (0x5744), little-endian on the LR35902.
        head = open(sav, "rb").read(2)
        check(head == b"\x44\x57", "save begins with the WD magic (got %r)" % head)

    # --- session 2: fresh boot, same save ---------------------------------
    r2 = Rom()
    r2.tick(120)
    r2.tap("start", hold=6, gap=10)
    r2.tick(30)
    reloaded = read_stats(r2)
    print("after reboot   :", reloaded)

    check(reloaded["played"] == after["played"],
          "played survived a power cycle (%r -> %r)" % (after["played"], reloaded["played"]))
    check(reloaded["winpct"] == after["winpct"],
          "win %% survived (%r -> %r)" % (after["winpct"], reloaded["winpct"]))
    check(reloaded["max"] == after["max"],
          "max streak survived (%r -> %r)" % (after["max"], reloaded["max"]))
    check(reloaded["dist"] == after["dist"],
          "guess distribution survived (%r -> %r)" % (after["dist"], reloaded["dist"]))
    check(reloaded["fails"] == after["fails"],
          "fail count survived (%r -> %r)" % (after["fails"], reloaded["fails"]))

    r2.pb.stop(save=False)

    # --- session 3: win a game, exercising the paths a loss never touches ---
    # The answer lives in WRAM; reading it lets the test solve in one guess and
    # check wins, streak, and the guess distribution actually update.
    addr = answer_address()
    check(addr is not None, "found the answer symbol in the linker map")
    if addr is None:
        return 1

    r3 = Rom()
    r3.tick(120)
    r3.tap("start", hold=6, gap=10)
    r3.tick(30)

    secret = "".join(chr(ord("A") + r3.pb.memory[addr + i]) for i in range(5))
    print("answer this game:", secret)
    check(all("A" <= c <= "Z" for c in secret), "answer read back as letters (got %r)" % secret)

    r3.type_word(secret)
    r3.tick(5)
    check(r3.row(0) == secret, "typed the answer (got %r)" % r3.row(0))
    r3.tap("a", hold=6, gap=6)
    r3.tick(200)

    won = read_stats(r3)
    print("after a win    :", won)
    # Session 1 lost, session 3 won, and the save carried over: 1 of 2 = 50%.
    check(won["played"] == "2", "played now 2 (got %r)" % won["played"])
    check(won["winpct"] == "50", "win %% is 50 after one win of two (got %r)" % won["winpct"])
    check(won["streak"] == "1", "streak incremented (got %r)" % won["streak"])
    check(won["max"] == "1", "max streak updated (got %r)" % won["max"])
    check(won["dist"][0] == "1",
          "solve counted in the 1-guess bucket (got %r)" % won["dist"])
    check(won["fails"] == "1", "earlier loss still counted (got %r)" % won["fails"])
    r3.pb.stop(save=False)

    if fail:
        print("\n%d CHECK(S) FAILED" % fail)
        return 1
    print("\nall save checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
