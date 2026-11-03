# Artist Hologram vs. the original Screen 2 silhouette

This compares `artist_hologram` (this folder) with the original Screen 2 silhouette visualisation:
`Screen2/screen2.glsl` and `Screen2/build_screen2.py`, the component `/project1/screen2`. It lists every
change made on the way from the first artist-photo video to the final hologram loop.

## At a glance

| | Screen 2 (original) | Artist Hologram (now) |
| --- | --- | --- |
| Source | live camera silhouette from `/project1/scenes` (AI person detection or difference) | the artist photo, head only (no background, neck or hoodie) |
| Frame | 1280 × 720 landscape, on a second window | 1080 × 1080 square, `OUT` + Record Loop |
| The figure | a solid dark figure (the light × 0.03) | a dark zone inside a bright particle stream, see-through (`Figure` 0.68) |
| The light | one soft backlight far behind drifting haze | the particle stream itself; the haze is only a dim backdrop |
| Movement | whatever the performer does | a constant particle stream from left to right |
| The face | always there while someone stands in view | surfaces only now and then, gradually, and sinks back |
| Look | failing analog TV, grey only | hologram projection, faint cool tint |
| Driven by | the music: pads, level and hits from `nin_stage` | a 7 s loop timeline, or optionally the `nin_stage` hits |

## 1. Source and framing

- **Still photo instead of the camera.** It reads `artist_photo.jpg` plus `head_mask.png`, no longer the `scenes/sil`
  silhouette and `scenes/cam_small` picture. The mask came from a background-removal model (BiRefNet-portrait); a cut
  under the beard removed the neck and hoodie, so **only the head** is used.
- **Square 1080 × 1080** instead of 1280 × 720. The head fills 84 % of the height and touches the frame's left edge,
  where the photo cuts the face.
- The head floats a few pixels up and down on a loop (`bob`). Screen 2's figure moved with the performer.
- **No history buffer.** Screen 2 keeps the last 48 frames of the silhouette (`history`, a 2D texture array) for time
  slicing, stutter and ghosts. A still photo has no history, so the time-based effects come from noise and the loop
  timeline instead.
- Removed Screen 2 controls: Scale, X, Y, Mirror (fixed framing) and Resolution (fixed square).

## 2. The figure

- **Made of particles, not painted.** Screen 2 darkens the figure to `col × 0.03`. Here the figure is a darker zone of
  the particle stream: inside the head the particles carry less light (`Figure`), so the stream keeps running through
  the face. **Figure 1.0 → 0.68.**
- **Detail stays soft.** Screen 2's `Detail` (0.6) adds the camera picture's fine relief. Here only a broad, blurred
  relief of the photo's highlights catches a little light (**Detail 0.22**). No traced features: an intermediate
  version had line contours for eyes, brow, hairline and beard, which were removed as too detailed and static.
- `Headglow` (new, 0.07): faint light left inside the head volume.

## 3. The outline

- **Rim** keeps Screen 2's idea: the outline catches the light. Screen 2 computes it from the silhouette gradient times
  the backlight. Here it is a soft band on the mask's outline, drawn by the particles passing it. **Rim 1.0 → 1.5.**
- **Flow** (Screen 2: the haze flows round the body). Here the flow displaces **the outline itself**: a slowly turning
  noise makes it wobble and breathe. **Flow 1.0 → 0.85.**
- **New: travelling segments.** The rim breaks into bright stretches that travel along the outline.
- **Tear** (Screen 2: rows tear while the figure moves, plus a little ambient tear). Here rows of the outline tear
  sideways now and then without any movement needed, and more on hits. **Tear 0.6 → 1.0.**
- **Echoes and Ghosts merged into Echoes.** Screen 2's ghosts are older silhouettes from the frame history, drifting
  up and aside and darkening the light. Here two faint older *outlines* trail behind the head (right / up, 16 and
  36 px at 720) as light, not darkness. **Echoes 0.8 → 1.0** (the Ghosts control is gone).
- No rim on the cut under the beard, so the removed neck doesn't show as an edge.

## 4. New: the particle stream (left → right)

- About 262,000 particles cross the whole frame from the left side to the right side (`Streamspeed`, 165 px/s at 720
  high). Curl-noise swirls (`Turbulence`) move on a loop. Sprites are short streaks along the motion, and a few
  twinkle brighter each frame.
- While the face is present the stream **slows down inside the head** (`Headslow` 0.6). The particles gather there,
  which makes the head readable as a zone of the flow.
