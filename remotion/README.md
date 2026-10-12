# Remotion project

Starter Remotion setup (1920×1080, 30 fps, 1800 frames) alongside the Python pipeline. It reuses `../assets/posters`, `../fonts` and `../out/audio.wav` via symlinks in `public/`.

```
cd remotion && npm install
npm run studio     # live preview
npm run render     # -> ../out/remotion_showreel.mp4
npm run still      # -> ../out/remotion_still.png
```

If Remotion cannot download its browser (restricted network), point it at an installed Chromium:
`REMOTION_BROWSER=/path/to/chrome npm run render`

Edit `src/Showreel.tsx` to build shots. Remotion packages are pinned to the same exact version (4.0.535); keep them in sync when upgrading.
