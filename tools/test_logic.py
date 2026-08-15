#!/usr/bin/env python3
"""Verify the data layout and scoring rules the ROM depends on.

Reads the generated C arrays back out (so it tests what actually shipped, not a
re-derivation) and checks:
  1. the packed valid list is sorted, so binary search is legal
  2. every word is findable by the exact search the ROM performs, including the
     bank arithmetic
  3. duplicate-letter scoring matches known NYT behaviour
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "res")
TOOLS = os.path.join(ROOT, "tools")
WORDS_PER_BANK = 16384 // 3

fail = 0


def check(cond, msg):
    global fail
    if not cond:
        print("FAIL:", msg)
        fail += 1
    else:
        print("ok  :", msg)


def read_bytes_from_c(path):
    src = open(path).read()
    body = src[src.index("{", src.index("const uint8_t")):]
    return [int(x, 16) for x in re.findall(r"0x([0-9A-Fa-f]{2})", body)]


def unpack(n):
    out = []
    for _ in range(5):
        out.append(n % 26)
        n //= 26
    return "".join(chr(97 + c) for c in reversed(out))


def pack(w):
    n = 0
    for ch in w:
        n = n * 26 + (ord(ch) - 97)
    return n


# --- Rebuild the flat word array exactly as the ROM sees it ----------------
chunks = []
for i in range(3):
    raw = read_bytes_from_c(os.path.join(RES, "words_%d.c" % i))
    words = [(raw[j] << 16) | (raw[j + 1] << 8) | raw[j + 2] for j in range(0, len(raw), 3)]
    chunks.append(words)

flat = []
for c in chunks:
    flat.extend(c)

source = sorted({w.strip() for w in open(os.path.join(TOOLS, "wordle_valid.txt")) if w.strip()})
# Trailing padding byte in a full bank can produce one bogus entry; trim to count.
flat = flat[:len(source)]

check(flat == sorted(flat), "packed valid list is sorted ascending")
check(len(flat) == len(source), "valid word count %d matches source %d" % (len(flat), len(source)))
check([unpack(n) for n in flat] == source, "packed words round-trip to the original list")


def rom_binary_search(target):
    """Mirror of word_is_valid(), including the bank/offset arithmetic."""
    lo, hi = 0, len(source) - 1
    while lo <= hi:
        mid = lo + ((hi - lo) >> 1)
        chunk = chunks[mid // WORDS_PER_BANK]
        v = chunk[mid % WORDS_PER_BANK]
        if v == target:
            return True
        if v < target:
            lo = mid + 1
        else:
            if mid == 0:
                break
            hi = mid - 1
    return False


missing = [w for w in source if not rom_binary_search(pack(w))]
check(not missing, "every valid word is found by the ROM's search (%d missing)" % len(missing))

answers = sorted({w.strip() for w in open(os.path.join(TOOLS, "wordle_answers.txt")) if w.strip()})
missing_ans = [w for w in answers if not rom_binary_search(pack(w))]
check(not missing_ans, "every answer is accepted as a guess (%d missing)" % len(missing_ans))

rejects = ["zzzzz", "aaaaa", "qqqqq", "xyzzy"]
bogus = [w for w in rejects if w not in set(source) and rom_binary_search(pack(w))]
check(not bogus, "non-words are rejected")

raw = read_bytes_from_c(os.path.join(RES, "answers.c"))
ans_packed = [(raw[j] << 16) | (raw[j + 1] << 8) | raw[j + 2] for j in range(0, len(raw), 3)][:len(answers)]
check([unpack(n) for n in ans_packed] == answers, "answer bank round-trips correctly")


# --- Scoring ---------------------------------------------------------------
GREEN, YELLOW, ABSENT = "G", "Y", "-"


def score(guess, answer):
    """Mirror of score_row()."""
    counts = {}
    for ch in answer:
        counts[ch] = counts.get(ch, 0) + 1
    out = [ABSENT] * 5
    for i in range(5):
        if guess[i] == answer[i]:
            out[i] = GREEN
            counts[guess[i]] -= 1
    for i in range(5):
        if out[i] == GREEN:
            continue
        if counts.get(guess[i], 0) > 0:
            out[i] = YELLOW
            counts[guess[i]] -= 1
    return "".join(out)


def score_reference(guess, answer):
    """Independent formulation, used to cross-check score().

    Rather than walking positions twice, this works per distinct letter: the
    total number of marks a letter earns is min(occurrences in guess,
    occurrences in answer); greens claim theirs by position, and the remainder
    become yellows on that letter's leftmost non-green positions. Agreeing with
    score() on every pair is far stronger evidence than hand-picked expectations.
    """
    out = [ABSENT] * 5
    greens = {i for i in range(5) if guess[i] == answer[i]}
    for i in greens:
        out[i] = GREEN
    for letter in set(guess):
        in_guess = [i for i in range(5) if guess[i] == letter]
        total = min(len(in_guess), answer.count(letter))
        green_count = len([i for i in in_guess if i in greens])
        remaining = total - green_count
        for i in in_guess:
            if remaining <= 0:
                break
            if i not in greens:
                out[i] = YELLOW
                remaining -= 1
    return "".join(out)


# Hand-checked anchors. Each was worked through by counting letters explicitly.
cases = [
    ("crane", "crane", "GGGGG"),   # exact match
    ("slate", "crane", "--G-G"),   # no duplicates
    ("speed", "abide", "--Y-Y"),   # guess has 2 e, answer 1: only the first pays
    ("geese", "eject", "-YG--"),   # green e consumes one of the answer's two e
    ("array", "radar", "YYYG-"),   # 2 a / 2 r both present, one a lands green
    ("allot", "cello", "-YGY-"),   # 2 l in both, one green one yellow
    ("mamma", "gamma", "-GGGG"),   # 3 m in guess, 2 in answer
    ("esses", "sense", "YYYY-"),   # 3 s / 2 e vs 2 s / 2 e, no greens at all
    ("abbey", "kebab", "YYGY-"),   # 2 b in both, one green
]
for guess, answer, expected in cases:
    got = score(guess, answer)
    check(got == expected, "score %s vs %s -> %s (expected %s)" % (guess, answer, got, expected))

# Exhaustive cross-check of the two independent implementations. Sampling the
# real word lists exercises the duplicate cases that actually occur in play.
import random
random.seed(1234)
mismatches = []
pool = source
for _ in range(200000):
    g = random.choice(pool)
    a = random.choice(answers)
    if score(g, a) != score_reference(g, a):
        mismatches.append((g, a, score(g, a), score_reference(g, a)))
        if len(mismatches) > 5:
            break
check(not mismatches, "200k random guess/answer pairs agree with the reference (%s)"
      % (mismatches[:3] if mismatches else "0 mismatches"))

# Every answer scored against itself must be all green.
bad_self = [w for w in answers if score(w, w) != "GGGGG"]
check(not bad_self, "every answer scores all-green against itself")

print()
if fail:
    print("%d CHECK(S) FAILED" % fail)
    sys.exit(1)
print("all checks passed")