- On the unstable moments a **gust** speeds the whole stream up.
- The **head's own particles** (new) rest on the head, mostly near the outline, trembling. Then they lift off and are
  carried away to the right with the stream, the back of the head first (`Particlehold`). They carry the face's light
  only if the face was visible when they lifted off, so the face dissolves into the flow.

## 5. New: the face appears only now and then

- Two appearances per loop (page Timing):
  - **Appear1 0.15 s, strength 0.78**, peaking on the first unstable moment;
  - **Appear2 3.45 s, strength 0.55**, a fainter one peaking on the second.
- Each appearance is gradual and eased in: it surfaces over **Rise 1.4 s**, stays for **Linger 0.3 s** and sinks back
  over **Fall 1.8 s**.
- It surfaces in **soft patches**: a drifting noise decides which parts of the head show first.
- In between there is only the flow.

## 6. Look: hologram instead of analog TV

Added:
- **Light, not shadow.** Additive glowing particles on dark, tone-mapped (`Gain`), with **bloom** (`Bloom`).
- **Projection scanlines.** Stronger than Screen 2's faint ones. Screen 2 darkens about 5 % (Scanlines 0.4 × 12 %);
  here up to 30 % (Scanlines 0.3 at full depth), with a 2 px period at 720.
- **A bright scan band rolling up**, twice per loop (`Scanband`). It replaces Screen 2's tracking band, which rolls
  down.
- **Flicker** with a rare short dip (`Flicker`).
- **Slices.** Horizontal bands jump sideways for a frame or two, more on hits (`Slices`).
- **RGB split** (`Chroma`, more on hits).
- **A faint cool tint** (`Tint` 0.84 / 0.97 / 1.08). Screen 2 is grey only; set `Tint` to 1 / 1 / 1 for grey.
- **The Screen 2 haze and backlight** stay only as a dim backdrop (`Backlight` 0.32). Screen 2's Haze, Light,
  Lightsize, Lightx and Lighty are fixed inside it.

Removed from Screen 2 (no movement in a still photo, or replaced by the hologram look):
- time slicing (`Timeslice`)
- buffer stutter (`Stutter`, `Stutterlength`)
- the scan-line figure (`Lines`, `Lineheight`, `Linespacing`)
- the tracking overlay (`Track`, `Trackcell`)
- interlace (`Interlace`)
- TV snow (`Snow`)
- dropouts, sync wobble, vertical hold slips and the tracking band (`Chaos`, `Ambient`)
- traces breaking into noise (`Noise`)
- the motion analysis (`motion_an`, `motion`)

## 7. New: Ambient Ink vibration

- The vibration of `Ambient Ink Live/ink_post.glsl` (per-frame jitter, fast oscillation, row wobble and a faint
  trailing second image) is applied to the whole hologram (`Vibration` 1.5).
- It trembles a little all the time and shakes hard on the two unstable moments.

## 8. What drives it

- Screen 2 follows the music: the pads (`/project1/stems`) thicken the haze, the level (`nin_stage/echo` slevel)
  breathes the light, and hits (`nin_stage/echo` env) trigger stutter and snow.
- The hologram runs on a **loop timeline** (page Timing): `Loop` 7 s, the two appearances, and **Burst1 1.55 s /
  Burst2 4.85 s**, the unstable moments with gust, vibration, slices and RGB split.
- **Hits = NIN stage hits** switches the gusts, vibration and glitches to follow `/project1/nin_stage/echo` env, like
  Screen 2's hits. The appearances keep following the loop.

## 9. Output

- Screen 2 opens `window2` on a second monitor and can hide the figure from the main scene (`Inmain`).
- The hologram is a self-contained component: `OUT` (null) and `out1` to wire into your chain or a window.
- **Record Loop** (page Output) starts the loop at t = 0 and writes exactly one loop to `Record File`.

## 10. The TouchDesigner component vs. the delivered videos

- The videos (`ArtistPhoto/*.mp4`) were rendered offline with numpy / OpenCV (`ArtistPhoto/render_hologram_loop.py`)
  at 30 fps. Every particle path there is precomputed, so the video loops exactly.
- The component runs **live on the GPU** with the same look, timings and parameter values. Its particles are
  simulated frame by frame, so it is not frame-identical to the video and the stream does not repeat exactly. The face
  appearances, bursts and noise all repeat with `Loop`.
- It records at the project's cook rate (60 fps in TDA).
