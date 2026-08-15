#!/usr/bin/env python3
"""Generate GBDK tile data for Wordle.

Three tile sets are emitted:

  cell_tiles  - 16x16 letter tiles for the 6x5 guess grid (blank + A-Z). The
                glyph is the 5x7 base font scaled 2x to 10x14 so it fills the
                tile the way the real game's letters do; a 5x7 glyph adrift in a
                16x16 box is what makes a board look like a debug view.
  font_tiles  - 8x8 glyphs (A-Z, 0-9, symbols) for headings and the stats screen.
  util_tiles  - a solid block, used for the statistics histogram bars.

Colour comes from CGB background palettes at runtime, not from the tiles, so one
letter tile serves every state. Pixel values mean: 0 = tile fill, 1 = border,
2 = letter ink. For a scored tile the palette sets fill and border to the same
colour, so the tile reads as solid; for an empty one the border stays visible as
a 1px outline.
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "res")

# 5x7 glyphs drawn as ASCII art; '#' is ink.
GLYPHS = {
    "A": [".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "B": ["####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."],
    "C": [".###.", "#...#", "#....", "#....", "#....", "#...#", ".###."],
    "D": ["####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."],
    "E": ["#####", "#....", "#....", "####.", "#....", "#....", "#####"],
    "F": ["#####", "#....", "#....", "####.", "#....", "#....", "#...."],
    "G": [".###.", "#...#", "#....", "#.###", "#...#", "#...#", ".###."],
    "H": ["#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "I": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"],
    "J": ["####.", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."],
    "K": ["#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"],
    "L": ["#....", "#....", "#....", "#....", "#....", "#....", "#####"],
    "M": ["#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"],
    "N": ["#...#", "##..#", "#.#.#", "#.#.#", "#..##", "#...#", "#...#"],
    "O": [".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "P": ["####.", "#...#", "#...#", "####.", "#....", "#....", "#...."],
    "Q": [".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"],
    "R": ["####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"],
    "S": [".####", "#....", "#....", ".###.", "....#", "....#", "####."],
    "T": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."],
    "U": ["#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "V": ["#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."],
    "W": ["#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"],
    "X": ["#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"],
    "Y": ["#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."],
    "Z": ["#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"],
    "0": [".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."],
    "1": ["..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."],
    "2": [".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"],
    "3": ["####.", "....#", "....#", ".###.", "....#", "....#", "####."],
    "4": ["...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."],
    "5": ["#####", "#....", "####.", "....#", "....#", "#...#", ".###."],
    "6": [".###.", "#...#", "#....", "####.", "#...#", "#...#", ".###."],
    "7": ["#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."],
    "8": [".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."],
    "9": [".###.", "#...#", "#...#", ".####", "....#", "#...#", ".###."],
    " ": [".....", ".....", ".....", ".....", ".....", ".....", "....."],
    "!": ["..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."],
    "-": [".....", ".....", ".....", "#####", ".....", ".....", "....."],
    ":": [".....", "..#..", "..#..", ".....", "..#..", "..#..", "....."],
    "%": ["##..#", "##.#.", "..#..", ".#...", "#..##", ".#.##", "....."],
    "/": ["....#", "...#.", "...#.", "..#..", ".#...", ".#...", "#...."],
    ".": [".....", ".....", ".....", ".....", ".....", ".....", "..#.."],
}

FONT_ORDER = [chr(c) for c in range(ord("A"), ord("Z") + 1)] + \
             [chr(c) for c in range(ord("0"), ord("9") + 1)] + \
             [" ", "!", "-", ":", "%", "/", "."]

CELL_ORDER = [chr(c) for c in range(ord("A"), ord("Z") + 1)]


def encode_tile(px):
    """px: 8x8 grid of ints 0-3 -> 16 bytes of GB 2bpp planar data."""
    out = []
    for y in range(8):
        lo = hi = 0
        for x in range(8):
            v = px[y][x]
            lo = (lo << 1) | (v & 1)
            hi = (hi << 1) | ((v >> 1) & 1)
        out.append(lo)
        out.append(hi)
    return out


def blank(w, h, v=0):
    return [[v] * w for _ in range(h)]


def scale2(rows):
    """Double a glyph in both axes: 5x7 -> 10x14, giving 2px strokes."""
    out = []
    for row in rows:
        doubled = "".join(c * 2 for c in row)
        out.append(doubled)
        out.append(doubled)
    return out


def make_cell(ch):
    """16x16 letter tile -> four 8x8 tiles.

    The glyph is 10x14 at (3,1), leaving exactly one pixel above and below for
    the outline, so a big letter and a clean border can coexist.
    """
    c = blank(16, 16, 0)
    for i in range(16):
        c[0][i] = 1
        c[15][i] = 1
        c[i][0] = 1
        c[i][15] = 1
    if ch != " ":
        rows = scale2(GLYPHS[ch])
        for y, row in enumerate(rows):
            for x, p in enumerate(row):
                if p == "#":
                    c[1 + y][3 + x] = 2
    tiles = []
    for tx in range(2):
        for ty in range(2):
            sub = [[c[ty * 8 + y][tx * 8 + x] for x in range(8)] for y in range(8)]
            tiles.append(encode_tile(sub))
    return tiles


def make_font_tile(ch):
    c = blank(8, 8, 0)
    rows = GLYPHS[ch]
    for y, row in enumerate(rows):
        for x, p in enumerate(row):
            if p == "#":
                c[y][1 + x] = 2
    return encode_tile(c)


def make_solid():
    """Solid block for histogram bars; drawn in the border colour."""
    return encode_tile(blank(8, 8, 1))


def emit(fh, name, tiles):
    flat = [b for t in tiles for b in t]
    fh.write("const uint8_t %s[%d] = {\n" % (name, len(flat)))
    for i in range(0, len(flat), 16):
        fh.write("    " + "".join("0x%02X," % b for b in flat[i:i + 16]) + "\n")
    fh.write("};\n\n")


def build_all():
    cells = list(make_cell(" "))
    for ch in CELL_ORDER:
        cells.extend(make_cell(ch))
    fonts = [make_font_tile(ch) for ch in FONT_ORDER]
    utils = [make_solid()]
    return cells, fonts, utils


def main():
    os.makedirs(RES, exist_ok=True)
    cells, fonts, utils = build_all()

    with open(os.path.join(RES, "tiles.c"), "w") as fh:
        fh.write('#include <gbdk/platform.h>\n#include <stdint.h>\n\n')
        emit(fh, "cell_tiles", cells)
        emit(fh, "font_tiles", fonts)
        emit(fh, "util_tiles", utils)

    with open(os.path.join(RES, "tiles.h"), "w") as fh:
        fh.write("#ifndef TILES_H\n#define TILES_H\n\n")
        fh.write('#include <gbdk/platform.h>\n#include <stdint.h>\n\n')
        fh.write("#define CELL_TILE_COUNT %d\n" % len(cells))
        fh.write("#define FONT_TILE_COUNT %d\n" % len(fonts))
        fh.write("#define UTIL_TILE_COUNT %d\n" % len(utils))
        fh.write("#define CELL_TILE_BASE 0\n")
        fh.write("#define FONT_TILE_BASE %d\n" % len(cells))
        fh.write("#define UTIL_TILE_BASE %d\n" % (len(cells) + len(fonts)))
        fh.write("#define TILE_SOLID (UTIL_TILE_BASE + 0)\n\n")
        fh.write("uint8_t font_index(char c);\n\n")
        fh.write("extern const uint8_t cell_tiles[];\n")
        fh.write("extern const uint8_t font_tiles[];\n")
        fh.write("extern const uint8_t util_tiles[];\n\n")
        fh.write("#endif\n")

    total = len(cells) + len(fonts) + len(utils)
    print("cell tiles : %d" % len(cells))
    print("font tiles : %d" % len(fonts))
    print("util tiles : %d" % len(utils))
    print("total      : %d / 256" % total)
    print("font order : %s" % "".join(FONT_ORDER))


if __name__ == "__main__":
    main()
