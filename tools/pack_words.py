#!/usr/bin/env python3
"""Pack Wordle word lists into banked GBDK C arrays.

Each word becomes a 24-bit base-26 integer (26^5 = 11,881,376 < 2^24), stored
big-endian as 3 bytes. The valid-guess list is sorted ascending so the ROM can
binary-search it; the answer list keeps its own bank for random selection.
"""
import os

WORDS_PER_BANK = 16384 // 3  # 5461 words fit in one 16KB ROM bank
VALID_BANK_START = 2
ANSWER_BANK = 6

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
RES = os.path.join(ROOT, "res")


def pack(word):
    n = 0
    for ch in word:
        n = n * 26 + (ord(ch) - 97)
    return n


def to_bytes(n):
    return (n >> 16) & 0xFF, (n >> 8) & 0xFF, n & 0xFF


def emit_array(fh, name, words, bank):
    fh.write("#pragma bank %d\n\n" % bank)
    fh.write('#include <gbdk/platform.h>\n#include <stdint.h>\n\n')
    fh.write("BANKREF(%s)\n" % name)
    fh.write("const uint8_t %s[%d] = {\n" % (name, len(words) * 3))
    for i in range(0, len(words), 8):
        chunk = words[i:i + 8]
        line = "".join("0x%02X,0x%02X,0x%02X," % to_bytes(pack(w)) for w in chunk)
        fh.write("    " + line + "\n")
    fh.write("};\n")


def main():
    valid = sorted({w.strip() for w in open(os.path.join(TOOLS, "wordle_valid.txt")) if w.strip()})
    answers = sorted({w.strip() for w in open(os.path.join(TOOLS, "wordle_answers.txt")) if w.strip()})

    # Answers must be reachable by the validity check, or a guess of the answer
    # itself would be rejected.
    missing = set(answers) - set(valid)
    assert not missing, "answers missing from valid list: %s" % sorted(missing)[:5]

    os.makedirs(RES, exist_ok=True)

    # Split the valid list across as many banks as it needs.
    banks = [valid[i:i + WORDS_PER_BANK] for i in range(0, len(valid), WORDS_PER_BANK)]
    assert len(answers) <= WORDS_PER_BANK, "answer list needs more than one bank"

    for idx, chunk in enumerate(banks):
        bank = VALID_BANK_START + idx
        with open(os.path.join(RES, "words_%d.c" % idx), "w") as fh:
            emit_array(fh, "valid_words_%d" % idx, chunk, bank)

    with open(os.path.join(RES, "answers.c"), "w") as fh:
        emit_array(fh, "answer_words", answers, ANSWER_BANK)

    with open(os.path.join(RES, "wordlist.h"), "w") as fh:
        fh.write("#ifndef WORDLIST_H\n#define WORDLIST_H\n\n")
        fh.write('#include <gbdk/platform.h>\n#include <stdint.h>\n\n')
        fh.write("#define WORDS_PER_BANK %d\n" % WORDS_PER_BANK)
        fh.write("#define VALID_WORD_COUNT %d\n" % len(valid))
        fh.write("#define VALID_BANK_COUNT %d\n" % len(banks))
        fh.write("#define ANSWER_COUNT %d\n" % len(answers))
        fh.write("#define ANSWER_BANK %d\n\n" % ANSWER_BANK)
        for idx in range(len(banks)):
            fh.write("BANKREF_EXTERN(valid_words_%d)\n" % idx)
            fh.write("extern const uint8_t valid_words_%d[];\n" % idx)
        fh.write("BANKREF_EXTERN(answer_words)\n")
        fh.write("extern const uint8_t answer_words[];\n\n")
        fh.write("#endif\n")

    print("valid   : %d words across %d banks (%d bytes)" % (len(valid), len(banks), len(valid) * 3))
    print("answers : %d words in bank %d (%d bytes)" % (len(answers), ANSWER_BANK, len(answers) * 3))
    for idx, chunk in enumerate(banks):
        print("  bank %d: %d words" % (VALID_BANK_START + idx, len(chunk)))


if __name__ == "__main__":
    main()
