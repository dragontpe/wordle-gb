GBDK_HOME = /Users/francoisdekock/gbdk/
LCC = $(GBDK_HOME)bin/lcc

PROJECTNAME = wordle
SRCDIR = src
RESDIR = res
BUILDDIR = build
OBJDIR = $(BUILDDIR)/obj

SRC_OBJS = \
	$(OBJDIR)/main.o \
	$(OBJDIR)/render.o \
	$(OBJDIR)/words.o \
	$(OBJDIR)/stats.o

RES_OBJS = \
	$(OBJDIR)/res_tiles.o \
	$(OBJDIR)/res_words_0.o \
	$(OBJDIR)/res_words_1.o \
	$(OBJDIR)/res_words_2.o \
	$(OBJDIR)/res_answers.o \
	$(OBJDIR)/song.o

# hUGEDriver ships a prebuilt GBDK library, so no RGBDS toolchain is needed to
# build this project. audio/song.c is checked in rather than generated, because
# converting the .uge needs a macOS x86_64 binary; see audio/README.md.
AUDIODIR = audio
HUGE_DIR = vendor/huge
HUGE_LIB = $(HUGE_DIR)/hUGEDriver.lib

OBJS = $(SRC_OBJS) $(RES_OBJS)

# -Wm-yc  : CGB-only (we rely on per-tile background palettes)
# -Wm-yt0x1B : MBC5 + SRAM + battery, for the persistent scorecard
# -Wm-yo8 : 8 ROM banks (128KB), enough for ~52KB of word data plus code
# -Wm-ya1 : 1 bank of cartridge RAM
LCCFLAGS = -Wa-l -Wl-m -Wl-j -Wm-yc -Wm-yt0x1B -Wm-yo8 -Wm-ya1
LCCFLAGS += -I$(RESDIR) -I$(SRCDIR) -I$(HUGE_DIR)/include

all: dirs $(BUILDDIR)/$(PROJECTNAME).gbc

dirs:
	@mkdir -p $(BUILDDIR) $(OBJDIR) $(RESDIR)

# Word lists and tiles are generated, not hand-authored.
$(RESDIR)/wordlist.h $(RESDIR)/words_0.c $(RESDIR)/words_1.c $(RESDIR)/words_2.c $(RESDIR)/answers.c: tools/pack_words.py tools/wordle_valid.txt tools/wordle_answers.txt
	python3 tools/pack_words.py

$(RESDIR)/tiles.c $(RESDIR)/tiles.h: tools/gen_tiles.py
	python3 tools/gen_tiles.py

$(OBJDIR)/%.o: $(SRCDIR)/%.c $(RESDIR)/wordlist.h $(RESDIR)/tiles.h
	$(LCC) $(LCCFLAGS) -c -o $@ $<

$(OBJDIR)/res_%.o: $(RESDIR)/%.c $(RESDIR)/wordlist.h $(RESDIR)/tiles.h
	$(LCC) $(LCCFLAGS) -c -o $@ $<

$(OBJDIR)/song.o: $(AUDIODIR)/song.c
	$(LCC) $(LCCFLAGS) -c -o $@ $<

$(BUILDDIR)/$(PROJECTNAME).gbc: $(OBJS)
	$(LCC) $(LCCFLAGS) -Wl-l$(HUGE_LIB) -o $@ $^

preview:
	python3 tools/preview.py

clean:
	rm -rf $(BUILDDIR) $(RESDIR)

.PHONY: all dirs clean preview
