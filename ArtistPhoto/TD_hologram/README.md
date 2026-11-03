# Artist Hologram: TouchDesigner component

The artist photo as a hologram hidden in a particle stream that flows across the frame from left to right. The face
surfaces only now and then, gradually, drawn like the Screen 2 figure. This is the TouchDesigner version of
`ArtistPhoto/artist_head_hologram_loop.mp4`. **CHANGES.md** lists everything that differs from the original Screen 2
silhouette.

## Add it to your project

1. Put this folder (`TD_hologram`) into your project folder, e.g. next to `Screen2`:
   `.../TD Visuals/ArtistPhoto/TD_hologram/`. Keep the files together; the build reads the shaders and images from
   this folder.
2. Open your project (TDA) and open the Textport (Alt+T). Run:

   ```
   exec(open(project.folder + '/ArtistPhoto/TD_hologram/build_artist_hologram.py').read())
   ```

   If the folder is somewhere else, either drag `build_artist_hologram.py` into the network and right-click the Text
   DAT → **Run Script**, or first run `HOLO_DIR = r'C:/…/TD_hologram'` and then the line above.
3. The component **`/project1/artist_hologram`** appears. Select it and press `i`, or view its `OUT`. Nothing else in
   the project is changed; running the script again rebuilds the component.
4. The build saves **`artist_hologram.tox`** in this folder. In later projects, drag the `.tox` straight in; you don't
   need to run the script again.

The Textport prints `holo_log` (anything it couldn't set: parameter names occasionally change between TouchDesigner
builds) plus any node errors and warnings. If something is listed there, send me the printout.

## Use it

- **Hologram** page: the look. `Streamglow`, `Figure`, `Headglow`, `Rim`, `Flow`, `Tear`, `Echoes` and `Detail` set
  how the head shows. `Streamspeed`, `Headslow`, `Turbulence`, `Particlesize` and `Particlehold` set the particles.
  `Gain`, `Bloom`, `Scanlines`, `Scanband`, `Flicker`, `Slices`, `Chroma`, `Vibration`, `Backlight` and `Tint` set the
  hologram.
- **Timing** page: `Loop` (7 s), `Appear1` / `Strength1` and `Appear2` / `Strength2` (when the face surfaces and how
  clearly), `Rise` / `Linger` / `Fall` (how slowly), and `Burst1` / `Burst2` (the unstable moments).
  `Hits = NIN stage hits` makes the gusts, vibration and glitches follow `/project1/nin_stage/echo` instead of the loop.
- **Output** page: **Record Loop** restarts the loop at t = 0 and writes exactly one loop to `Record File` (at the
  project's cook rate). **Restart Particles** scatters the particles again.
- To show it: wire `out1` into your chain, or point a Window COMP (or your `viewer`) at `/project1/artist_hologram/OUT`.

## Inside

| Node | What it does |
| --- | --- |
| `photo`, `mask`, `place` | the photo and the head mask, placed in the 1080 × 1080 frame (cooks once) |
| `mask_*`, `luma_*`, `maps` | the head's static maps: outline, volume, soft relief, where the stream slows down |
| `glow` | every frame: the Screen 2-style figure (soft rim, flowing outline, segments, tears, echoes, presence) |
| `stream`, `stream_fb` | 512 × 512 stream particles (GLSL feedback simulation, left → right) |
| `head`, `head_fb` | 512 × 512 candidates for the head's own particles (rest, then evaporate into the stream) |
| `*_mat`, `*_geo`, `render` | the particles as instanced sprites (GLSL MAT), additive |
| `bloom_*`, `post` | the hologram: vibration, bloom, scanlines, scan band, flicker, slices, RGB split, haze |
| `OUT`, `out1`, `record` | output and the loop recorder |

Shaders: `holo_common.glsl` (shared; the build puts it in front of the others), `holo_place`, `holo_maps`,
`holo_glow`, `holo_sim_stream`, `holo_sim_head`, `holo_vertex`, `holo_pixel`, `holo_post`.

## Notes

- **Tested so far:**
  - All shaders compile with glslang against TouchDesigner's injected declarations.
  - The figure shader (`holo_glow`) was run on the real head maps and matches the video's placement and timing.
- **Not yet tested inside TouchDesigner**, as with the other build scripts in this repo. The operator and parameter
  names follow the 2025 builds that `build_ink.py` and `build_screen2.py` use; anything that doesn't apply is listed
  in `holo_log` rather than stopping the build.
- The Non-Commercial licence caps every TOP at 1280; this component uses 1080.
- On a weaker GPU, lower the particle counts: `STREAM_RES` / `HEAD_RES` at the top of the build script (e.g. 384).
