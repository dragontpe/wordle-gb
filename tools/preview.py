#!/usr/bin/env python3
"""Render mockups of every screen from the real generated tile data.

Decodes the same 2bpp bytes the ROM loads into VRAM and paints them with the
CGB palettes the ROM uses, at true 160x144. If it looks right here it looks
right on hardware.
"""
import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_tiles as G

SCALE = 3
W, H = 160, 144

# NYT dark theme. A light board on a 160x144 screen reads as a terminal; the
# dark ground is what makes the green and yellow tiles feel like game pieces.
BG = (18, 18, 19)
BORDER_EMPTY = (58, 58, 60)
BORDER_FILLED = (86, 87, 88)
INK = (255, 255, 255)
DIM = (129, 131, 132)
GREEN = (83, 141, 78)
YELLOW = (181, 159, 59)
ABSENT = (58, 58, 60)

# palette = [fill, border, ink, accent]
PAL = {
    "empty":  [BG, BORDER_EMPTY, INK, INK],
    "filled": [BG, BORDER_FILLED, INK, INK],
    "cursor": [BG, INK, INK, INK],
    "green":  [GREEN, GREEN, INK, INK],
    "yellow": [YELLOW, YELLOW, INK, INK],
    "absent": [ABSENT, ABSENT, INK, INK],
    "text":   [BG, BG, INK, INK],
    "dim":    [BG, DIM, DIM, DIM],
}

GRID_X, GRID_Y = 5, 3

CELLS, FONTS, UTILS = G.build_all()


def decode(data):
    px = [[0] * 8 for _ in range(8)]
    for y in range(8):
        lo, hi = data[y * 2], data[y * 2 + 1]
        for x in range(8):
            b = 7 - x
            px[y][x] = ((lo >> b) & 1) | (((hi >> b) & 1) << 1)
    return px


def blit(img, tile, tx, ty, pal):
    px = decode(tile)
    for y in range(8):
        for x in range(8):
            img.putpixel((tx * 8 + x, ty * 8 + y), pal[px[y][x]])


def cell(img, ch, tx, ty, pal):
    idx = 0 if ch == " " else 1 + (ord(ch) - ord("A"))
    base = idx * 4
    for t, (dx, dy) in zip(range(4), [(0, 0), (0, 1), (1, 0), (1, 1)]):
        blit(img, CELLS[base + t], tx + dx, ty + dy, PAL[pal])


def text(img, s, tx, ty, pal="text"):
    for i, ch in enumerate(s.upper()):
        if ch not in G.GLYPHS:
            ch = " "
        blit(img, FONTS[G.FONT_ORDER.index(ch)], tx + i, ty, PAL[pal])


def centered(img, s, ty, pal="text"):
    text(img, s, (20 - len(s)) // 2, ty, pal)


def bar(img, tx, ty, width, pal):
    for i in range(width):
        blit(img, UTILS[0], tx + i, ty, PAL[pal])


def new_screen():
    return Image.new("RGB", (W, H), BG)


def screen_title():
    img = new_screen()
    # The wordmark is built from real game tiles, so the title screen is a
    # sample of the thing you are about to play rather than a label.
    word = "WORDLE"
    pals = ["green", "empty", "yellow", "empty", "empty", "green"]
    x = (20 - len(word) * 2) // 2
    for i, ch in enumerate(word):
        cell(img, ch, x + i * 2, 3, pals[i])
    centered(img, "PRESS START", 9, "text")
    centered(img, "UP DOWN - LETTER", 13, "dim")
    centered(img, "LEFT RIGHT - MOVE", 14, "dim")
    centered(img, "A - ENTER", 15, "dim")
    return img


def screen_play():
    img = new_screen()
    text(img, "STREAK 3", 1, 0, "dim")
    text(img, "4/6", 16, 0, "dim")
    board = [
        ("CRANE", ["absent", "yellow", "absent", "absent", "green"]),
        ("SLOTH", ["green", "absent", "yellow", "absent", "absent"]),
        ("SPORE", ["green", "absent", "green", "absent", "green"]),
        ("SO   ", ["filled", "cursor", "empty", "empty", "empty"]),
        ("     ", ["empty"] * 5),
        ("     ", ["empty"] * 5),
    ]
    for r, (word, pals) in enumerate(board):
        for c in range(5):
            cell(img, word[c], GRID_X + c * 2, GRID_Y + r * 2, pals[c])
    centered(img, "A ENTER   SEL STATS", 16, "dim")
    return img


def screen_won():
    img = new_screen()
    text(img, "STREAK 4", 1, 0, "dim")
    board = [
        ("CRANE", ["absent", "yellow", "absent", "absent", "green"]),
        ("SLOTH", ["green", "absent", "yellow", "absent", "absent"]),
        ("SPORE", ["green", "absent", "green", "absent", "green"]),
        ("SHORE", ["green"] * 5),
        ("     ", ["empty"] * 5),
        ("     ", ["empty"] * 5),
    ]
    for r, (word, pals) in enumerate(board):
        for c in range(5):
            cell(img, word[c], GRID_X + c * 2, GRID_Y + r * 2, pals[c])
    centered(img, "SPLENDID!", 15, "text")
    centered(img, "START - NEW GAME", 16, "dim")
    return img


def screen_stats():
    img = new_screen()
    centered(img, "STATISTICS", 0, "text")

    labels = [("PLAYED", "42"), ("WIN %", "88"), ("STREAK", "6"), ("MAX", "11")]
    for i, (k, v) in enumerate(labels):
        col = (i % 2) * 10 + 1
        row = 2 + (i // 2) * 2
        text(img, v, col, row, "text")
        text(img, k, col, row + 1, "dim")

    text(img, "GUESSES", 1, 7, "dim")
    dist = [1, 4, 12, 11, 7, 2]
    top = max(dist) or 1
    for i, n in enumerate(dist):
        y = 9 + i
        text(img, str(i + 1), 1, y, "dim")
        width = max(1, round(n * 11 / top))
        bar(img, 3, y, width, "green" if i == 2 else "absent")
        text(img, str(n), 3 + width + 1, y, "dim")
    text(img, "X", 1, 15, "dim")
    text(img, "5", 4, 15, "dim")
    centered(img, "B - BACK", 17, "dim")
    return img


def main():
    screens = [
        ("title", screen_title()),
        ("play", screen_play()),
        ("won", screen_won()),
        ("stats", screen_stats()),
    ]
    pad = 10
    sheet = Image.new("RGB",
                      (len(screens) * (W * SCALE + pad) + pad, H * SCALE + pad * 2),
                      (10, 10, 11))
    for i, (_, img) in enumerate(screens):
        sheet.paste(img.resize((W * SCALE, H * SCALE), Image.NEAREST),
                    (pad + i * (W * SCALE + pad), pad))
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "build", "preview.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    sheet.save(out)
    print("wrote", out, "-", ", ".join(n for n, _ in screens))


if __name__ == "__main__":
    main()
