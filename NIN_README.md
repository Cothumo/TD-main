# NIN Stage - the last layer of TDA (after ink_layer)

Inspired by Nine Inch Nails: the Peel It Back tour (2025) - projection on stacked translucent scrims, live delayed
copies of the image ("Copy of A"), a show in acts - and the static / distortion imagery of their earlier eras. No strobes / flashes - every light change is smoothed.

- **Scrim depth layers:** fainter, softer copies of the scene behind the front one (pale ink on white, dim light in the
  dark); the front scrim moves in the air (folds, sheen); the layers behind sway and are pushed by hits; a faint
  Pepper's-ghost reflection floats in front.
- **Copy of A echoes:** a strong hit leaves two delayed copies that drift out and fade (Hits From: track 1's meter with
  its own hit detection, track 2 = the ink layer's hits, or ableton_reactive t1_pulse).
- **Three acts (rotating by themselves):**
  1. **Static** - the picture breaks up like a failing analog signal: fine monochrome static in drifting bands, a slow
     rolling bar of lost signal, rows torn sideways and smeared on hits, scanlines (Broken / Year Zero era).
  2. **Melt** - video feedback (nin_trails.glsl): the picture leaves trails that slowly sink, smear and swirl apart in a
     drifting noise field, with a strong heat-haze warp - light trails in the dark picture, ink trails on white.
  3. **Scrim** - the layered projection: fainter copies behind, the front fabric moving in the air, heat-haze warp,
     Pepper's ghost.
  Echoes ("Copy of A") run in every act. With Acts Follow = Auto (the default) each act lasts Act Duration (30 s),
  then the scene moves on at the next strong hit (or 8 s later), 1 > 2 > 3 > 1 ..., crossfading over Actfade (8 s).
  Manual: the Act menu / Go to Act buttons. Ableton: scene launches (scene 1 = act 1, 4 = act 1 again).
  While "Acts Drive The Look" is on, the acts own the NIN sliders (and the ink's Layeramount); switch it off to tweak
  by hand. The act values are in the 'acts' DAT inside nin_stage. Nothing flashes: the noise keeps the picture's own
  brightness.

Files here: build_nin.py (rebuilds /project1/nin_stage: exec(open(project.folder + '/build_nin.py').read())),
nin_stage.glsl, nin_trails.glsl, nin_stage.tox; build_nin_v1.py / nin_stage_v1.glsl = before acts; *_v2_lines = with sheets of light and four acts; *_v3_corrode = with the Corrode act.
Ambient Ink Live/ = the ink layer (build_ink.py, live_features.py, shaders, ink_track2.tox, Avernus.mp3 test file).
mcp_webserver_base.tox, import_modules.py, modules/ = the TouchDesigner MCP connection (so Claude can work in TDA).

## Negative echo
For an instant after a hit the "Copy of A" echoes appear as negatives: they invert what they pass over (a difference
blend), then turn positive as they drift and fade. The frame itself never flips, so the overall brightness stays the
same (no flash). Page NIN: **Negecho** (0.8, 0 = off) and **Negtime** (0.15 s, how long the negative lasts).
Triggered by the same hits as the echoes. Backups: nin_stage_v4_before_negecho.glsl, build_nin_v4_before_negecho.py.
