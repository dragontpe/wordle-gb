# Audio

## Music

`bs-rpg-seaside.uge` — **"Seaside Village" by Beatscribe**, from
https://github.com/Beatscribe/homebrew_vgm

**Licence: CC0.** The repository README states the assets are "available under
the CC0 license" and that credit is "not required." Safe for commercial release,
including itch.io. No attribution obligation, though the game credits Beatscribe
anyway.

CC0 is more permissive than MIT here: MIT would require shipping a copyright
notice, CC0 requires nothing.

## Driver

hUGEDriver, vendored under `vendor/huge/`, from
https://github.com/SuperDisk/hUGEDriver — described by its author as a "public
domain sound driver for Game Boy homebrew."

Taken from the **v6.1.3 release package**, which ships a prebuilt
`hUGEDriver.lib` for GBDK. That matters: building the driver from source needs
the RGBDS assembler plus `rgb2sdas.py`, and that path is currently broken on
this machine — `rgb2sdas.py` accepts RGBDS object revisions 6-9, while current
rgbasm (v0.8.0) emits revision 10. Using the prebuilt library sidesteps the
whole problem.

## Regenerating res/song.c

`res/song.c` is generated from the `.uge` and checked in, so a normal `make`
needs none of this.

```sh
./vendor/huge/uge2source audio/bs-rpg-seaside.uge --bank=0 seaside_song res/song.c
```

Notes:

- The bank flag only accepts the `--bank=N` long form. `-b N` and `-b=N` both
  fail with "Option at position 2 needs an argument".
- **Bank 0 is deliberate.** `hUGE_init()` takes a bare pointer and the driver
  does no bank switching of its own, so song data must live somewhere always
  paged in. The game's word lookup switches ROM banks constantly, which would
  otherwise pull the song's bank out from under the driver.
- `uge2source` is an x86_64 binary and runs under Rosetta 2 on Apple Silicon.
  It comes from the hUGETracker macOS release.

## Playback

`hUGE_dosound` is registered with `add_VBL()` and ticks once per VBlank. This is
deliberate rather than using a timer: VBlank still fires once per real frame in
CGB double-speed mode, so `cpu_fast()` cannot skew the tempo. Do not also call
`hUGE_dosound()` in the main loop — ticking twice a frame doubles the tempo.

Music plays on the title screen only and is stopped before the board appears.

## Verifying

```sh
python3 tools/test_audio.py
```

Measures PyBoy's emulated audio output. Do **not** try to verify this by reading
the APU registers: several are write-only and read back as 0xFF, so register
inspection reports silence even while the music is playing correctly.
