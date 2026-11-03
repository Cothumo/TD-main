# Meter guard - silence when Ableton goes silent

TDAbleton sends a track meter only when it changes. When Ableton stops (or the link drops) the last value stayed
frozen in TouchDesigner, so the scene believed audio was still coming: neith did not invert, ink and echoes went on.

/project1/meter_guard has one guard per track (track_A_transient, track_B_tonal, track_C_ink, track_D_micro). Each
passes the track's channels through unchanged, but a meter that has not moved at all for **Stale** (1.5 s) seconds
fades to 0 over **Fade** (0.4 s). Real audio always moves the meter, so only frozen values are silenced.

Now listening to the guards: neith_live (Transienttrack, Tonaltrack), nin_stage (Track1meter), ink_track2
(Abletonchop), stems (Bassmeter, Padmeter). ableton_reactive still reads the tracks directly.

Build: exec(open(project.folder + '/Guard/build_meter_guard.py').read()) - run it again after rebuilding the stems,
nin_stage or the ink, so they read the guards again.
