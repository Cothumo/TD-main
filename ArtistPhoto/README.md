# Artist photo loop: Screen 2 silhouette + Ambient Ink with vibration

`artist_head_ink_loop.mp4` is a **7 s seamless loop** (1080 × 1080, 30 fps, H.264) built from `artist_photo.jpg`.
Only the head is used; the room, the neck and the hoodie are removed (`head_mask.png`).

![frame 52](preview_frame.jpg)

**What's in it**

- **Screen 2 silhouette** (`Screen2/screen2.glsl`): the head is a dark, backlit form against one soft light far behind
  drifting haze. The haze flows round the head and its outline catches the light. The face is drawn as scan lines
  lifted by the photo (analog video synth), with the photo's relief catching a little light. Older heads drift behind
  it as ghosts, and the rows come from slightly different moments (time slicing). The analog-TV layer is on as well:
  a tracking band rolls down once per loop, plus sync wobble, a vertical-hold slip, snow, dropouts, interlace and
  scanlines. The tracking overlay locks boxes and data bars onto the outline.
- **Ambient Ink particles** (`Ambient Ink Live/ink_*.glsl`): about 320k ink particles well up from about 56 points on
  the head's outline. The flow (curl-noise billows, a current away from the face, buoyancy) stretches them into
  tendrils. The ink spreads and pales as it ages, with trails and a dissolved halo, and is laid over the picture with
  `ink_layer`'s greys.
- **Vibration** (`ink_post.glsl`): the ink trembles all the time. At 1.55 s and 4.85 s it erupts in puffs and shakes
  hard: per-frame jitter, a fast oscillation, rows wobbling, and a faint second image trailing the shake. The Screen 2
  glitches peak on the same beats.

Every time-dependent term is periodic in the loop length, so the end runs straight into the start.

## Evaporating silhouette (latest)

`artist_head_silhouette_evaporate_loop.mp4` is a 7 s, 1080 × 1080 seamless loop made by `render_evaporate_loop.py`
(the default `--look silhouette`).

- The head is a dark form against the backlight, built from about 1.5M noise particles.
- The face is concealed. Only contours show: the outline catches the light as a grainy rim, and faint lines trace the
  hairline, eyes, brow, ear and beard edge (from the photo's edges).
- The whole head constantly evaporates to the right. Each grain rests and trembles, then lifts off on a current that
  speeds up, and turbulence and buoyancy tear the streams into dark smoke. The back of the head goes first.
- At 1.55 s and 4.85 s a gust drives the streams and the Ambient Ink vibration (`ink_post.glsl`) shakes the whole
  particle head.
- Behind it are the Screen 2 haze, the rolling tracking band, snow, dropouts, scanlines and the vignette.

`artist_head_evaporate_loop.mp4` is the earlier photo-tone version (`--look photo`): the particles take the photo's
tones, so the portrait itself is visible.

The look is set in the `PP` dict: Hold, Flight, Current, Rise, Turbulence, Coverage, Shimmer, Tremble, Rim, Contours,
Dust and Vibration. `--density` sets how many particles there are.

```
python ArtistPhoto/render_evaporate_loop.py                  # silhouette -> ArtistPhoto/artist_head_silhouette_evaporate_loop.mp4 (~5 min, ~3 GB RAM)
python ArtistPhoto/render_evaporate_loop.py --look photo     # photo tones -> ArtistPhoto/artist_head_evaporate_loop.mp4
python ArtistPhoto/render_evaporate_loop.py --preview 30 52  # a few PNGs only
```

## Re-render

```
pip install numpy opencv-python-headless
python ArtistPhoto/render_artist_loop.py                     # -> ArtistPhoto/artist_head_ink_loop.mp4 (~3 min on 4 cores)
python ArtistPhoto/render_artist_loop.py --preview 0 52 150  # a few PNGs only, to try settings
python ArtistPhoto/render_artist_loop.py --seconds 5 --size 720 --out short.mp4
```

The look is set in the `P2` dict (the Screen 2 page values) and the `PI` dict (the Ambient Ink and layer values) at
the top of the script. `BURSTS` holds the moments when the ink erupts and the vibration peaks. ffmpeg must be on the PATH.

This is an offline port of the shaders (numpy / OpenCV), not a TouchDesigner render. TouchDesigner isn't available
where this was made.

The head mask came from BiRefNet-portrait (rembg), then a cut under the beard removed the neck and hoodie.
