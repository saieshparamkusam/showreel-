# Jeevan Saiesh Paramkusam — 60 s Showreel

**Final video:** `out/Jeevan_Saiesh_Paramkusam_Showreel_60s.mp4` — 1920×1080, 30 fps, exactly 60.000 s (1800 frames), H.264 + AAC stereo, about -14 LUFS.

## Editable source
| Path | What it is |
|---|---|
| `src/shots.py` | Master **TIMELINE** (cut times, transitions) and every shot. Edit copy, timings, poster choices here. |
| `src/engine.py` | Compositing engine: poster placement, liquid-glass panels, text, transitions, perspective. |
| `src/audio.py` | Original synthesised score and sound design, driven by the same timeline (120 BPM, 1 beat = 15 frames). |
| `src/render.py`, `build.sh` | Parallel render and mux. |
| `assets/posters/` | The 33 posters used (copied unmodified from `saieshparamkusam/Static-Graphics`). Swap or add files and reference them by filename in `shots.py`. |
| `fonts/` | Inter (OFL) and Instrument Serif (OFL). |
| `out/audio.wav` | Mastered soundtrack, standalone. |

Run `./build.sh` to rebuild (needs ffmpeg and `pip install pillow numpy scipy fonttools brotli`).

## Poster rule
Every poster is shown **complete**: all four edges visible, original aspect ratio, no rounded corners, no shape used as a frame or container, no overlaps. Masks are used only as brief reveal wipes (and transitions); glass discs sit *behind* posters. Backdrops are heavily blurred colour fields, not poster crops.

## Structure (beat-locked)
0–4 hook (complete REWIND, slit reveal; RELICS via slat transition) · 4–9 identity (name + complete Warp Gradients poster) · 9–22 craft (Typography, Hierarchy, Color, Composition, tagline; one poster per chapter, then pairs/trios) · 22–32 range (pairs, hero, trio) · 32–36 services card · 36–49 momentum (one complete poster per beat, per quarter-second, then 2–3 poster layouts on every beat) · 49–53 climax (layouts accelerate from 1 to 5 posters, then rapid singles) · 53–55 all 18 posters assemble on one grid · 55–60 contact card.

## Notes
- **Phone number is deliberately omitted**: it was supplied as unconfirmed (`812843410`). To add it, edit `S_end()` in `src/shots.py` once confirmed.
- No corner marks, logos, watermarks, timecodes or badges: all graphics sit inside the centre safe area.
- Posters featuring real brands/artists (Nike, Ray-Ban, David Guetta, Don Toliver, Travis Scott–style Pressure Drop 23) were left out to avoid implying client work.
- Posters are ~1080 px wide, so they are upscaled slightly (Lanczos) when shown large. Higher-resolution exports would make them crisper.
- The repository contains posters and a few brand-style layouts only; no packaging mockups were supplied, so "Packaging" appears only as copy, never as invented imagery.
