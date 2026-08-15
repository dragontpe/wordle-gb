#!/usr/bin/env python3
"""Verify the title music actually plays, and stops when the game starts.

Measures PyBoy's emulated audio output rather than the APU registers: several
Game Boy sound registers are write-only and read back as 0xFF, so inspecting
them proves nothing about whether a note is sounding.
"""
import os
import sys

import numpy as np
from pyboy import PyBoy

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROM = os.path.join(ROOT, "build", "wordle.gbc")

fail = 0


def check(cond, msg):
    global fail
    print(("ok  : " if cond else "FAIL: ") + msg)
    if not cond:
        fail += 1


def measure(pb, frames):
    """Peak deviation from the DC level, averaged per frame."""
    amps = []
    for _ in range(frames):
        pb.tick(1)
        a = np.array(pb.sound.ndarray, copy=True).astype(np.int32)
        if a.size:
            amps.append(float(np.abs(a - a.mean()).max()))
    return np.array(amps) if amps else np.zeros(1)


def main():
    if not os.path.exists(ROM):
        print("ROM not found:", ROM)
        return 1

    pb = PyBoy(ROM, window="null", sound_emulated=True)
    pb.set_emulation_speed(0)

    pb.tick(200)
    title = measure(pb, 240)
    print("title  peak=%.0f mean=%.1f loud frames=%d/%d"
          % (title.max(), title.mean(), (title > 2).sum(), len(title)))
    check(title.max() > 5, "title screen produces audio (peak %.0f)" % title.max())
    check((title > 2).sum() > len(title) * 0.5,
          "title audio is sustained, not a single blip")

    # The tune must vary: a stuck tone would also register as "audio".
    check(len(set(title.round().astype(int))) > 3,
          "title audio varies over time (%d distinct levels)"
          % len(set(title.round().astype(int))))

    pb.button_press("start")
    pb.tick(6)
    pb.button_release("start")
    pb.tick(90)

    game = measure(pb, 180)
    print("ingame peak=%.0f mean=%.1f loud frames=%d/%d"
          % (game.max(), game.mean(), (game > 2).sum(), len(game)))
    check(game.max() <= 2,
          "board is silent after leaving the title (peak %.0f)" % game.max())

    pb.stop(save=False)

    if fail:
        print("\n%d CHECK(S) FAILED" % fail)
        return 1
    print("\nall audio checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
