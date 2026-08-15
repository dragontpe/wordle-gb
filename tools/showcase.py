#!/usr/bin/env python3
"""Capture a contact sheet of the real ROM with a game actually played.

Unlike preview.py (which mocks screens from tile data), this drives the built
ROM so the images are exactly what the hardware produces, with real statistics
built up over several games.
"""
import os
import sys

from PIL import Image
from pyboy import PyBoy

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROM = os.path.join(ROOT, "build", "wordle.gbc")
OUT = os.path.join(ROOT, "build", "showcase.png")
SAV = ROM + ".ram"

shots = []


def answer_address():
    for line in open(os.path.join(ROOT, "build", "wordle.noi")):
        p = line.split()
        if len(p) == 3 and p[0] == "DEF" and p[1] == "_answer":
            return int(p[2], 16)
    return None


class Rom:
    def __init__(self):
        self.pb = PyBoy(ROM, window="null", sound_emulated=False)
        self.pb.set_emulation_speed(0)

    def tap(self, b, times=1, hold=3, gap=3):
        for _ in range(times):
            self.pb.button_press(b)
            self.pb.tick(hold)
            self.pb.button_release(b)
            self.pb.tick(gap)

    def tick(self, n):
        self.pb.tick(n)

    def grab(self, label):
        shots.append((label, self.pb.screen.image.convert("RGB")))

    def type_word(self, w):
        for i, ch in enumerate(w):
            self.tap("up", times=ord(ch) - ord("A") + 1)
            if i < len(w) - 1:
                self.tap("right")

    def clear_row(self):
        self.tap("left", times=6)
        for i in range(5):
            self.tap("b")
            if i < 4:
                self.tap("right")
        self.tap("left", times=6)


def play_game(r, addr, guesses_before_win):
    """Play a game, deliberately burning N guesses before solving."""
    secret = "".join(chr(ord("A") + r.pb.memory[addr + i]) for i in range(5))
    filler = ["CRANE", "SLOTH", "PUDGY", "WHIMS", "BLEAK"]
    for i in range(guesses_before_win):
        w = filler[i % len(filler)]
        if w == secret:
            w = filler[(i + 1) % len(filler)]
        if i > 0 or True:
            r.clear_row()
        r.type_word(w)
        r.tap("a", hold=6, gap=6)
        r.tick(170)
    r.clear_row()
    r.type_word(secret)
    r.tap("a", hold=6, gap=6)
    r.tick(200)
    return secret


def main():
    if os.path.exists(SAV):
        os.remove(SAV)

    addr = answer_address()
    if addr is None:
        print("could not find _answer in the linker map")
        return 1

    # Build up a save with a few games so the histogram has a shape.
    for n in (2, 3, 3, 4, 1):
        r = Rom()
        r.tick(120)
        r.tap("start", hold=6, gap=10)
        r.tick(30)
        play_game(r, addr, n)
        r.pb.stop(save=True)

    # Final session: capture every screen.
    r = Rom()
    r.tick(120)
    r.grab("title")
    r.tap("start", hold=6, gap=10)
    r.tick(30)

    addr_secret = "".join(chr(ord("A") + r.pb.memory[addr + i]) for i in range(5))
    r.clear_row()
    r.type_word("CRANE")
    r.tap("a", hold=6, gap=6)
    r.tick(170)
    r.clear_row()
    r.type_word("SLOTH")
    r.tap("a", hold=6, gap=6)
    r.tick(170)
    r.clear_row()
    r.type_word("PU")
    r.tick(10)
    r.grab("mid game")

    r.clear_row()
    r.type_word(addr_secret)
    r.tap("a", hold=6, gap=6)
    r.tick(220)
    r.grab("solved")

    r.tap("select", hold=6, gap=10)
    r.tick(40)
    r.grab("stats")
    r.pb.stop(save=False)

    scale, pad = 3, 10
    w, h = 160 * scale, 144 * scale
    sheet = Image.new("RGB", (len(shots) * (w + pad) + pad, h + pad * 2), (10, 10, 11))
    for i, (_, img) in enumerate(shots):
        sheet.paste(img.resize((w, h), Image.NEAREST), (pad + i * (w + pad), pad))
    sheet.save(OUT)
    print("wrote", OUT, "-", ", ".join(l for l, _ in shots))
    print("answer was", addr_secret)
    return 0


if __name__ == "__main__":
    sys.exit(main())
