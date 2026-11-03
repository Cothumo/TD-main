# Stems - each element belongs to a sound

- **Bass = Ableton track "Microcosm" -> the sphere's gravity.** Lens, Swirl and Streaks swell gently with it (Gravity 0.45: around their set value on
  average, about +/-25%). It follows slowly (Gravityattack 0.9 s, Gravityrelease 3.5 s) - a swell, not a pulse.
- **Pads = Ableton track "2" -> the NIN stage's Haze and Darkness.** The haze lifts and the edges sink deeper into
  darkness as the pads swell, slowly (Padattack 2.5 s, Padrelease 6 s).
- Each track is measured between its own recent quietest and loudest level (Adapt), so it works for any mix level; silence = 0.
- The acts still set Haze / Darkness / Lens etc.; the stems multiply on top of what the act chose.

Settings: /project1/stems, page Stems - Gravity, Haze, Darkness (amounts, 0 = off), the attack/release times,
Adapt, and the meter CHOPs (Bassmeter = track_D_micro/out1, Padmeter = track_C_ink/out1).
Outputs (/project1/stems/out): bass, padlevel, grav, pads, gmul, hmul, dmul.

Build (in TouchDesigner's textport): exec(open(project.folder + '/Stems/build_stems.py').read())
It makes track_D_micro (an abletonTrack COMP on Microcosm) and /project1/stems, and wires the sphere and nin_stage.
build_sphere.py and build_nin.py already contain the same wiring (falling back to 1 if stems is missing).
