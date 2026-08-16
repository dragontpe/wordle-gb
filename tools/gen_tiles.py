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
    # (c) copyright mark, addressed as '@' in text strings.
    "@": [".###.", "#...#", "#.###", "##..#", "#.###", "#...#", ".###."],
}

FONT_ORDER = [chr(c) for c in range(ord("A"), ord("Z") + 1)] + \
             [chr(c) for c in range(ord("0"), ord("9") + 1)] + \
             [" ", "!", "-", ":", "%", "/", ".", "@"]

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


def scale_tall(rows):
    """5x7 -> 10x13: double width everywhere, double height except one row.

    The dropped row is chosen per glyph: the first row that duplicates its
    neighbour, so the letter loses redundancy rather than a feature. Dropping
    the middle row blindly halved the A's crossbar, which made it read as an
    H at keycap size."""
    skip = 3
    for i in range(1, 7):
        if rows[i] == rows[i - 1]:
            skip = i
            break
    out = []
    for i, row in enumerate(rows):
        d = "".join(c * 2 for c in row)
        out.append(d)
        if i != skip:
            out.append(d)
    return out


def make_cell(ch):
    """16x16 keycap -> four 8x8 tiles.

    Wordyl-style key: a rounded 15x15 body with a 1px ink outline and a drop
    shadow falling one pixel down-right, sitting on the sky. Pixel values:
    0 = sky, 1 = key face, 2 = shadow, 3 = ink (outline and letter). State
    colours arrive via the palette, so one set of tiles serves every state.
    """
    c = blank(16, 16, 0)

    # Drop shadow: the body silhouette shifted one pixel down-right.
    for y in range(1, 16):
        c[y][15] = 2
    for x in range(1, 16):
        c[15][x] = 2
    c[1][15] = 0
    c[15][1] = 0

    # Body outline, rounded by leaving the corner pixels as sky.
    for i in range(1, 14):
        c[0][i] = 3
        c[14][i] = 3
        c[i][0] = 3
        c[i][14] = 3

    # Face.
    for y in range(1, 14):
        for x in range(1, 14):
            c[y][x] = 1

    if ch != " ":
        rows = scale_tall(GLYPHS[ch])
        for y, row in enumerate(rows):
            for x, p in enumerate(row):
                if p == "#":
                    c[1 + y][2 + x] = 3
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
    """Solid block for histogram bars; drawn in the face colour."""
    return encode_tile(blank(8, 8, 1))


