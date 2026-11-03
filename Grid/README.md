# Grid - the notes you play on the GRID track shape the visuals

No buttons, no triggers: the TDA_MIDI device on the Ableton MIDI track "GRID" sends the notes to TouchDesigner
(/project1/grid_midi), and /project1/grid turns them into slow, smoothed influences. Nothing changes while nothing is
played.

| what you play | what it does |
|---|---|
| pitch (average of the held notes, Lownote 36 .. Highnote 84) | the backlight rises / sinks (act 4); low notes darken the edges, high notes lighten them |
| chord (how many notes are held, 1 .. 4+) | the haze opens (up to 2x) and the scrim layers multiply |
| velocity | more ink (up to 1.6x) |
| held notes | the Melt trails stretch (fully after Holdtime 3 s) |

Settings, page Grid: Amount (0 = off), Pitchlight, Pitchdark, Chordhaze, Velink, Holdmelt, Lownote / Highnote,
Attack 0.6 s, Release 2.5 s, Holdtime, MIDI CHOP. Outputs (/project1/grid/out): count, pitch, on, chord, vel, held and
the multipliers hmul, smul, dmul, ly, imul, madd - they multiply on top of the acts and the Stems.

Build: exec(open(project.folder + '/Grid/build_grid.py').read()) - run it again after rebuilding nin_stage, the ink or
the scenes (it wires the multipliers into them). The earlier pad version is described in README_v1_pads.md
(freeze.glsl belonged to it and is unused).
