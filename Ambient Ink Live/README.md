# Ambient Ink Live - the third reacting layer of TDA.16

The Ambient Ink simulation (1M GPU particles) driven **live by Ableton track "2"**, multiplied over `neith_live`.

In TDA.16:
- `/project1/abletonLevel_track2` - TDAbleton levels of track "2" from its TDA_Audio_Analyzer (Low / Mid / High).
  The analyzer rack on track "2" was switched on in Ableton for this.
- `/project1/ink_track2` - the ink. The Script CHOP `live` turns the three band levels into the ink's features frame
  by frame (`live_features.py`): loudness, low hits (eruptions, pressure waves), hi-hats (sprays), accents, a slowly
  turning current. Play page: **Source** (Ableton track "2" / audio input / test file), **Input Gain**,
  **Restart Ink**. Look page: the Ambient Ink sliders, plus **Layeramount** (how strongly the ink sits over the picture).
- `/project1/ink_layer` - neith_live/OUT x ink (multiply), crossfaded by Layeramount; the `viewer` window shows it.
  To go back to neith_live alone, set the viewer's Window Operator to /project1/neith_live/OUT (or Layeramount 0).

Rebuild (Textport): `exec(open(r'C:/Users/cothu/Documents/TD Visuals/Ambient Ink Live/build_ink.py').read())`
It only replaces ink_track2 and ink_layer. `ink_track2.tox` is a saved copy of the layer.

Preset: the original Ambient Ink particles (Opacity 3, Condense 1, Dust 0.5, Trails 0.25, Lifetime 1) with Vibration 1.5
(the ink trembles on unstable sound), on white paper so neith_live underneath looks as before.

## neith_live, thinned out (2026-10-25)
To make the scene less crowded these neith_live values were lowered: Quality 0.42 > 0.3, Density 1 > 0.55,
Chaos 1 > 0.7, Noise 1 > 0.6, Depth Dust 1 > 0.4, Red Vapor 1.8 > 0.9, Vapor Glow 2.6 > 1.6, Vein Loops 1 > 0.5,
Interference 1 > 0.5, Static Bursts 1 > 0.4, Accent Lights 0.6 > 0.4, Invert Smoothing 0.3 > 1.0 (calmer inversions).
All previous values are in neith_live_settings_before.json. To restore them (Textport):
  import json; N = op('/project1/neith_live')
  [setattr(getattr(N.par, k), 'val', v) for k, v in json.load(open(r'C:/Users/cothu/Documents/TD Visuals/Ambient Ink Live/neith_live_settings_before.json')).items() if not getattr(N.par, k).readOnly]
Later the background texture was returned to the original values (Noise 1, Density 1, Red Vapor 1.8, Vapor Glow 2.6,
Interference 1, Static Bursts 1); still lowered: Quality 0.3, Chaos 0.7, Depth Dust 0.4, Vein Loops 0.5,
Accent Lights 0.4. The inversion shader is the gradual one (neith_quiet_pixel.glsl; original: neith_quiet_pixel_before.glsl).
Then the vapor was removed: Red Vapor 0, Vapor Glow 0 (originally 1.8 / 2.6).