def make_logo():
    """The title logo: WORDLE as sticker lettering - the glyph filled in the
    face colour, wrapped in a 1px ink outline, with the whole sticker casting
    a shadow one pixel down-right. Thin strokes with a bare shadow read as
    large text; fill + outline + shadow is what reads as a logo. Values:
    0 = sky, 1 = face, 2 = shadow, 3 = ink; drawn with cell palettes, so the
    attribute can recolour individual letters."""
    word = "WORDLE"
    w = 16 * len(word)
    c = blank(w, 16, 0)
    for i, ch in enumerate(word):
        rows = scale_tall(GLYPHS[ch])          # 10x13
        ox, oy = i * 16 + 2, 1
        fill = set()
        for y, row in enumerate(rows):
            for x, px in enumerate(row):
                if px == "#":
                    fill.add((ox + x, oy + y))
        # Outline: every sky neighbour of the fill, including diagonals.
        edge = set()
        for (x, y) in fill:
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if (x + dx, y + dy) not in fill:
                        edge.add((x + dx, y + dy))
        # Shadow: the whole sticker silhouette, one pixel down-right.
        for (x, y) in fill | edge:
            if 0 <= y + 1 < 16 and x + 1 < w:
                c[y + 1][x + 1] = 2
        for (x, y) in edge:
            if 0 <= y < 16:
                c[y][x] = 3
        for (x, y) in fill:
            c[y][x] = 1
    tiles = []
    for ty in range(2):
        for tx in range(w // 8):
            sub = [[c[ty * 8 + y][tx * 8 + x] for x in range(8)] for y in range(8)]
            tiles.append(encode_tile(sub))
    return tiles


def make_logo2():
    """The big title logo: WORDLE at 3x scale (15x21 letters) on an arched
    baseline, sticker construction - fill, ink outline, dropped shadow - the
    register real GBC titles use, where the logotype IS the title screen.

    Letters alternate two fill values so a single palette colours the whole
    block: 0 = paper, 1 = fill A (green), 2 = fill B (orange), 3 = ink.
    Boundary tiles hold two letters' fills and stay within four values.
    Returns (tiles, tilemap) for a 14x4-tile region with duplicates shared.
    """
    word = "WORDLE"
    W, H = 112, 32
    c = blank(W, H, 0)
    arc = [5, 1, 0, 0, 1, 5]
    for i, ch in enumerate(word):
        ox, oy = 2 + i * 18, 1 + arc[i]
        fill_v = 1 if (i % 2 == 0) else 2
        fill = set()
        for gy, row in enumerate(GLYPHS[ch]):
            for gx, px in enumerate(row):
                if px == "#":
                    for dy in range(3):
                        for dx in range(3):
                            fill.add((ox + gx * 3 + dx, oy + gy * 3 + dy))
        edge = set()
        for (x, y) in fill:
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if (x + dx, y + dy) not in fill:
                        edge.add((x + dx, y + dy))
        body = fill | edge
        for (x, y) in body:                    # 2px shadow, down-right
            for (sx, sy) in ((x + 2, y + 2),):
                if 0 <= sx < W and 0 <= sy < H and (sx, sy) not in body:
                    if c[sy][sx] == 0:
                        c[sy][sx] = 3
        for (x, y) in edge:
            if 0 <= x < W and 0 <= y < H:
                c[y][x] = 3
        for (x, y) in fill:
            c[y][x] = fill_v

    # Which letters' fill pixels land in each tile decides its palette: the
    # rainbow colours are chosen so every adjacent pair fits one of four
    # palettes (see render.c). Pair index i covers letters i and i+1.
    tiles, tilemap, attr, index = [], [], [], {}
    pair_pal = [0, 1, 2, 3, 0]
    for ty in range(H // 8):
        for tx in range(W // 8):
            sub = tuple(tuple(c[ty * 8 + y][tx * 8 + x] for x in range(8))
                        for y in range(8))
            if sub not in index:
                index[sub] = len(tiles)
                tiles.append(encode_tile([list(r) for r in sub]))
            tilemap.append(index[sub])
            letters = set()
            for y in range(8):
                for x in range(8):
                    if c[ty * 8 + y][tx * 8 + x] in (1, 2):
                        letters.add(min((tx * 8 + x - 2) // 18, 5))
            lo = min(letters) if letters else 0
            attr.append(pair_pal[min(lo, 4)])
    return tiles, tilemap, attr


def make_sparkle(kind):
    """Little dark decorations scattered on the sky, wordyl-style. Drawn in
    value 2, the ink slot of the text palette, so they need no palette of
    their own."""
    c = blank(8, 8, 0)
    if kind == 0:      # four-point star
        pts = [(3,1),(3,2),(3,4),(3,5),(1,3),(2,3),(4,3),(5,3),(3,3)]
    elif kind == 1:    # dot
        pts = [(3,3)]
    else:              # tiny diamond
        pts = [(3,2),(2,3),(4,3),(3,4)]
    for x, y in pts:
        c[y][x] = 2
    return encode_tile(c)


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
    utils = [make_solid(), make_sparkle(0), make_sparkle(1), make_sparkle(2)]
    logo = make_logo()
    logo2, logo2_map, logo2_attr = make_logo2()
    return cells, fonts, utils, logo, logo2, logo2_map, logo2_attr


def main():
    os.makedirs(RES, exist_ok=True)
    cells, fonts, utils, logo, logo2, logo2_map, logo2_attr = build_all()

    with open(os.path.join(RES, "tiles.c"), "w") as fh:
        fh.write('#include <gbdk/platform.h>\n#include <stdint.h>\n\n')
        emit(fh, "cell_tiles", cells)
        emit(fh, "font_tiles", fonts)
        emit(fh, "util_tiles", utils)
        emit(fh, "logo_tiles", logo)
        emit(fh, "logo2_tiles", logo2)
        fh.write("const uint8_t logo2_map[%d] = {\n    " % len(logo2_map))
        fh.write(", ".join(str(v) for v in logo2_map))
        fh.write("\n};\n\n")
        fh.write("const uint8_t logo2_attr[%d] = {\n    " % len(logo2_attr))
        fh.write(", ".join(str(v) for v in logo2_attr))
        fh.write("\n};\n\n")

    with open(os.path.join(RES, "tiles.h"), "w") as fh:
        fh.write("#ifndef TILES_H\n#define TILES_H\n\n")
        fh.write('#include <gbdk/platform.h>\n#include <stdint.h>\n\n')
        fh.write("#define CELL_TILE_COUNT %d\n" % len(cells))
        fh.write("#define FONT_TILE_COUNT %d\n" % len(fonts))
        fh.write("#define UTIL_TILE_COUNT %d\n" % len(utils))
        fh.write("#define CELL_TILE_BASE 0\n")
        fh.write("#define FONT_TILE_BASE %d\n" % len(cells))
        fh.write("#define UTIL_TILE_BASE %d\n" % (len(cells) + len(fonts)))
        fh.write("#define LOGO_TILE_COUNT %d\n" % len(logo))
        fh.write("#define LOGO_TILE_BASE %d\n" % (len(cells) + len(fonts) + len(utils)))
        fh.write("#define LOGO_TILES_W %d\n" % (len(logo) // 2))
        fh.write("#define LOGO2_TILE_COUNT %d\n" % len(logo2))
        fh.write("#define LOGO2_TILE_BASE %d\n" % (len(cells) + len(fonts) + len(utils) + len(logo)))
        fh.write("#define LOGO2_W 14\n#define LOGO2_H 4\n")
        fh.write("#define TILE_SOLID (UTIL_TILE_BASE + 0)\n")
        fh.write("#define TILE_STAR (UTIL_TILE_BASE + 1)\n")
        fh.write("#define TILE_DOT (UTIL_TILE_BASE + 2)\n")
        fh.write("#define TILE_DIAMOND (UTIL_TILE_BASE + 3)\n\n")
        fh.write("uint8_t font_index(char c);\n\n")
        fh.write("extern const uint8_t cell_tiles[];\n")
        fh.write("extern const uint8_t font_tiles[];\n")
        fh.write("extern const uint8_t util_tiles[];\n")
        fh.write("extern const uint8_t logo_tiles[];\n")
        fh.write("extern const uint8_t logo2_tiles[];\n")
        fh.write("extern const uint8_t logo2_map[];\n")
        fh.write("extern const uint8_t logo2_attr[];\n\n")
        fh.write("#endif\n")

    total = len(cells) + len(fonts) + len(utils) + len(logo) + len(logo2)
    print("cell tiles : %d" % len(cells))
    print("font tiles : %d" % len(fonts))
    print("util tiles : %d" % len(utils))
    print("logo tiles : %d" % len(logo))
    print("logo2 tiles: %d" % len(logo2))
    print("total      : %d / 256" % total)
    print("font order : %s" % "".join(FONT_ORDER))


if __name__ == "__main__":
    main()
